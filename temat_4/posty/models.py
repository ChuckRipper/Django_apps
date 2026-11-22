"""
Posty, komentarze i polubienia.

Reguły dostępu są WYŁĄCZNIE w metodach QuerySet – widoki nigdy nie robią
`Post.objects.get(pk=...)`, tylko `Post.objects.widoczne_dla(user).get(pk=...)`.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Exists, OuterRef, Q

from relacje.uslugi import id_zablokowanych, id_znajomych


def _aktywny(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active and not user.jest_zablokowany)


def sciezka_zdjecia(instancja, nazwa_pliku: str) -> str:
    return f"posty/{uuid.uuid4().hex}.webp"


class Widocznosc(models.TextChoices):
    PUBLICZNY = "publiczny", "Publiczny"
    ZNAJOMI = "znajomi", "Tylko znajomi"
    TYLKO_JA = "tylko_ja", "Tylko ja"


class PostQuerySet(models.QuerySet):
    def widoczne_dla(self, user):
        """
        Post jest widoczny, gdy NIE ma blokady między autorem a użytkownikiem oraz:
          * post poza grupą: autor to ja, LUB publiczny, LUB „znajomi” i autor jest znajomym,
          * post w grupie: grupa publiczna, LUB jestem członkiem grupy prywatnej,
        a do tego post nie jest ukryty przez moderację (autor nadal go widzi).
        Moderator i administrator NIE mają tu wyjątków – treści prywatne widzą tylko
        w ramach zgłoszenia (aplikacja `moderacja`).
        """
        if not _aktywny(user):
            return self.none()
        from grupy.models import Czlonkostwo  # import lokalny: unikamy cyklu

        czlonkostwa = Czlonkostwo.objects.czlonkowskie(user).values("grupa")
        poza_grupa = Q(grupa__isnull=True) & (
            Q(autor=user)
            | Q(widocznosc=Widocznosc.PUBLICZNY)
            | Q(widocznosc=Widocznosc.ZNAJOMI, autor__in=id_znajomych(user))
        )
        w_grupie = Q(grupa__isnull=False) & (Q(grupa__prywatna=False) | Q(grupa__in=czlonkostwa))
        return (
            self.filter(poza_grupa | w_grupie)
            .filter(Q(ukryty=False) | Q(autor=user))
            .exclude(autor__in=id_zablokowanych(user))
        )

    def edytowalne_przez(self, user):
        """Edytować może tylko autor (i tylko gdy nadal widzi post)."""
        return self.widoczne_dla(user).filter(autor=user)

    def usuwalne_przez(self, user):
        """Usunąć może autor albo założyciel grupy, w której post opublikowano."""
        return self.widoczne_dla(user).filter(Q(autor=user) | Q(grupa__zalozyciel=user))

    def z_licznikami(self, user):
        return self.select_related("autor", "grupa").annotate(
            liczba_polubien=models.Count("polubienia", distinct=True),
            liczba_komentarzy=models.Count("komentarze", distinct=True),
            polubiony=Exists(Polubienie.objects.filter(post=OuterRef("pk"), uzytkownik=user)),
        ).order_by("-utworzono")  # przy annotate(Count) Django pomija Meta.ordering


class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # autor ustawiany WYŁĄCZNIE w widoku z request.user (nie ma go w formularzu).
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posty")
    tresc = models.TextField("treść", max_length=5000)
    obraz = models.ImageField("zdjęcie", upload_to=sciezka_zdjecia, blank=True)
    widocznosc = models.CharField("widoczność", max_length=10, choices=Widocznosc.choices,
                                  default=Widocznosc.ZNAJOMI)
    grupa = models.ForeignKey("grupy.Grupa", on_delete=models.CASCADE, null=True, blank=True,
                              related_name="posty")
    ukryty = models.BooleanField("ukryty przez moderację", default=False)
    utworzono = models.DateTimeField(auto_now_add=True)
    zmieniono = models.DateTimeField(auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-utworzono"]
        verbose_name = "post"
        verbose_name_plural = "posty"

    def __str__(self) -> str:
        return f"Post {self.pk}"


class KomentarzQuerySet(models.QuerySet):
    def widoczne_dla(self, user):
        if not _aktywny(user):
            return self.none()
        return (
            self.filter(post__in=Post.objects.widoczne_dla(user))
            .filter(Q(ukryty=False) | Q(autor=user))
            .exclude(autor__in=id_zablokowanych(user))
        )

    def usuwalne_przez(self, user):
        """Komentarz usuwa jego autor albo autor posta."""
        return self.widoczne_dla(user).filter(Q(autor=user) | Q(post__autor=user))


class Komentarz(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="komentarze")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="komentarze")
    tresc = models.TextField("komentarz", max_length=1000)
    ukryty = models.BooleanField(default=False)
    utworzono = models.DateTimeField(auto_now_add=True)

    objects = KomentarzQuerySet.as_manager()

    class Meta:
        ordering = ["utworzono"]
        verbose_name = "komentarz"
        verbose_name_plural = "komentarze"

    def __str__(self) -> str:
        return f"Komentarz {self.pk}"


class Polubienie(models.Model):
    """Jedno polubienie na użytkownika na post – pilnuje tego baza (UniqueConstraint)."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="polubienia")
    uzytkownik = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="polubienia")
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "uzytkownik"], name="jedno_polubienie")]
