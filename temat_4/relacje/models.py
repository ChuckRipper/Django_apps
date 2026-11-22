"""
Relacje między użytkownikami: znajomości (z zaproszeniem) i blokady.

Blokada działa w OBIE strony dla widoczności: jeśli A zablokował B, to B nie widzi
profilu ani postów A i nie może do niego pisać – a A również nie widzi B
(standard w portalach: nikt nie „podgląda” osoby, z którą zerwał kontakt).
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class StatusZnajomosci(models.TextChoices):
    OCZEKUJE = "oczekuje", "Oczekuje"
    ZAAKCEPTOWANA = "zaakceptowana", "Zaakceptowana"


class Znajomosc(models.Model):
    """Zaproszenie od `od` do `do`; po akceptacji – znajomość obustronna."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    od = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="zaproszenia_wyslane")
    do = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="zaproszenia_odebrane")
    status = models.CharField(max_length=15, choices=StatusZnajomosci.choices, default=StatusZnajomosci.OCZEKUJE)
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "znajomość"
        verbose_name_plural = "znajomości"
        constraints = [
            models.UniqueConstraint(fields=["od", "do"], name="znajomosc_unikalna_para"),
            models.CheckConstraint(condition=~Q(od=models.F("do")), name="znajomosc_nie_z_soba"),
        ]

    @classmethod
    def miedzy(cls, a, b):
        """Relacja w dowolnym kierunku między a i b."""
        return cls.objects.filter(Q(od=a, do=b) | Q(od=b, do=a))


class Blokada(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kto = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blokady_nalozone")
    kogo = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blokady_otrzymane")
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "blokada"
        verbose_name_plural = "blokady"
        constraints = [
            models.UniqueConstraint(fields=["kto", "kogo"], name="blokada_unikalna_para"),
            models.CheckConstraint(condition=~Q(kto=models.F("kogo")), name="blokada_nie_siebie"),
        ]
