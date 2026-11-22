"""Wspólne narzędzia testów bezpieczeństwa."""

import io
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from grupy.models import Czlonkostwo, Grupa, StatusCzlonkostwa
from konta.models import Rola, Uzytkownik
from konta.uprawnienia import KOMUNIKAT_BRAK_DOSTEPU
from posty.models import Post, Widocznosc
from relacje.models import StatusZnajomosci, Znajomosc

HASLO = "Bardzo-Trudne-Haslo-2026"
BACKEND = "konta.backends.TylkoNiezablokowaniBackend"


def obraz(nazwa="zdjecie.png", format_="PNG", rozmiar=(40, 30)):
    bufor = io.BytesIO()
    Image.new("RGB", rozmiar, (200, 50, 50)).save(bufor, format=format_)
    return SimpleUploadedFile(nazwa, bufor.getvalue(), content_type=f"image/{format_.lower()}")


class TestBezpieczenstwa(TestCase):
    """
    Baza testów: konta A, B, C (C nie jest znajomym nikogo), moderator, administrator.
    A i B są znajomymi.
    """

    def setUp(self):
        self.a = self.konto("ala")
        self.b = self.konto("bolek")
        self.c = self.konto("celina")
        self.mod = self.konto("moderator", Rola.MODERATOR)
        self.adm = self.konto("admin", Rola.ADMINISTRATOR)
        Znajomosc.objects.create(od=self.a, do=self.b, status=StatusZnajomosci.ZAAKCEPTOWANA)

    # --- fabryki ---------------------------------------------------------------

    def konto(self, login, rola=Rola.UZYTKOWNIK):
        return Uzytkownik.objects.create_user(username=login, email=f"{login}@example.com",
                                              password=HASLO, rola=rola)

    def post(self, autor, tresc, widocznosc=Widocznosc.PUBLICZNY, grupa=None, **kw):
        return Post.objects.create(autor=autor, tresc=tresc, widocznosc=widocznosc, grupa=grupa, **kw)

    def grupa(self, zalozyciel, prywatna=True, nazwa=None):
        g = Grupa.objects.create(nazwa=nazwa or f"G-{uuid.uuid4().hex[:6]}", prywatna=prywatna,
                                 zalozyciel=zalozyciel)
        Czlonkostwo.objects.create(grupa=g, uzytkownik=zalozyciel, status=StatusCzlonkostwa.CZLONEK)
        return g

    def zaloguj(self, kto):
        self.client.logout()
        self.client.force_login(kto, backend=BACKEND)

    # --- asercje -----------------------------------------------------------------

    @staticmethod
    def porownywalna(odpowiedz):
        """Treść bez wartości zmiennych przy KAŻDYM żądaniu (token CSRF, nonce CSP)."""
        import re
        tresc = odpowiedz.content.decode()
        tresc = re.sub(r'name="csrfmiddlewaretoken" value="[^"]+"', 'name="csrfmiddlewaretoken"', tresc)
        return odpowiedz.status_code, re.sub(r'nonce="[^"]+"', 'nonce=""', tresc)

    def assertOdmowaBezDanych(self, odpowiedz, *zakazane):
        """
        Każdy test odmowy sprawdza trzy rzeczy (wymóg zadania):
          1. status 403,
          2. neutralny komunikat,
          3. brak chronionych danych w odpowiedzi.
        """
        self.assertEqual(odpowiedz.status_code, 403)
        tresc = odpowiedz.content.decode()
        self.assertIn(KOMUNIKAT_BRAK_DOSTEPU, tresc)
        for fragment in zakazane:
            if fragment:
                self.assertNotIn(str(fragment), tresc, f"Wyciek danych: {fragment!r}")
