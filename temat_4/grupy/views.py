"""
Grupy. Opis grupy widzi każdy zalogowany; posty grupy prywatnej – tylko członkowie
(reguła w Post.objects.widoczne_dla, scenariusz 6). Zarządza założyciel.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView

from konta.models import Rola
from konta.uprawnienia import ObiektDlaUzytkownikaMixin, WymaganaRolaMixin, odmow_dostepu, pobierz_lub_odmow
from posty.forms import PostForm
from posty.models import Post, Widocznosc

from .forms import GrupaForm
from .models import Czlonkostwo, Grupa, StatusCzlonkostwa, jest_czlonkiem


class ListaGrupView(WymaganaRolaMixin, View):
    def get(self, request):
        moje = Czlonkostwo.objects.czlonkowskie(request.user).values("grupa")
        return render(request, "grupy/lista.html", {
            "moje": Grupa.objects.widoczne_dla(request.user).filter(pk__in=moje),
            "pozostale": Grupa.objects.widoczne_dla(request.user).exclude(pk__in=moje),
        })


class NowaGrupaView(WymaganaRolaMixin, CreateView):
    minimalna_rola = Rola.UZYTKOWNIK
    form_class = GrupaForm
    template_name = "grupy/formularz.html"

    @transaction.atomic
    def form_valid(self, form):
        form.instance.zalozyciel = self.request.user
        odpowiedz = super().form_valid(form)
        Czlonkostwo.objects.create(grupa=self.object, uzytkownik=self.request.user,
                                   status=StatusCzlonkostwa.CZLONEK)
        return odpowiedz

    def get_success_url(self):
        return reverse("grupy:szczegoly", args=[self.object.pk])


class SzczegolyGrupyView(WymaganaRolaMixin, View):
    """GET – opis + posty (jeśli dozwolone), POST – nowy post w grupie (tylko członek)."""

    def _grupa(self, request, pk):
        return pobierz_lub_odmow(request, Grupa.objects.widoczne_dla(request.user), pk=pk)

    def get(self, request, pk, form=None):
        grupa = self._grupa(request, pk)
        czlonek = jest_czlonkiem(grupa, request.user)
        posty = Post.objects.widoczne_dla(request.user).filter(grupa=grupa).z_licznikami(request.user)
        zalozyciel = grupa.zalozyciel_id == request.user.pk
        return render(request, "grupy/szczegoly.html", {
            "grupa": grupa,
            "czlonek": czlonek,
            "zalozyciel": zalozyciel,
            "oczekuje": Czlonkostwo.objects.filter(grupa=grupa, uzytkownik=request.user,
                                                   status=StatusCzlonkostwa.OCZEKUJE).exists(),
            "strona": Paginator(posty, 10).get_page(request.GET.get("strona")),
            "form": form or PostForm(w_grupie=True),
            "prosby": grupa.czlonkostwa.filter(status=StatusCzlonkostwa.OCZEKUJE).select_related("uzytkownik")
                if zalozyciel else [],
            "czlonkowie": grupa.czlonkostwa.filter(status=StatusCzlonkostwa.CZLONEK).select_related("uzytkownik")
                if (czlonek or not grupa.prywatna) else [],
        })

    def post(self, request, pk):
        grupa = self._grupa(request, pk)
        if not (jest_czlonkiem(grupa, request.user) and request.user.ma_role(Rola.UZYTKOWNIK)):
            odmow_dostepu(request, f"post w grupie {grupa.pk} bez członkostwa")
        form = PostForm(request.POST, request.FILES, w_grupie=True)
        if not form.is_valid():
            return self.get(request, pk, form=form)
        form.instance.autor = request.user
        form.instance.grupa = grupa
        form.instance.widocznosc = Widocznosc.PUBLICZNY  # widoczność = typ grupy
        form.save()
        return redirect("grupy:szczegoly", grupa.pk)


@method_decorator(require_POST, name="dispatch")
class DolaczView(WymaganaRolaMixin, View):
    """Publiczna – od razu członek; prywatna – prośba czekająca na założyciela."""

    def post(self, request, pk):
        grupa = pobierz_lub_odmow(request, Grupa.objects.widoczne_dla(request.user), pk=pk)
        status = StatusCzlonkostwa.OCZEKUJE if grupa.prywatna else StatusCzlonkostwa.CZLONEK
        Czlonkostwo.objects.get_or_create(grupa=grupa, uzytkownik=request.user, defaults={"status": status})
        messages.info(request, "Wysłano prośbę o dołączenie." if grupa.prywatna else "Dołączono do grupy.")
        return redirect("grupy:szczegoly", grupa.pk)


@method_decorator(require_POST, name="dispatch")
class OpuscView(WymaganaRolaMixin, View):
    def post(self, request, pk):
        zbior = Czlonkostwo.objects.filter(uzytkownik=request.user).exclude(grupa__zalozyciel=request.user)
        czl = pobierz_lub_odmow(request, zbior, grupa_id=pk)
        czl.delete()
        messages.info(request, "Opuszczono grupę.")
        return redirect("grupy:lista")


@method_decorator(require_POST, name="dispatch")
class ZarzadzajCzlonkiemView(WymaganaRolaMixin, View):
    """
    Założyciel akceptuje/odrzuca prośby i usuwa członków. Zbiór: członkostwa
    w grupach, których request.user jest założycielem (nie da się ruszyć cudzej grupy).
    """

    akcja = "akceptuj"

    def post(self, request, pk, czl_pk):
        zbior = Czlonkostwo.objects.filter(grupa__zalozyciel=request.user, grupa_id=pk) \
            .exclude(uzytkownik=request.user)
        czl = pobierz_lub_odmow(request, zbior, pk=czl_pk)
        if self.akcja == "akceptuj":
            czl.status = StatusCzlonkostwa.CZLONEK
            czl.save(update_fields=["status"])
        else:
            czl.delete()
        return redirect("grupy:szczegoly", pk)


class UsunGrupeView(ObiektDlaUzytkownikaMixin, DeleteView):
    """Założyciel albo administrator."""

    template_name = "grupy/usun.html"
    context_object_name = "grupa"
    success_url = reverse_lazy("grupy:lista")

    def get_queryset(self):
        return Grupa.objects.zarzadzane_przez(self.request.user)
