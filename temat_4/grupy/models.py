"""Grupy publiczne (dołączanie bez akceptacji) i prywatne (prośba + akceptacja założyciela)."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class GrupaQuerySet(models.QuerySet):
    def widoczne_dla(self, user):
        """Nazwa i opis każdej grupy są widoczne (by można było poprosić o dołączenie);
        treści grupy prywatnej chroni Post.objects.widoczne_dla."""
        if not (user.is_authenticated and user.is_active):
            return self.none()
        return self.all()

    def zarzadzane_przez(self, user):
        """Zarządza założyciel; administrator może usuwać grupy."""
        if not (user.is_authenticated and user.is_active):
            return self.none()
        if user.jest_administratorem:
            return self.all()
        return self.filter(zalozyciel=user)


class Grupa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nazwa = models.CharField("nazwa", max_length=100, unique=True)
    opis = models.TextField("opis", max_length=2000, blank=True)
    prywatna = models.BooleanField("grupa prywatna", default=False,
                                   help_text="Treści widzą tylko członkowie; dołączenie wymaga akceptacji.")
    zalozyciel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="zalozone_grupy")
    utworzono = models.DateTimeField(auto_now_add=True)

    objects = GrupaQuerySet.as_manager()

    class Meta:
        ordering = ["nazwa"]
        verbose_name = "grupa"
        verbose_name_plural = "grupy"

    def __str__(self) -> str:
        return self.nazwa


class StatusCzlonkostwa(models.TextChoices):
    OCZEKUJE = "oczekuje", "Prośba oczekuje"
    CZLONEK = "czlonek", "Członek"


class CzlonkostwoQuerySet(models.QuerySet):
    def czlonkowskie(self, user):
        return self.filter(uzytkownik=user, status=StatusCzlonkostwa.CZLONEK)


class Czlonkostwo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grupa = models.ForeignKey(Grupa, on_delete=models.CASCADE, related_name="czlonkostwa")
    uzytkownik = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="czlonkostwa")
    status = models.CharField(max_length=10, choices=StatusCzlonkostwa.choices)
    utworzono = models.DateTimeField(auto_now_add=True)

    objects = CzlonkostwoQuerySet.as_manager()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["grupa", "uzytkownik"], name="czlonkostwo_unikalne")]


def jest_czlonkiem(grupa, user) -> bool:
    return Czlonkostwo.objects.filter(grupa=grupa, uzytkownik=user, status=StatusCzlonkostwa.CZLONEK).exists()
