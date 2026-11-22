"""
Wiadomości prywatne. Zbiór: Rozmowa.objects.dostepne_dla(user) – tylko uczestnicy.
Moderator/administrator nie mają wyjątku (scenariusze 5 i 10). Nie można pisać
do osoby, z którą jest blokada – w dowolną stronę (scenariusz 12).
"""

from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from konta.models import Rola
from konta.uprawnienia import WymaganaRolaMixin, odmow_dostepu, pobierz_lub_odmow
from relacje.uslugi import czy_blokada, widoczni_dla

from .forms import WiadomoscForm
from .models import Rozmowa


class ListaRozmowView(WymaganaRolaMixin, View):
    def get(self, request):
        rozmowy = Rozmowa.objects.dostepne_dla(request.user).select_related("uczestnik_a", "uczestnik_b")
        return render(request, "wiadomosci/lista.html", {
            "rozmowy": [(r, r.rozmowca(request.user)) for r in rozmowy],
        })


class RozmowaView(WymaganaRolaMixin, View):
    def _rozmowa(self, request, pk):
        return pobierz_lub_odmow(request, Rozmowa.objects.dostepne_dla(request.user), pk=pk)

    def get(self, request, pk, form=None):
        rozmowa = self._rozmowa(request, pk)
        rozmowca = rozmowa.rozmowca(request.user)
        return render(request, "wiadomosci/rozmowa.html", {
            "rozmowa": rozmowa,
            "rozmowca": rozmowca,
            "wiadomosci": rozmowa.wiadomosci.select_related("nadawca"),
            "zablokowana": czy_blokada(request.user, rozmowca),
            "form": form or WiadomoscForm(),
        })

    @transaction.atomic
    def post(self, request, pk):
        rozmowa = self._rozmowa(request, pk)
        rozmowca = rozmowa.rozmowca(request.user)
        if not request.user.ma_role(Rola.UZYTKOWNIK) or czy_blokada(request.user, rozmowca) \
                or not rozmowca.is_active:
            odmow_dostepu(request, f"wiadomość w rozmowie {rozmowa.pk} – blokada")
        form = WiadomoscForm(request.POST)
        if not form.is_valid():
            return self.get(request, pk, form=form)
        form.instance.rozmowa = rozmowa
        form.instance.nadawca = request.user
        form.save()
        Rozmowa.objects.filter(pk=rozmowa.pk).update(ostatnia_wiadomosc=timezone.now())
        return redirect("wiadomosci:rozmowa", rozmowa.pk)


@method_decorator(require_POST, name="dispatch")
class NowaRozmowaView(WymaganaRolaMixin, View):
    """Otwiera (lub tworzy) rozmowę z osobą widoczną dla mnie – nie z zablokowaną."""

    minimalna_rola = Rola.UZYTKOWNIK

    def post(self, request, username):
        cel = pobierz_lub_odmow(request, widoczni_dla(request.user).exclude(pk=request.user.pk),
                                username=username)
        return redirect("wiadomosci:rozmowa", Rozmowa.dla_pary(request.user, cel).pk)
