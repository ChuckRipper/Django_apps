"""
Prywatne rozmowy 1:1. Czytać mogą WYŁĄCZNIE dwaj uczestnicy – nie ma wyjątku
dla moderatora ani administratora, a modele nie są zarejestrowane w panelu admina.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class RozmowaQuerySet(models.QuerySet):
    def dostepne_dla(self, user):
        if not (user.is_authenticated and user.is_active and not user.jest_zablokowany):
            return self.none()
        return self.filter(Q(uczestnik_a=user) | Q(uczestnik_b=user))


class Rozmowa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Para zapisywana w ustalonej kolejności (mniejsze UUID jako `a`) – jedna rozmowa na parę.
    uczestnik_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    uczestnik_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    utworzono = models.DateTimeField(auto_now_add=True)
    ostatnia_wiadomosc = models.DateTimeField(auto_now_add=True)

    objects = RozmowaQuerySet.as_manager()

    class Meta:
        ordering = ["-ostatnia_wiadomosc"]
        constraints = [models.UniqueConstraint(fields=["uczestnik_a", "uczestnik_b"], name="rozmowa_unikalna_para")]

    @classmethod
    def dla_pary(cls, x, y):
        a, b = sorted([x, y], key=lambda u: str(u.pk))
        rozmowa, _ = cls.objects.get_or_create(uczestnik_a=a, uczestnik_b=b)
        return rozmowa

    def rozmowca(self, user):
        return self.uczestnik_b if self.uczestnik_a_id == user.pk else self.uczestnik_a


class Wiadomosc(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rozmowa = models.ForeignKey(Rozmowa, on_delete=models.CASCADE, related_name="wiadomosci")
    nadawca = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    tresc = models.TextField("wiadomość", max_length=2000)
    wyslano = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["wyslano"]
