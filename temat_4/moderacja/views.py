"""
Moderacja.

* Zgłosić można tylko to, co się widzi (zbiory widoczne_dla) – zgłoszenie nie jest
  furtką do sprawdzania istnienia cudzych treści.
* Moderator widzi WYŁĄCZNIE zgłoszoną treść, przez zgłoszenie (kopia z chwili
  zgłoszenia + bieżący stan obiektu). Nie dostaje dostępu do postów „znajomi”/„tylko ja”
  ani do rozmów przez ich zwykłe adresy.
* Moderator nie zablokuje konta o roli równej lub wyższej od swojej.
* Każda decyzja => AkcjaModeratora (historia) + log audytu.
"""

from datetime import timedelta

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from konta.models import Rola
from konta.uprawnienia import WymaganaRolaMixin, odmow_dostepu, pobierz_lub_odmow, zapisz_zdarzenie
from posty.models import Komentarz, Post
from relacje.uslugi import widoczni_dla

from .forms import DecyzjaForm, ZgloszenieForm
from .models import AkcjaModeratora, RodzajAkcji, StatusZgloszenia, TypZgloszenia, Zgloszenie


class ZglosView(WymaganaRolaMixin, View):
    """GET – formularz, POST – zapis. Obiekt zawsze ze zbioru widocznego dla zgłaszającego."""

    def _cel(self, request, typ, ident):
        if typ == TypZgloszenia.POST:
            post = pobierz_lub_odmow(request, Post.objects.widoczne_dla(request.user), pk=ident)
            return {"post": post, "uzytkownik": post.autor}, post.tresc
        if typ == TypZgloszenia.KOMENTARZ:
            kom = pobierz_lub_odmow(request, Komentarz.objects.widoczne_dla(request.user), pk=ident)
            return {"komentarz": kom, "uzytkownik": kom.autor}, kom.tresc
        if typ == TypZgloszenia.UZYTKOWNIK:
            osoba = pobierz_lub_odmow(request, widoczni_dla(request.user).exclude(pk=request.user.pk),
                                      username=ident)
            return {"uzytkownik": osoba}, f"Profil: {osoba.username}\n{osoba.opis}"
        odmow_dostepu(request, f"nieznany typ zgłoszenia {typ}")

    def get(self, request, typ, ident):
        self._cel(request, typ, ident)
        return render(request, "moderacja/zglos.html", {"form": ZgloszenieForm(), "typ": typ})

    def post(self, request, typ, ident):
        cel, kopia = self._cel(request, typ, ident)
        form = ZgloszenieForm(request.POST)
        if not form.is_valid():
            return render(request, "moderacja/zglos.html", {"form": form, "typ": typ})
        zgl = form.save(commit=False)
        zgl.zglaszajacy = request.user
        zgl.typ = typ
        zgl.kopia_tresci = kopia[:5000]
        for pole, wartosc in cel.items():
            setattr(zgl, pole, wartosc)
        zgl.save()
        messages.success(request, "Dziękujemy – zgłoszenie trafiło do moderatorów.")
        return redirect("posty:tablica")


class PanelModeratoraView(WymaganaRolaMixin, ListView):
    minimalna_rola = Rola.MODERATOR
    template_name = "moderacja/panel.html"
    context_object_name = "zgloszenia"
    paginate_by = 20

    def get_queryset(self):
        status = self.request.GET.get("status", StatusZgloszenia.NOWE)
        if status not in StatusZgloszenia.values:
            status = StatusZgloszenia.NOWE
        return Zgloszenie.objects.dla_moderatora(self.request.user).filter(status=status) \
            .select_related("zglaszajacy", "uzytkownik")

    def get_context_data(self, **kwargs):
        kontekst = super().get_context_data(**kwargs)
        kontekst["status"] = self.request.GET.get("status", StatusZgloszenia.NOWE)
        kontekst["Statusy"] = StatusZgloszenia
        return kontekst


class ZgloszenieView(WymaganaRolaMixin, View):
    minimalna_rola = Rola.MODERATOR

    def _zgloszenie(self, request, pk):
        return pobierz_lub_odmow(request, Zgloszenie.objects.dla_moderatora(request.user)
                                 .select_related("post", "komentarz", "uzytkownik", "zglaszajacy"), pk=pk)

    def get(self, request, pk, form=None):
        zgl = self._zgloszenie(request, pk)
        return render(request, "moderacja/zgloszenie.html", {
            "zgl": zgl,
            "form": form or DecyzjaForm(),
            "akcje": zgl.akcje.select_related("wykonal"),
        })

    @transaction.atomic
    def post(self, request, pk):
        zgl = self._zgloszenie(request, pk)
        form = DecyzjaForm(request.POST)
        if not form.is_valid() or zgl.status != StatusZgloszenia.NOWE:
            messages.error(request, "Nie można zapisać decyzji.")
            return self.get(request, pk, form=form)
        akcja = form.cleaned_data["akcja"]
        uzasadnienie = form.cleaned_data["uzasadnienie"]
        obiekt = zgl.post or zgl.komentarz
        opis_celu = f"{zgl.get_typ_display()} {zgl.uzytkownik or ''}".strip()

        if akcja == "odrzuc":
            zgl.status = StatusZgloszenia.ODRZUCONE
            rodzaj = RodzajAkcji.ODRZUCENIE
        elif akcja in ("ukryj", "usun"):
            if obiekt is None:
                messages.error(request, "Ta treść już nie istnieje albo zgłoszenie dotyczy osoby.")
                return self.get(request, pk, form=form)
            if akcja == "ukryj":
                obiekt.ukryty = True
                obiekt.save(update_fields=["ukryty"])
                rodzaj = RodzajAkcji.UKRYCIE
            else:
                if getattr(obiekt, "obraz", None):
                    obiekt.obraz.delete(save=False)
                obiekt.delete()
                rodzaj = RodzajAkcji.USUNIECIE
            zgl.status = StatusZgloszenia.ROZPATRZONE
        else:  # zablokuj
            autor = zgl.uzytkownik
            if autor is None or autor.rola >= request.user.rola:
                odmow_dostepu(request, f"blokada konta o równej/wyższej roli w zgłoszeniu {zgl.pk}")
            dni = form.cleaned_data.get("dni") or 3
            autor.zablokowany_do = timezone.now() + timedelta(days=dni)
            autor.save(update_fields=["zablokowany_do"])
            zgl.status = StatusZgloszenia.ROZPATRZONE
            rodzaj = RodzajAkcji.BLOKADA
            uzasadnienie = f"{dni} dni. {uzasadnienie}".strip()

        zgl.save(update_fields=["status"])
        AkcjaModeratora.objects.create(wykonal=request.user, akcja=rodzaj, zgloszenie=zgl,
                                       cel=opis_celu[:200], uzasadnienie=uzasadnienie[:500])
        zapisz_zdarzenie(request, f"MODERACJA {rodzaj} zgłoszenie={zgl.pk} cel={opis_celu}")
        messages.success(request, "Decyzja zapisana.")
        return redirect("moderacja:panel")


class ZdjecieZgloszeniaView(WymaganaRolaMixin, View):
    """Zdjęcie ZGŁOSZONEGO posta – dla moderatora wyłącznie w kontekście zgłoszenia."""

    minimalna_rola = Rola.MODERATOR

    def get(self, request, pk):
        from posty.views_pliki import _odpowiedz_pliku

        zgl = pobierz_lub_odmow(request, Zgloszenie.objects.dla_moderatora(request.user)
                                .filter(post__isnull=False).exclude(post__obraz=""), pk=pk)
        return _odpowiedz_pliku(zgl.post.obraz)


class HistoriaView(WymaganaRolaMixin, ListView):
    minimalna_rola = Rola.MODERATOR
    template_name = "moderacja/historia.html"
    context_object_name = "akcje"
    paginate_by = 30

    def get_queryset(self):
        return AkcjaModeratora.objects.select_related("wykonal", "zgloszenie")
