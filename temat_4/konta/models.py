"""
Model użytkownika portalu.

* klucz główny UUID – identyfikatora nie da się zgadnąć ani „przewinąć” (1, 2, 3...),
* rola nadawana WYŁĄCZNIE przez administratora (nigdy z formularza rejestracji),
* blokada konta (`zablokowany_do`) – nakładana przez moderatora/administratora;
  zablokowany nie zaloguje się (konta.backends) ani nie opublikuje treści.
"""

import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


class Rola(models.IntegerChoices):
    """Role rosną z uprawnieniami – porównanie `>=` oznacza „co najmniej”."""

    UZYTKOWNIK = 10, "Użytkownik"
    MODERATOR = 20, "Moderator"
    ADMINISTRATOR = 30, "Administrator"


def sciezka_avatara(instancja, nazwa_pliku: str) -> str:
    # Nazwa pliku nigdy nie pochodzi od użytkownika (path traversal, kolizje, wycieki nazw).
    return f"avatary/{uuid.uuid4().hex}.webp"


class UzytkownikQuerySet(models.QuerySet):
    def aktywni(self):
        teraz = timezone.now()
        return self.filter(is_active=True).filter(
            models.Q(zablokowany_do__isnull=True) | models.Q(zablokowany_do__lte=teraz)
        )


class UzytkownikManager(UserManager.from_queryset(UzytkownikQuerySet)):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Superuser Django = Administrator portalu (spójność uprawnień).
        extra_fields.setdefault("rola", Rola.ADMINISTRATOR)
        return super().create_superuser(username, email, password, **extra_fields)


class Uzytkownik(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("adres e-mail", unique=True)
    rola = models.PositiveSmallIntegerField("rola", choices=Rola.choices, default=Rola.UZYTKOWNIK)

    # Profil (edytowany wyłącznie przez właściciela pod adresem bez ID).
    avatar = models.ImageField("avatar", upload_to=sciezka_avatara, blank=True)
    opis = models.TextField("o mnie", max_length=1000, blank=True)
    miasto = models.CharField("miasto", max_length=100, blank=True)
    data_urodzenia = models.DateField("data urodzenia", null=True, blank=True)

    # Blokada konta (moderacja). null = brak blokady.
    zablokowany_do = models.DateTimeField("zablokowany do", null=True, blank=True)

    objects = UzytkownikManager()

    class Meta:
        verbose_name = "użytkownik"
        verbose_name_plural = "użytkownicy"
        ordering = ["username"]

    def __str__(self) -> str:
        return self.username

    # --- Uprawnienia ---------------------------------------------------------

    @property
    def jest_zablokowany(self) -> bool:
        return self.zablokowany_do is not None and self.zablokowany_do > timezone.now()

    def ma_role(self, minimalna: int) -> bool:
        return self.is_active and not self.jest_zablokowany and self.rola >= minimalna

    @property
    def jest_moderatorem(self) -> bool:
        return self.ma_role(Rola.MODERATOR)

    @property
    def jest_administratorem(self) -> bool:
        return self.ma_role(Rola.ADMINISTRATOR)
