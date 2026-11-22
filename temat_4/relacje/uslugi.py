"""
Zapytania o relacje – zwracają PODZAPYTANIA (QuerySet z .values()), dzięki czemu
reguły widoczności składają się w jedno zapytanie SQL zamiast pętli w Pythonie.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Blokada, StatusZnajomosci, Znajomosc


def id_znajomych(user):
    """Podzapytanie: ID osób, z którymi `user` ma zaakceptowaną znajomość."""
    Uzytkownik = get_user_model()
    zaakc = StatusZnajomosci.ZAAKCEPTOWANA
    return Uzytkownik.objects.filter(
        Q(zaproszenia_wyslane__do=user, zaproszenia_wyslane__status=zaakc)
        | Q(zaproszenia_odebrane__od=user, zaproszenia_odebrane__status=zaakc)
    ).values("pk")


def znajomi(user):
    return get_user_model().objects.filter(pk__in=id_znajomych(user))


def id_zablokowanych(user):
    """Podzapytanie: ID osób w relacji blokady z `user` (w dowolną stronę)."""
    Uzytkownik = get_user_model()
    return Uzytkownik.objects.filter(
        Q(blokady_otrzymane__kto=user) | Q(blokady_nalozone__kogo=user)
    ).values("pk")


def czy_znajomi(a, b) -> bool:
    return Znajomosc.miedzy(a, b).filter(status=StatusZnajomosci.ZAAKCEPTOWANA).exists()


def czy_blokada(a, b) -> bool:
    return Blokada.objects.filter(Q(kto=a, kogo=b) | Q(kto=b, kogo=a)).exists()


def widoczni_dla(user):
    """Użytkownicy, których profil `user` może oglądać (aktywni, bez blokady)."""
    if not (user.is_authenticated and user.is_active):
        return get_user_model().objects.none()
    return get_user_model().objects.filter(is_active=True).exclude(pk__in=id_zablokowanych(user))
