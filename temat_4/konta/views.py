"""
Widoki kont. Komentarze przy widokach mówią, DLACZEGO są chronione tak, a nie inaczej.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from moderacja.models import AkcjaModeratora, RodzajAkcji
from relacje.uslugi import czy_znajomi, widoczni_dla
from relacje.models import Blokada, Znajomosc

from .forms import LogowanieForm, ProfilForm, RejestracjaForm, ZarzadzanieKontemForm
from .models import Rola, Uzytkownik
from .uprawnienia import (
    KOMUNIKAT_BRAK_DOSTEPU,
    WymaganaRolaMixin,
    odmow_dostepu,
    pobierz_lub_odmow,
    zapisz_zdarzenie,
)


# ---------------------------------------------------------------------------
# Rejestracja, logowanie, wylogowanie
# ---------------------------------------------------------------------------

class RejestracjaView(CreateView):
    """Publiczna. Rola zawsze Użytkownik – ustawiana w RejestracjaForm.save()."""

    form_class = RejestracjaForm
    template_name = "konta/rejestracja.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("posty:tablica")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        uzytkownik = form.save()
        # login() zmienia identyfikator sesji (ochrona przed session fixation).
        login(self.request, uzytkownik, backend="konta.backends.TylkoNiezablokowaniBackend")
        zapisz_zdarzenie(self.request, f"REJESTRACJA konta {uzytkownik.username}")
        messages.success(self.request, "Witaj w Kręgu! Uzupełnij swój profil.")
        return redirect("konta:profil_edycja")


class LogowanieView(LoginView):
    """Publiczna. Próby limituje django-axes; blokady kont – konta.backends."""

    template_name = "konta/logowanie.html"
    authentication_form = LogowanieForm
    redirect_authenticated_user = True


class WylogowanieView(LogoutView):
    """
    Tylko POST (Django 5 – ochrona przed wylogowaniem przez <img src=...>).
    Clear-Site-Data czyści cache, ciasteczka i magazyny witryny – na wspólnym
    komputerze „Wstecz” po wylogowaniu nie pokaże prywatnych stron.
    """

    def post(self, request, *args, **kwargs):
        odpowiedz = super().post(request, *args, **kwargs)
        odpowiedz["Clear-Site-Data"] = '"cache", "cookies", "storage"'
        odpowiedz["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        return odpowiedz


# ---------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------

class EdycjaProfiluView(WymaganaRolaMixin, UpdateView):
    """
    Adres BEZ identyfikatora (/profil/edycja/) – obiektem jest zawsze request.user,
    więc nie ma czego podmienić w URL (IDOR niemożliwy z definicji).
    """

    form_class = ProfilForm
    template_name = "konta/profil_edycja.html"

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profil zapisany.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("konta:profil", args=[self.request.user.username])


class ProfilView(WymaganaRolaMixin, View):
    """
    Profil innej osoby. Zbiór: widoczni_dla(user) – bez osób w relacji blokady
    i nieaktywnych. Brak konta i blokada => to samo neutralne 403 (scenariusz 12).
    Data urodzenia tylko dla znajomych (minimalizacja danych); e-mail nigdy.
    """

    def get(self, request, username):
        profil = pobierz_lub_odmow(request, widoczni_dla(request.user), username=username)
        ja = profil.pk == request.user.pk
        znajomi = czy_znajomi(request.user, profil)
        relacja = Znajomosc.miedzy(request.user, profil).first()
        from posty.models import Post

        posty = Post.objects.widoczne_dla(request.user).filter(autor=profil, grupa__isnull=True) \
            .z_licznikami(request.user)
        strona = Paginator(posty, 10).get_page(request.GET.get("strona"))
        return render(request, "konta/profil.html", {
            "profil": profil,
            "ja": ja,
            "znajomi": znajomi,
            "relacja": relacja,
            "moja_blokada": Blokada.objects.filter(kto=request.user, kogo=profil).exists(),
            "pokaz_prywatne": ja or znajomi,
            "strona": strona,
        })


class MojProfilView(WymaganaRolaMixin, View):
    def get(self, request):
        return redirect("konta:profil", request.user.username)


class SzukajView(WymaganaRolaMixin, View):
    """
    Wyszukiwarka nie zdradza prywatnych danych: tylko login i avatar osób
    widocznych dla pytającego (bez zablokowanych), grupy – nazwa i typ.
    """

    def get(self, request):
        q = (request.GET.get("q") or "").strip()[:50]
        osoby, grupy = [], []
        if len(q) >= 2:
            from grupy.models import Grupa

            osoby = widoczni_dla(request.user).filter(username__icontains=q) \
                .only("id", "username", "avatar")[:20]
            grupy = Grupa.objects.widoczne_dla(request.user).filter(nazwa__icontains=q) \
                .only("id", "nazwa", "prywatna")[:20]
        return render(request, "konta/szukaj.html", {"q": q, "osoby": osoby, "grupy": grupy})


# ---------------------------------------------------------------------------
# Panel administratora (role i blokady)
# ---------------------------------------------------------------------------

class ListaUzytkownikowView(WymaganaRolaMixin, ListView):
    """Tylko Administrator. Lista bez danych profilu – login, rola, status."""

    minimalna_rola = Rola.ADMINISTRATOR
    template_name = "konta/panel_uzytkownicy.html"
    paginate_by = 25
    context_object_name = "uzytkownicy"

    def get_queryset(self):
        qs = Uzytkownik.objects.only("id", "username", "rola", "is_active", "zablokowany_do", "date_joined")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(username__icontains=q))
        return qs.order_by("username")


class ZarzadzanieKontemView(WymaganaRolaMixin, UpdateView):
    """
    Tylko Administrator. Zbiór WYKLUCZA własne konto – administrator nie odbierze
    sobie roli ani nie zablokuje się (wymóg zadania). Zmiana roli/blokady
    trafia do logu audytu i historii działań.
    """

    minimalna_rola = Rola.ADMINISTRATOR
    form_class = ZarzadzanieKontemForm
    template_name = "konta/panel_konto.html"
    context_object_name = "konto"

    def get_object(self, queryset=None):
        zbior = Uzytkownik.objects.exclude(pk=self.request.user.pk)
        return pobierz_lub_odmow(self.request, zbior, pk=self.kwargs["pk"])

    @transaction.atomic
    def form_valid(self, form):
        poprzednia = Uzytkownik.objects.get(pk=self.object.pk)
        konto = form.save()
        if poprzednia.rola != konto.rola:
            AkcjaModeratora.objects.create(
                wykonal=self.request.user, akcja=RodzajAkcji.ZMIANA_ROLI,
                cel=konto.username, uzasadnienie=f"{poprzednia.get_rola_display()} → {konto.get_rola_display()}",
            )
            zapisz_zdarzenie(self.request, f"ZMIANA ROLI {konto.username}: {poprzednia.rola} -> {konto.rola}")
        if poprzednia.zablokowany_do != konto.zablokowany_do:
            akcja = RodzajAkcji.BLOKADA if konto.zablokowany_do else RodzajAkcji.ODBLOKOWANIE
            AkcjaModeratora.objects.create(
                wykonal=self.request.user, akcja=akcja, cel=konto.username,
                uzasadnienie=f"do {konto.zablokowany_do:%Y-%m-%d %H:%M}" if konto.zablokowany_do else "",
            )
            zapisz_zdarzenie(self.request, f"BLOKADA KONTA {konto.username} do {konto.zablokowany_do}")
        messages.success(self.request, f"Zapisano zmiany konta {konto.username}.")
        return redirect("konta:panel_uzytkownicy")


# ---------------------------------------------------------------------------
# Obsługa błędów – bez szczegółów technicznych
# ---------------------------------------------------------------------------

def blad_403(request, exception=None):
    return render(request, "403.html", {"komunikat": KOMUNIKAT_BRAK_DOSTEPU}, status=403)


def blad_404(request, exception=None):
    return render(request, "404.html", status=404)


def blad_500(request):
    return render(request, "500.html", status=500)


def blad_400(request, exception=None):
    return render(request, "400.html", status=400)


def blad_csrf(request, reason=""):
    """Wygasły/brakujący token CSRF – neutralna strona (bez `reason` w odpowiedzi)."""
    from .uprawnienia import zapisz_odmowe

    zapisz_odmowe(request, f"CSRF: {reason}")
    return render(request, "403_csrf.html", status=403)
