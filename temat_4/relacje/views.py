"""
Znajomi i blokady. Wszystkie akcje zmieniające dane są tylko POST (+ CSRF).
Osobę-cel zawsze wybieramy ze zbioru `widoczni_dla(user)` – zablokowanej osobie
nie da się wysłać zaproszenia, a ona nie dowie się, że jest zablokowana
(dostaje to samo 403 co przy nieistniejącym koncie).
"""

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views import View
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

from konta.uprawnienia import WymaganaRolaMixin, pobierz_lub_odmow, zapisz_zdarzenie

from .models import Blokada, StatusZnajomosci, Znajomosc
from .uslugi import widoczni_dla, znajomi


class ZnajomiView(WymaganaRolaMixin, View):
    def get(self, request):
        return render(request, "relacje/znajomi.html", {
            "znajomi": znajomi(request.user).only("id", "username", "avatar"),
            "odebrane": Znajomosc.objects.filter(do=request.user, status=StatusZnajomosci.OCZEKUJE)
                .select_related("od"),
            "wyslane": Znajomosc.objects.filter(od=request.user, status=StatusZnajomosci.OCZEKUJE)
                .select_related("do"),
            "blokady": Blokada.objects.filter(kto=request.user).select_related("kogo"),
        })


@method_decorator(require_POST, name="dispatch")
class ZaprosView(WymaganaRolaMixin, View):
    def post(self, request, username):
        cel = pobierz_lub_odmow(request, widoczni_dla(request.user).exclude(pk=request.user.pk),
                                username=username)
        istniejaca = Znajomosc.miedzy(request.user, cel).first()
        if istniejaca is None:
            Znajomosc.objects.create(od=request.user, do=cel)
            messages.success(request, f"Wysłano zaproszenie do {cel.username}.")
        elif istniejaca.do_id == request.user.pk and istniejaca.status == StatusZnajomosci.OCZEKUJE:
            istniejaca.status = StatusZnajomosci.ZAAKCEPTOWANA  # wzajemne zaproszenie = akceptacja
            istniejaca.save(update_fields=["status"])
            messages.success(request, f"Jesteście teraz znajomymi z {cel.username}.")
        return redirect("konta:profil", cel.username)


@method_decorator(require_POST, name="dispatch")
class OdpowiedzNaZaproszenieView(WymaganaRolaMixin, View):
    """Odpowiada wyłącznie ADRESAT zaproszenia – zbiór: zaproszenia do mnie."""

    akceptuj = True

    def post(self, request, pk):
        zbior = Znajomosc.objects.filter(do=request.user, status=StatusZnajomosci.OCZEKUJE)
        zaproszenie = pobierz_lub_odmow(request, zbior, pk=pk)
        if self.akceptuj:
            zaproszenie.status = StatusZnajomosci.ZAAKCEPTOWANA
            zaproszenie.save(update_fields=["status"])
            messages.success(request, "Zaproszenie przyjęte.")
        else:
            zaproszenie.delete()
            messages.info(request, "Zaproszenie odrzucone.")
        return redirect("relacje:znajomi")


@method_decorator(require_POST, name="dispatch")
class UsunZnajomoscView(WymaganaRolaMixin, View):
    """Usuwa znajomość albo anuluje własne zaproszenie – tylko relacje, w których biorę udział."""

    def post(self, request, pk):
        zbior = Znajomosc.objects.filter(Q(od=request.user) | Q(do=request.user))
        pobierz_lub_odmow(request, zbior, pk=pk).delete()
        messages.info(request, "Usunięto.")
        return redirect("relacje:znajomi")


@method_decorator(require_POST, name="dispatch")
class ZablokujView(WymaganaRolaMixin, View):
    @transaction.atomic
    def post(self, request, username):
        cel = pobierz_lub_odmow(request, widoczni_dla(request.user).exclude(pk=request.user.pk),
                                username=username)
        Blokada.objects.get_or_create(kto=request.user, kogo=cel)
        Znajomosc.miedzy(request.user, cel).delete()  # blokada kończy znajomość
        zapisz_zdarzenie(request, f"BLOKADA OSOBY {cel.username}")
        messages.info(request, f"Zablokowano {cel.username}.")
        return redirect("relacje:znajomi")


@method_decorator(require_POST, name="dispatch")
class OdblokujView(WymaganaRolaMixin, View):
    def post(self, request, pk):
        pobierz_lub_odmow(request, Blokada.objects.filter(kto=request.user), pk=pk).delete()
        messages.info(request, "Blokada zdjęta.")
        return redirect("relacje:znajomi")
