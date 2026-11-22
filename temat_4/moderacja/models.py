"""
Zgłoszenia i historia działań moderatorów.

Moderator widzi TYLKO zgłoszoną treść – przez zgłoszenie (zapisaną kopię treści
z chwili zgłoszenia), nie przez zwykłe adresy postów czy rozmów.
"""

import uuid

from django.conf import settings
from django.db import models


class TypZgloszenia(models.TextChoices):
    POST = "post", "Post"
    KOMENTARZ = "komentarz", "Komentarz"
    UZYTKOWNIK = "uzytkownik", "Użytkownik"


class Powod(models.TextChoices):
    SPAM = "spam", "Spam"
    NEKANIE = "nekanie", "Nękanie lub mowa nienawiści"
    NIEODPOWIEDNIE = "nieodpowiednie", "Treść nieodpowiednia"
    PODSZYWANIE = "podszywanie", "Podszywanie się"
    INNE = "inne", "Inne"


class StatusZgloszenia(models.TextChoices):
    NOWE = "nowe", "Nowe"
    ROZPATRZONE = "rozpatrzone", "Rozpatrzone"
    ODRZUCONE = "odrzucone", "Odrzucone"


class ZgloszenieQuerySet(models.QuerySet):
    def dla_moderatora(self, user):
        from konta.models import Rola
        if not (user.is_authenticated and user.ma_role(Rola.MODERATOR)):
            return self.none()
        return self.all()


class Zgloszenie(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zglaszajacy = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    related_name="zgloszenia_wyslane")
    typ = models.CharField(max_length=12, choices=TypZgloszenia.choices)
    post = models.ForeignKey("posty.Post", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    komentarz = models.ForeignKey("posty.Komentarz", on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="+")
    uzytkownik = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="zgloszenia_otrzymane",
                                   help_text="Zgłoszony użytkownik albo autor zgłoszonej treści.")
    powod = models.CharField("powód", max_length=20, choices=Powod.choices)
    opis = models.TextField("opis", max_length=1000, blank=True)
    kopia_tresci = models.TextField(blank=True, help_text="Treść w chwili zgłoszenia (dowód).")
    status = models.CharField(max_length=12, choices=StatusZgloszenia.choices, default=StatusZgloszenia.NOWE)
    utworzono = models.DateTimeField(auto_now_add=True)

    objects = ZgloszenieQuerySet.as_manager()

    class Meta:
        ordering = ["status", "-utworzono"]
        verbose_name = "zgłoszenie"
        verbose_name_plural = "zgłoszenia"


class RodzajAkcji(models.TextChoices):
    USUNIECIE = "usuniecie", "Usunięcie treści"
    UKRYCIE = "ukrycie", "Ukrycie treści"
    ODRZUCENIE = "odrzucenie", "Odrzucenie zgłoszenia"
    BLOKADA = "blokada", "Blokada konta"
    ODBLOKOWANIE = "odblokowanie", "Zdjęcie blokady"
    ZMIANA_ROLI = "zmiana_roli", "Zmiana roli"


class AkcjaModeratora(models.Model):
    """Historia działań (kto, co, kiedy) – tylko dopisywana, nigdy edytowana."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wykonal = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    akcja = models.CharField(max_length=15, choices=RodzajAkcji.choices)
    zgloszenie = models.ForeignKey(Zgloszenie, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="akcje")
    cel = models.CharField(max_length=200, help_text="Czego dotyczyła akcja (np. login, typ treści).")
    uzasadnienie = models.CharField(max_length=500, blank=True)
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-utworzono"]
        verbose_name = "akcja moderatora"
        verbose_name_plural = "historia działań"
