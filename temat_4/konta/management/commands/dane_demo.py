"""
python manage.py dane_demo [--haslo HASLO]

Tworzy konta testowe (po jednym na rolę + zwykli użytkownicy) i przykładowe treści
pokrywające scenariusze sprawdzane przez prowadzącego. Polecenie jest idempotentne.

Hasło:
  * lokalnie (DEBUG=True) domyślnie "Demo!Haslo2026",
  * na produkcji WYMAGANE: --haslo albo zmienna DJANGO_DEMO_HASLO (min. 12 znaków),
    żeby na publicznym serwerze nie stały konta ze znanym hasłem z README.
"""

import os

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from grupy.models import Czlonkostwo, Grupa, StatusCzlonkostwa
from konta.models import Rola, Uzytkownik
from moderacja.models import Powod, TypZgloszenia, Zgloszenie
from posty.models import Komentarz, Post, Widocznosc
from relacje.models import StatusZnajomosci, Znajomosc
from wiadomosci.models import Rozmowa, Wiadomosc

KONTA = [
    ("admin", Rola.ADMINISTRATOR, "Administrator portalu."),
    ("moderator", Rola.MODERATOR, "Pilnuję porządku."),
    ("anna", Rola.UZYTKOWNIK, "Lubię góry i fotografię."),
    ("bartek", Rola.UZYTKOWNIK, "Programista, kawa, rower."),
    ("celina", Rola.UZYTKOWNIK, "Nowa w Kręgu."),
]


class Command(BaseCommand):
    help = "Tworzy konta testowe i przykładowe treści."

    def add_arguments(self, parser):
        parser.add_argument("--haslo", help="Hasło dla wszystkich kont testowych.")

    @transaction.atomic
    def handle(self, *args, **opcje):
        haslo = opcje.get("haslo") or os.environ.get("DJANGO_DEMO_HASLO")
        if not haslo:
            if not settings.DEBUG:
                raise CommandError("Na produkcji podaj --haslo lub DJANGO_DEMO_HASLO (min. 12 znaków).")
            haslo = "Demo!Haslo2026"
        if not settings.DEBUG and len(haslo) < 12:
            raise CommandError("Hasło kont testowych na produkcji: min. 12 znaków.")
        validate_password(haslo)

        u = {}
        for login, rola, opis in KONTA:
            konto, nowe = Uzytkownik.objects.get_or_create(
                username=login, defaults={"email": f"{login}@example.com", "rola": rola, "opis": opis},
            )
            konto.rola, konto.is_active, konto.zablokowany_do = rola, True, None
            konto.set_password(haslo)
            konto.save()
            u[login] = konto
            self.stdout.write(f"  {'+' if nowe else '='} {login:10} {konto.get_rola_display()}")

        Znajomosc.objects.get_or_create(od=u["anna"], do=u["bartek"],
                                        defaults={"status": StatusZnajomosci.ZAAKCEPTOWANA})
        Znajomosc.objects.get_or_create(od=u["celina"], do=u["anna"])  # oczekujące zaproszenie

        def post(autor, tresc, widocznosc=Widocznosc.PUBLICZNY, grupa=None):
            return Post.objects.get_or_create(autor=autor, tresc=tresc,
                                              defaults={"widocznosc": widocznosc, "grupa": grupa})[0]

        p1 = post(u["anna"], "Cześć wszystkim! To mój pierwszy publiczny post.")
        post(u["anna"], "Tylko dla znajomych: w sobotę idziemy w Beskidy.", Widocznosc.ZNAJOMI)
        post(u["anna"], "Notatka tylko dla mnie: kupić baterie do aparatu.", Widocznosc.TYLKO_JA)
        post(u["bartek"], "Ktoś poleci dobrą książkę o Django?", Widocznosc.PUBLICZNY)
        post(u["bartek"], "Znajomi – mam wolny bilet na koncert w piątek.", Widocznosc.ZNAJOMI)
        Komentarz.objects.get_or_create(post=p1, autor=u["bartek"], defaults={"tresc": "Witaj w Kręgu!"})

        publiczna, _ = Grupa.objects.get_or_create(
            nazwa="Fotografia", defaults={"opis": "Dzielimy się zdjęciami.", "zalozyciel": u["anna"]})
        prywatna, _ = Grupa.objects.get_or_create(
            nazwa="Klub książki", defaults={"opis": "Zamknięta grupa czytelnicza.", "prywatna": True,
                                            "zalozyciel": u["bartek"]})
        for grupa, osoba in ((publiczna, u["anna"]), (publiczna, u["bartek"]), (prywatna, u["bartek"]),
                             (prywatna, u["anna"])):
            Czlonkostwo.objects.get_or_create(grupa=grupa, uzytkownik=osoba,
                                              defaults={"status": StatusCzlonkostwa.CZLONEK})
        Czlonkostwo.objects.get_or_create(grupa=prywatna, uzytkownik=u["celina"],
                                          defaults={"status": StatusCzlonkostwa.OCZEKUJE})
        post(u["bartek"], "W tym miesiącu czytamy „Solaris”.", grupa=prywatna)
        post(u["anna"], "Zachód słońca nad Wisłą.", grupa=publiczna)

        rozmowa = Rozmowa.dla_pary(u["anna"], u["bartek"])
        if not rozmowa.wiadomosci.exists():
            Wiadomosc.objects.create(rozmowa=rozmowa, nadawca=u["anna"], tresc="Hej, idziesz w sobotę?")
            Wiadomosc.objects.create(rozmowa=rozmowa, nadawca=u["bartek"], tresc="Jasne, o której zbiórka?")

        spam = post(u["celina"], "KUP TANIO!!! najlepsze okazje, kliknij link", Widocznosc.PUBLICZNY)
        Zgloszenie.objects.get_or_create(
            typ=TypZgloszenia.POST, post=spam,
            defaults={"zglaszajacy": u["anna"], "uzytkownik": u["celina"], "powod": Powod.SPAM,
                      "kopia_tresci": spam.tresc},
        )
        self.stdout.write(self.style.SUCCESS(
            "Gotowe. Konta: admin, moderator, anna, bartek, celina"
            + (" – hasło: Demo!Haslo2026" if haslo == "Demo!Haslo2026" else " – hasło z parametru.")
        ))
