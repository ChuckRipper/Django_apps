"""
Warstwa uprawnień – JEDYNE miejsce, w którym zapadają decyzje o dostępie.

Zasady (wymagania zadania):
  1. Obiekty pobieramy wyłącznie z zawężonego zbioru (metody QuerySet
     `widoczne_dla`, `edytowalne_przez`, `dostepne_dla`) – nigdy
     `Model.objects.get(pk=pk)` / `get_object_or_404(Model, pk=pk)`.
  2. Odmowa = neutralna strona 403 „Ta treść nie jest przeznaczona dla Ciebie.”
     bez tytułu, autora ani fragmentu treści.
  3. „Nie istnieje” i „nie dla Ciebie” dają IDENTYCZNĄ odpowiedź (403) –
     nie da się sprawdzić, czy obiekt o danym UUID w ogóle istnieje.
  4. Każda odmowa trafia do logu audytu (kto, kiedy, IP, jaki adres/obiekt).
"""

import logging
from functools import wraps
from typing import NoReturn

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured, PermissionDenied, ValidationError
from django.http import Http404

logger = logging.getLogger("bezpieczenstwo")

KOMUNIKAT_BRAK_DOSTEPU = "Ta treść nie jest przeznaczona dla Ciebie."


def adres_ip(request) -> str:
    """REMOTE_ADDR, nie X-Forwarded-For (ten nagłówek może sfałszować klient)."""
    return request.META.get("REMOTE_ADDR", "?")


def _kto(request) -> str:
    u = getattr(request, "user", None)
    return u.get_username() if u is not None and u.is_authenticated else "anonim"


def zapisz_odmowe(request, powod: str) -> None:
    """Szczegóły odmowy trafiają TYLKO do logu serwera – nigdy do odpowiedzi."""
    logger.warning(
        "ODMOWA DOSTĘPU | użytkownik=%s | ip=%s | %s %s | powód: %s",
        _kto(request), adres_ip(request), request.method, request.path, powod,
    )


def zapisz_zdarzenie(request, opis: str) -> None:
    """Zdarzenia istotne dla bezpieczeństwa (zmiana roli, blokada, moderacja)."""
    logger.info("ZDARZENIE | użytkownik=%s | ip=%s | %s", _kto(request), adres_ip(request), opis)


def odmow_dostepu(request, powod: str) -> NoReturn:
    """Loguje i przerywa żądanie – Django wyrenderuje neutralne 403 (handler403)."""
    zapisz_odmowe(request, powod)
    raise PermissionDenied(KOMUNIKAT_BRAK_DOSTEPU)


def pobierz_lub_odmow(request, queryset, **filtry):
    """
    Odpowiednik get_object_or_404 dla ZAWĘŻONEGO zbioru: brak obiektu
    (bo nie istnieje ALBO nie jest dla tego użytkownika) => to samo 403.
    """
    try:
        return queryset.get(**filtry)
    except (queryset.model.DoesNotExist, ValidationError, ValueError):
        odmow_dostepu(request, f"brak obiektu {queryset.model.__name__} {filtry} w zbiorze użytkownika")


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------

def wymagana_rola(minimalna_rola: int):
    """Dekorator widoków funkcyjnych: zalogowany + rola ≥ minimalna."""

    def dekorator(widok):
        @wraps(widok)
        def opakowanie(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not request.user.ma_role(minimalna_rola):
                odmow_dostepu(request, f"wymagana rola {minimalna_rola}, ma {request.user.rola}")
            return widok(request, *args, **kwargs)

        return opakowanie

    return dekorator


class WymaganaRolaMixin(LoginRequiredMixin):
    """Widoki klasowe: zalogowany (inaczej – logowanie) i rola ≥ `minimalna_rola`."""

    minimalna_rola: int | None = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.minimalna_rola is not None and not request.user.ma_role(self.minimalna_rola):
            odmow_dostepu(request, f"wymagana rola {self.minimalna_rola}, ma {request.user.rola}")
        return super().dispatch(request, *args, **kwargs)


class ObiektDlaUzytkownikaMixin(WymaganaRolaMixin):
    """
    Bezpieczny domyślnie DetailView/UpdateView/DeleteView:
      * `get_queryset()` MUSI być nadpisane i zwrócić zbiór zawężony do użytkownika
        (zapomnienie = błąd od razu, a nie cicha dziura IDOR),
      * obiekt spoza zbioru => 403 (identyczne dla nieistniejącego).
    Działa tak samo dla GET i POST (dispatch -> get_object w obu metodach).
    """

    def get_queryset(self):
        raise ImproperlyConfigured(
            f"{self.__class__.__name__} musi nadpisać get_queryset() i zwrócić "
            "zbiór zawężony do użytkownika (np. Post.objects.widoczne_dla(user))."
        )

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except Http404:
            odmow_dostepu(request=self.request, powod=f"obiekt {self.kwargs} poza zbiorem użytkownika")
