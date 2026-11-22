"""Testy poza tabelą scenariuszy: CSRF, nagłówki, pliki, moderacja, grupy, relacje, brute force."""

import uuid
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from grupy.models import Czlonkostwo, StatusCzlonkostwa
from konta.models import Rola
from konta.tests.pomocnicze import HASLO, TestBezpieczenstwa, obraz
from moderacja.models import AkcjaModeratora, Powod, StatusZgloszenia, TypZgloszenia, Zgloszenie
from posty.models import Post, Widocznosc
from relacje.models import StatusZnajomosci, Znajomosc


class CsrfTest(TestBezpieczenstwa):
    def test_post_bez_tokena_csrf_odrzucony(self):
        przegladarka = Client(enforce_csrf_checks=True)
        przegladarka.force_login(self.a, backend="konta.backends.TylkoNiezablokowaniBackend")
        odp = przegladarka.post(reverse("posty:nowy"), {"tresc": "cross-site", "widocznosc": "publiczny"})
        self.assertEqual(odp.status_code, 403)
        self.assertNotContains(odp, "CSRF verification", status_code=403)  # bez technicznych szczegółów
        self.assertFalse(Post.objects.filter(tresc="cross-site").exists())


class NaglowkiTest(TestBezpieczenstwa):
    def test_naglowki_bezpieczenstwa(self):
        self.zaloguj(self.a)
        odp = self.client.get(reverse("posty:tablica"))
        self.assertIn("default-src 'self'", odp["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", odp["Content-Security-Policy"])
        self.assertEqual(odp["X-Frame-Options"], "DENY")
        self.assertEqual(odp["X-Content-Type-Options"], "nosniff")
        self.assertIn("camera=()", odp["Permissions-Policy"])
        self.assertEqual(odp["Cross-Origin-Opener-Policy"], "same-origin")

    def test_skrypt_inline_ma_nonce_zgodny_z_csp(self):
        self.zaloguj(self.a)
        odp = self.client.get(reverse("posty:tablica"))
        nonce = odp["Content-Security-Policy"].split("'nonce-")[1].split("'")[0]
        self.assertContains(odp, f'nonce="{nonce}"')

    def test_xss_w_tresci_jest_escapowany(self):
        self.post(self.a, "<script>alert(1)</script>")
        self.zaloguj(self.a)
        odp = self.client.get(reverse("posty:tablica"))
        self.assertNotContains(odp, "<script>alert(1)</script>")
        self.assertContains(odp, "&lt;script&gt;")


class PlikiTest(TestBezpieczenstwa):
    def wyslij(self, plik):
        self.zaloguj(self.a)
        return self.client.post(reverse("posty:nowy"), {"tresc": "z plikiem", "widocznosc": "publiczny",
                                                       "obraz": plik})

    def test_falszywy_obraz_odrzucony(self):
        self.wyslij(SimpleUploadedFile("x.png", b"<?php system($_GET['c']); ?>", content_type="image/png"))
        self.assertFalse(Post.objects.filter(tresc="z plikiem").exists())

    def test_gif_odrzucony(self):
        self.wyslij(obraz("a.gif", "GIF"))
        self.assertFalse(Post.objects.filter(tresc="z plikiem").exists())

    @override_settings(MAKS_ROZMIAR_OBRAZU=100)
    def test_za_duzy_plik_odrzucony(self):
        self.wyslij(obraz(rozmiar=(400, 400)))
        self.assertFalse(Post.objects.filter(tresc="z plikiem").exists())

    def test_jpg_przekodowany_do_webp_z_losowa_nazwa(self):
        self.wyslij(obraz("../../wakacje GPS.jpg", "JPEG"))
        p = Post.objects.get(tresc="z plikiem")
        self.assertTrue(p.obraz.name.startswith("posty/") and p.obraz.name.endswith(".webp"))
        self.assertNotIn("wakacje", p.obraz.name)

    def test_avatar_osoby_zablokowanej_niedostepny(self):
        from relacje.models import Blokada
        self.zaloguj(self.b)
        self.client.post(reverse("konta:profil_edycja"), {"avatar": obraz(), "opis": "", "miasto": ""})
        self.b.refresh_from_db()
        self.assertTrue(self.b.avatar)
        Blokada.objects.create(kto=self.b, kogo=self.c)
        self.zaloguj(self.c)
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:avatar", args=[self.b.pk])))


class ModeracjaTest(TestBezpieczenstwa):
    def zglos(self, post, kto):
        self.zaloguj(kto)
        return self.client.post(reverse("moderacja:zglos", args=["post", post.pk]),
                                {"powod": Powod.SPAM, "opis": "spam"})

    def test_nie_mozna_zglosic_niewidocznego_posta(self):
        p = self.post(self.b, "SEKRET", Widocznosc.TYLKO_JA)
        self.assertOdmowaBezDanych(self.zglos(p, self.c), "SEKRET")
        self.assertFalse(Zgloszenie.objects.exists())

    def test_moderator_widzi_tylko_zgloszona_tresc(self):
        p = self.post(self.a, "ZGLOSZONY-znajomi", Widocznosc.ZNAJOMI)
        inny = self.post(self.a, "NIEZGLOSZONY-znajomi", Widocznosc.ZNAJOMI)
        self.zglos(p, self.b)
        zgl = Zgloszenie.objects.get()
        self.zaloguj(self.mod)
        self.assertContains(self.client.get(reverse("moderacja:zgloszenie", args=[zgl.pk])), "ZGLOSZONY-znajomi")
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:szczegoly", args=[p.pk])), "ZGLOSZONY")
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:szczegoly", args=[inny.pk])), "NIEZGLOSZONY")

    def test_decyzja_ukrycia_zapisuje_historie(self):
        p = self.post(self.c, "spamik")
        self.zglos(p, self.a)
        zgl = Zgloszenie.objects.get()
        self.zaloguj(self.mod)
        self.client.post(reverse("moderacja:zgloszenie", args=[zgl.pk]), {"akcja": "ukryj"})
        p.refresh_from_db()
        zgl.refresh_from_db()
        self.assertTrue(p.ukryty)
        self.assertEqual(zgl.status, StatusZgloszenia.ROZPATRZONE)
        self.assertTrue(AkcjaModeratora.objects.filter(wykonal=self.mod, zgloszenie=zgl).exists())
        self.zaloguj(self.a)  # ukryty post znika dla innych
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:szczegoly", args=[p.pk])), "spamik")

    def test_blokada_autora_na_dni(self):
        p = self.post(self.c, "spam")
        self.zglos(p, self.a)
        zgl = Zgloszenie.objects.get()
        self.zaloguj(self.mod)
        self.client.post(reverse("moderacja:zgloszenie", args=[zgl.pk]), {"akcja": "zablokuj", "dni": 2})
        self.c.refresh_from_db()
        self.assertTrue(self.c.jest_zablokowany)
        self.assertLess(self.c.zablokowany_do, timezone.now() + timedelta(days=2, minutes=1))

    def test_moderator_nie_zablokuje_administratora(self):
        p = self.post(self.adm, "post admina")
        self.zglos(p, self.a)
        zgl = Zgloszenie.objects.get()
        self.zaloguj(self.mod)
        odp = self.client.post(reverse("moderacja:zgloszenie", args=[zgl.pk]), {"akcja": "zablokuj", "dni": 5})
        self.assertOdmowaBezDanych(odp)
        self.adm.refresh_from_db()
        self.assertFalse(self.adm.jest_zablokowany)

    def test_zablokowany_nie_opublikuje(self):
        self.c.zablokowany_do = timezone.now() + timedelta(days=1)
        self.c.save()
        self.client.force_login(self.c)  # nawet z „przemyconą” sesją
        self.client.post(reverse("posty:nowy"), {"tresc": "mimo blokady", "widocznosc": "publiczny"})
        self.assertFalse(Post.objects.filter(tresc="mimo blokady").exists())


class GrupyRelacjeTest(TestBezpieczenstwa):
    def test_tylko_zalozyciel_akceptuje_prosby(self):
        g = self.grupa(self.b, prywatna=True)
        prosba = Czlonkostwo.objects.create(grupa=g, uzytkownik=self.c, status=StatusCzlonkostwa.OCZEKUJE)
        self.zaloguj(self.c)  # próba samoakceptacji
        odp = self.client.post(reverse("grupy:akceptuj", args=[g.pk, prosba.pk]))
        self.assertOdmowaBezDanych(odp)
        prosba.refresh_from_db()
        self.assertEqual(prosba.status, StatusCzlonkostwa.OCZEKUJE)
        self.zaloguj(self.b)
        self.client.post(reverse("grupy:akceptuj", args=[g.pk, prosba.pk]))
        prosba.refresh_from_db()
        self.assertEqual(prosba.status, StatusCzlonkostwa.CZLONEK)

    def test_dolaczenie_do_publicznej_bez_akceptacji_do_prywatnej_prosba(self):
        pub, pryw = self.grupa(self.b, prywatna=False), self.grupa(self.b, prywatna=True)
        self.zaloguj(self.c)
        self.client.post(reverse("grupy:dolacz", args=[pub.pk]))
        self.client.post(reverse("grupy:dolacz", args=[pryw.pk]))
        self.assertEqual(Czlonkostwo.objects.get(grupa=pub, uzytkownik=self.c).status, StatusCzlonkostwa.CZLONEK)
        self.assertEqual(Czlonkostwo.objects.get(grupa=pryw, uzytkownik=self.c).status, StatusCzlonkostwa.OCZEKUJE)

    def test_tylko_adresat_przyjmuje_zaproszenie(self):
        z = Znajomosc.objects.create(od=self.c, do=self.b)
        self.zaloguj(self.c)
        self.assertOdmowaBezDanych(self.client.post(reverse("relacje:akceptuj", args=[z.pk])))
        z.refresh_from_db()
        self.assertEqual(z.status, StatusZnajomosci.OCZEKUJE)

    def test_wyszukiwarka_nie_pokazuje_emaili_ani_zablokowanych(self):
        from relacje.models import Blokada
        Blokada.objects.create(kto=self.c, kogo=self.a)
        self.zaloguj(self.a)
        odp = self.client.get(reverse("konta:szukaj"), {"q": "e"})
        self.assertNotContains(odp, "@example.com")
        self.assertNotContains(odp, "celina")


class BruteForceTest(TestBezpieczenstwa):
    def test_axes_blokuje_po_5_probach(self):
        for _ in range(5):
            self.client.post(reverse("konta:logowanie"), {"username": "ala", "password": "zle-haslo"})
        odp = self.client.post(reverse("konta:logowanie"), {"username": "ala", "password": HASLO})
        self.assertEqual(odp.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_komunikat_logowania_nie_zdradza_istnienia_konta(self):
        o1 = self.client.post(reverse("konta:logowanie"), {"username": "ala", "password": "zle"})
        o2 = self.client.post(reverse("konta:logowanie"), {"username": "nikt-taki", "password": "zle"})
        self.assertContains(o1, "Niepoprawny login lub hasło")
        self.assertContains(o2, "Niepoprawny login lub hasło")


class MotywTest(TestBezpieczenstwa):
    def test_przelacznik_motywu_na_belce_dla_zalogowanych_i_goscia(self):
        for zalogowany in (False, True):
            if zalogowany:
                self.zaloguj(self.a)
            odp = self.client.get(reverse("posty:tablica" if zalogowany else "konta:logowanie"))
            with self.subTest(zalogowany=zalogowany):
                self.assertContains(odp, "przelacznik-motywu")
                self.assertContains(odp, "js/motyw.js")

    def test_skrypt_motywu_w_head_ma_nonce(self):
        """Wczesny skrypt motywu jest inline – musi mieć nonce, inaczej CSP go zablokuje."""
        odp = self.client.get(reverse("konta:logowanie"))
        nonce = odp["Content-Security-Policy"].split("'nonce-")[1].split("'")[0]
        head = odp.content.decode().split("</head>")[0]
        self.assertIn(f'<script nonce="{nonce}">', head)


class TablicaTest(TestBezpieczenstwa):
    def test_tablica_od_najnowszych(self):
        from datetime import timedelta
        stary = self.post(self.a, "STARY-POST")
        Post.objects.filter(pk=stary.pk).update(utworzono=timezone.now() - timedelta(days=1))
        self.post(self.a, "NOWY-POST")
        self.zaloguj(self.a)
        tresc = self.client.get(reverse("posty:tablica")).content.decode()
        self.assertLess(tresc.index("NOWY-POST"), tresc.index("STARY-POST"))


class StronyRenderujaSieTest(TestBezpieczenstwa):
    """Dymny test: każda strona działa dla każdej roli (brak błędów szablonów)."""

    def test_strony(self):
        g = self.grupa(self.a, prywatna=False)
        p = self.post(self.a, "test", grupa=None)
        from wiadomosci.models import Rozmowa
        r = Rozmowa.dla_pary(self.a, self.b)
        zgl = Zgloszenie.objects.create(typ=TypZgloszenia.POST, post=p, uzytkownik=self.a,
                                        zglaszajacy=self.b, powod=Powod.INNE, kopia_tresci="test")
        wspolne = [reverse("posty:tablica"), reverse("relacje:znajomi"), reverse("grupy:lista"),
                   reverse("grupy:nowa"), reverse("grupy:szczegoly", args=[g.pk]), reverse("wiadomosci:lista"),
                   reverse("konta:profil_edycja"), reverse("konta:profil", args=["ala"]),
                   reverse("konta:szukaj") + "?q=al", reverse("posty:nowy"),
                   reverse("posty:szczegoly", args=[p.pk]),
                   reverse("moderacja:zglos", args=["post", p.pk])]
        self.zaloguj(self.a)
        for adres in wspolne + [reverse("posty:edycja", args=[p.pk]), reverse("posty:usun", args=[p.pk]),
                                reverse("wiadomosci:rozmowa", args=[r.pk]), reverse("grupy:usun", args=[g.pk])]:
            with self.subTest(adres):
                self.assertEqual(self.client.get(adres).status_code, 200)
        self.zaloguj(self.adm)
        for adres in [reverse("moderacja:panel"), reverse("moderacja:historia"),
                      reverse("moderacja:zgloszenie", args=[zgl.pk]), reverse("konta:panel_uzytkownicy"),
                      reverse("konta:panel_konto", args=[self.a.pk])]:
            with self.subTest(adres):
                self.assertEqual(self.client.get(adres).status_code, 200)
        self.client.logout()
        for adres in [reverse("konta:logowanie"), reverse("konta:rejestracja")]:
            self.assertEqual(self.client.get(adres).status_code, 200)

    @override_settings(DEBUG=False)
    def test_wlasna_strona_404_bez_szczegolow(self):
        self.zaloguj(self.a)
        odp = self.client.get("/nie/ma/takiej/strony/")
        self.assertEqual(odp.status_code, 404)
        self.assertContains(odp, "Nie ma takiej strony", status_code=404)
        self.assertNotContains(odp, "urlpatterns", status_code=404)
