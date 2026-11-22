"""
Scenariusze sprawdzane przez prowadzącego (tabela z treści zadania) – po co najmniej
jednym teście na każdy z 14 scenariuszy. Każdy test odmowy: 403 + neutralny komunikat
+ brak chronionych danych (assertOdmowaBezDanych).
"""

import uuid

from django.test import Client
from django.urls import reverse

from grupy.models import Czlonkostwo, StatusCzlonkostwa
from konta.models import Rola, Uzytkownik
from konta.tests.pomocnicze import TestBezpieczenstwa, obraz
from posty.models import Komentarz, Polubienie, Post, Widocznosc
from relacje.models import Blokada
from wiadomosci.models import Rozmowa, Wiadomosc


class Scenariusz01TylkoJaTest(TestBezpieczenstwa):
    def test_cudzy_post_tylko_ja_to_403_bez_tresci(self):
        p = self.post(self.b, "SEKRET-tylko-ja-B", Widocznosc.TYLKO_JA)
        self.zaloguj(self.a)  # A jest nawet znajomym B
        odp = self.client.get(reverse("posty:szczegoly", args=[p.pk]))
        self.assertOdmowaBezDanych(odp, "SEKRET-tylko-ja-B", self.b.username)

    def test_autor_widzi_swoj_post_tylko_ja(self):
        p = self.post(self.b, "moja notatka", Widocznosc.TYLKO_JA)
        self.zaloguj(self.b)
        self.assertContains(self.client.get(reverse("posty:szczegoly", args=[p.pk])), "moja notatka")

    def test_post_tylko_ja_nie_pojawia_sie_na_tablicy_ani_profilu(self):
        self.post(self.b, "SEKRET-tablica", Widocznosc.TYLKO_JA)
        self.zaloguj(self.a)
        self.assertNotContains(self.client.get(reverse("posty:tablica")), "SEKRET-tablica")
        self.assertNotContains(self.client.get(reverse("konta:profil", args=[self.b.username])), "SEKRET-tablica")


class Scenariusz02ZnajomiTest(TestBezpieczenstwa):
    def test_post_znajomi_dla_nieznajomego_403(self):
        p = self.post(self.b, "SEKRET-znajomi-B", Widocznosc.ZNAJOMI)
        self.zaloguj(self.c)
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:szczegoly", args=[p.pk])), "SEKRET-znajomi-B")

    def test_post_znajomi_dla_znajomego_widoczny(self):
        p = self.post(self.b, "dla-znajomych", Widocznosc.ZNAJOMI)
        self.zaloguj(self.a)
        self.assertContains(self.client.get(reverse("posty:szczegoly", args=[p.pk])), "dla-znajomych")

    def test_oczekujace_zaproszenie_nie_daje_dostepu(self):
        from relacje.models import Znajomosc
        Znajomosc.objects.create(od=self.c, do=self.b)  # niezaakceptowane
        p = self.post(self.b, "SEKRET-oczekuje", Widocznosc.ZNAJOMI)
        self.zaloguj(self.c)
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:szczegoly", args=[p.pk])), "SEKRET-oczekuje")


class Scenariusz03ZdjecieTest(TestBezpieczenstwa):
    def setUp(self):
        super().setUp()
        self.zaloguj(self.b)
        self.client.post(reverse("posty:nowy"), {"tresc": "foto", "widocznosc": Widocznosc.TYLKO_JA,
                                                 "obraz": obraz()})
        self.p = Post.objects.get(autor=self.b, tresc="foto")

    def test_bezposredni_adres_zdjecia_prywatnego_posta_403_bez_pliku(self):
        self.zaloguj(self.a)
        odp = self.client.get(reverse("posty:zdjecie", args=[self.p.pk]))
        self.assertOdmowaBezDanych(odp)
        self.assertNotIn("image/", odp.get("Content-Type", ""))

    def test_plik_nie_ma_publicznego_adresu_media(self):
        self.zaloguj(self.a)
        odp = self.client.get("/media/" + self.p.obraz.name)
        self.assertEqual(odp.status_code, 404)

    def test_autor_dostaje_plik(self):
        odp = self.client.get(reverse("posty:zdjecie", args=[self.p.pk]))
        self.assertEqual(odp.status_code, 200)
        self.assertEqual(odp["Content-Type"], "image/webp")
        odp.close()


class Scenariusz04EdycjaUsuwanieTest(TestBezpieczenstwa):
    def setUp(self):
        super().setUp()
        self.p = self.post(self.b, "ORYGINAL-B", Widocznosc.PUBLICZNY)
        self.zaloguj(self.a)

    def test_get_edycji_cudzego_posta_403(self):
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:edycja", args=[self.p.pk])), "ORYGINAL-B")

    def test_post_edycji_cudzego_posta_403_i_bez_zmian(self):
        odp = self.client.post(reverse("posty:edycja", args=[self.p.pk]),
                               {"tresc": "PRZEJETY", "widocznosc": Widocznosc.PUBLICZNY})
        self.assertOdmowaBezDanych(odp, "ORYGINAL-B")
        self.p.refresh_from_db()
        self.assertEqual(self.p.tresc, "ORYGINAL-B")

    def test_post_usuniecia_cudzego_posta_403_i_post_istnieje(self):
        odp = self.client.post(reverse("posty:usun", args=[self.p.pk]))
        self.assertOdmowaBezDanych(odp, "ORYGINAL-B")
        self.assertTrue(Post.objects.filter(pk=self.p.pk).exists())


class Scenariusz05RozmowaTest(TestBezpieczenstwa):
    def test_cudza_rozmowa_403(self):
        r = Rozmowa.dla_pary(self.b, self.c)
        Wiadomosc.objects.create(rozmowa=r, nadawca=self.b, tresc="SEKRET-rozmowy")
        self.zaloguj(self.a)
        self.assertOdmowaBezDanych(self.client.get(reverse("wiadomosci:rozmowa", args=[r.pk])),
                                   "SEKRET-rozmowy", self.c.username)

    def test_nie_mozna_dopisac_wiadomosci_do_cudzej_rozmowy(self):
        r = Rozmowa.dla_pary(self.b, self.c)
        self.zaloguj(self.a)
        odp = self.client.post(reverse("wiadomosci:rozmowa", args=[r.pk]), {"tresc": "wtracam sie"})
        self.assertOdmowaBezDanych(odp)
        self.assertFalse(Wiadomosc.objects.filter(tresc="wtracam sie").exists())


class Scenariusz06GrupaPrywatnaTest(TestBezpieczenstwa):
    def setUp(self):
        super().setUp()
        self.g = self.grupa(self.b, prywatna=True)
        self.p = self.post(self.b, "SEKRET-grupy", grupa=self.g)

    def test_niezalogowany_do_grupy_czlonek_widzi_nieczlonek_403(self):
        self.zaloguj(self.c)
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:szczegoly", args=[self.p.pk])), "SEKRET-grupy")
        self.assertNotContains(self.client.get(reverse("grupy:szczegoly", args=[self.g.pk])), "SEKRET-grupy")

    def test_prosba_oczekujaca_nie_daje_dostepu(self):
        Czlonkostwo.objects.create(grupa=self.g, uzytkownik=self.c, status=StatusCzlonkostwa.OCZEKUJE)
        self.zaloguj(self.c)
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:szczegoly", args=[self.p.pk])), "SEKRET-grupy")

    def test_nieczlonek_nie_opublikuje_w_grupie(self):
        self.zaloguj(self.c)
        odp = self.client.post(reverse("grupy:szczegoly", args=[self.g.pk]), {"tresc": "wpis z zewnatrz"})
        self.assertOdmowaBezDanych(odp)
        self.assertFalse(Post.objects.filter(tresc="wpis z zewnatrz").exists())

    def test_czlonek_widzi(self):
        Czlonkostwo.objects.create(grupa=self.g, uzytkownik=self.c, status=StatusCzlonkostwa.CZLONEK)
        self.zaloguj(self.c)
        self.assertContains(self.client.get(reverse("posty:szczegoly", args=[self.p.pk])), "SEKRET-grupy")


class Scenariusz07RejestracjaTest(TestBezpieczenstwa):
    def test_wstrzykniete_rola_i_is_staff_ignorowane(self):
        odp = self.client.post(reverse("konta:rejestracja"), {
            "username": "intruz", "email": "intruz@example.com",
            "password1": "Mocne-Haslo-12345", "password2": "Mocne-Haslo-12345",
            "rola": Rola.ADMINISTRATOR, "is_staff": "on", "is_superuser": "on", "zablokowany_do": "",
        })
        self.assertEqual(odp.status_code, 302)
        u = Uzytkownik.objects.get(username="intruz")
        self.assertEqual(u.rola, Rola.UZYTKOWNIK)
        self.assertFalse(u.is_staff or u.is_superuser)


class Scenariusz08AutorTest(TestBezpieczenstwa):
    def test_wstrzykniety_autor_ignorowany(self):
        self.zaloguj(self.a)
        self.client.post(reverse("posty:nowy"), {"tresc": "moj post", "widocznosc": Widocznosc.PUBLICZNY,
                                                 "autor": str(self.b.pk), "grupa": "", "ukryty": "on"})
        p = Post.objects.get(tresc="moj post")
        self.assertEqual(p.autor, self.a)
        self.assertFalse(p.ukryty)

    def test_wstrzykniety_nadawca_wiadomosci_ignorowany(self):
        r = Rozmowa.dla_pary(self.a, self.b)
        self.zaloguj(self.a)
        self.client.post(reverse("wiadomosci:rozmowa", args=[r.pk]), {"tresc": "hej", "nadawca": str(self.b.pk)})
        self.assertEqual(Wiadomosc.objects.get(tresc="hej").nadawca, self.a)


class Scenariusz09PanelTest(TestBezpieczenstwa):
    def test_uzytkownik_nie_wejdzie_do_paneli(self):
        self.zaloguj(self.a)
        for adres in (reverse("moderacja:panel"), reverse("moderacja:historia"),
                      reverse("konta:panel_uzytkownicy"), reverse("konta:panel_konto", args=[self.b.pk])):
            with self.subTest(adres):
                self.assertOdmowaBezDanych(self.client.get(adres), self.b.email)

    def test_moderator_nie_wejdzie_do_panelu_admina(self):
        self.zaloguj(self.mod)
        self.assertOdmowaBezDanych(self.client.get(reverse("konta:panel_uzytkownicy")))

    def test_uzytkownik_nie_zmieni_roli_przez_post(self):
        self.zaloguj(self.a)
        odp = self.client.post(reverse("konta:panel_konto", args=[self.a.pk]), {"rola": Rola.ADMINISTRATOR})
        self.assertOdmowaBezDanych(odp)
        self.a.refresh_from_db()
        self.assertEqual(self.a.rola, Rola.UZYTKOWNIK)

    def test_admin_nie_odbierze_sobie_roli(self):
        self.zaloguj(self.adm)
        odp = self.client.post(reverse("konta:panel_konto", args=[self.adm.pk]), {"rola": Rola.UZYTKOWNIK})
        self.assertOdmowaBezDanych(odp)
        self.adm.refresh_from_db()
        self.assertEqual(self.adm.rola, Rola.ADMINISTRATOR)

    def test_admin_zmienia_role_innego_i_zostaje_slad(self):
        self.zaloguj(self.adm)
        with self.assertLogs("bezpieczenstwo", "INFO") as logi:
            self.client.post(reverse("konta:panel_konto", args=[self.a.pk]),
                             {"rola": Rola.MODERATOR, "zablokowany_do": ""})
        self.a.refresh_from_db()
        self.assertEqual(self.a.rola, Rola.MODERATOR)
        self.assertTrue(any("ZMIANA ROLI" in w for w in logi.output))


class Scenariusz10ModeratorRozmowaTest(TestBezpieczenstwa):
    def test_moderator_i_admin_nie_czytaja_rozmow(self):
        r = Rozmowa.dla_pary(self.a, self.b)
        Wiadomosc.objects.create(rozmowa=r, nadawca=self.a, tresc="SEKRET-prywatny")
        for kto in (self.mod, self.adm):
            with self.subTest(kto.username):
                self.zaloguj(kto)
                self.assertOdmowaBezDanych(self.client.get(reverse("wiadomosci:rozmowa", args=[r.pk])),
                                           "SEKRET-prywatny")

    def test_moderator_nie_widzi_postow_znajomi_bez_zgloszenia(self):
        p = self.post(self.a, "SEKRET-znajomi-A", Widocznosc.ZNAJOMI)
        self.zaloguj(self.mod)
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:szczegoly", args=[p.pk])), "SEKRET-znajomi-A")


class Scenariusz11KomentarzPolubienieTest(TestBezpieczenstwa):
    def setUp(self):
        super().setUp()
        self.p = self.post(self.b, "SEKRET-B", Widocznosc.TYLKO_JA)
        self.zaloguj(self.a)

    def test_komentarz_do_niewidocznego_posta_403_nic_nie_zapisano(self):
        odp = self.client.post(reverse("posty:komentarz", args=[self.p.pk]), {"tresc": "wcisniety"})
        self.assertOdmowaBezDanych(odp, "SEKRET-B")
        self.assertFalse(Komentarz.objects.exists())

    def test_polubienie_niewidocznego_posta_403_nic_nie_zapisano(self):
        odp = self.client.post(reverse("posty:polub", args=[self.p.pk]))
        self.assertOdmowaBezDanych(odp, "SEKRET-B")
        self.assertFalse(Polubienie.objects.exists())

    def test_jedno_polubienie_na_osobe(self):
        p = self.post(self.b, "publiczny")
        self.client.post(reverse("posty:polub", args=[p.pk]))
        self.assertEqual(Polubienie.objects.filter(post=p).count(), 1)
        self.client.post(reverse("posty:polub", args=[p.pk]))  # ponowne = cofnięcie
        self.assertEqual(Polubienie.objects.filter(post=p).count(), 0)


class Scenariusz12BlokadaTest(TestBezpieczenstwa):
    def test_zablokowany_nie_widzi_profilu_ani_postow(self):
        Blokada.objects.create(kto=self.b, kogo=self.c)
        p = self.post(self.b, "SEKRET-publiczny-B", Widocznosc.PUBLICZNY)
        self.zaloguj(self.c)
        self.assertOdmowaBezDanych(self.client.get(reverse("konta:profil", args=[self.b.username])),
                                   self.b.opis or "SEKRET-publiczny-B")
        self.assertOdmowaBezDanych(self.client.get(reverse("posty:szczegoly", args=[p.pk])), "SEKRET-publiczny-B")

    def test_zablokowany_nie_napisze_wiadomosci(self):
        r = Rozmowa.dla_pary(self.b, self.c)
        Blokada.objects.create(kto=self.b, kogo=self.c)
        self.zaloguj(self.c)
        self.assertOdmowaBezDanych(self.client.post(reverse("wiadomosci:nowa", args=[self.b.username])))
        self.assertOdmowaBezDanych(self.client.post(reverse("wiadomosci:rozmowa", args=[r.pk]), {"tresc": "x"}))
        self.assertFalse(Wiadomosc.objects.exists())

    def test_zablokowane_konto_nie_zaloguje_sie(self):
        from datetime import timedelta
        from django.utils import timezone
        self.c.zablokowany_do = timezone.now() + timedelta(days=1)
        self.c.save()
        odp = self.client.post(reverse("konta:logowanie"), {"username": "celina", "password": "Bardzo-Trudne-Haslo-2026"})
        self.assertEqual(odp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_blokada_konta_wylogowuje_otwarta_sesje(self):
        from datetime import timedelta
        from django.utils import timezone
        self.zaloguj(self.c)
        self.c.zablokowany_do = timezone.now() + timedelta(days=1)
        self.c.save()
        odp = self.client.get(reverse("posty:tablica"))
        self.assertEqual(odp.status_code, 302)  # sesja już nie działa -> logowanie


class Scenariusz13IdentycznaOdpowiedzTest(TestBezpieczenstwa):
    def test_losowy_uuid_i_cudzy_obiekt_daja_to_samo(self):
        cudzy = self.post(self.b, "SEKRET", Widocznosc.TYLKO_JA)
        self.zaloguj(self.a)
        for nazwa in ("posty:szczegoly", "posty:edycja", "posty:usun", "posty:zdjecie"):
            with self.subTest(nazwa):
                o1 = self.client.get(reverse(nazwa, args=[cudzy.pk]))
                o2 = self.client.get(reverse(nazwa, args=[uuid.uuid4()]))
                self.assertEqual(self.porownywalna(o1), self.porownywalna(o2))

    def test_rozmowy_i_grupy_tez(self):
        r = Rozmowa.dla_pary(self.b, self.c)
        self.zaloguj(self.a)
        o1 = self.client.get(reverse("wiadomosci:rozmowa", args=[r.pk]))
        o2 = self.client.get(reverse("wiadomosci:rozmowa", args=[uuid.uuid4()]))
        self.assertEqual(self.porownywalna(o1), self.porownywalna(o2))

    def test_nieistniejacy_profil_i_zablokowany_profil_identyczne(self):
        Blokada.objects.create(kto=self.b, kogo=self.a)
        self.zaloguj(self.a)
        o1 = self.client.get(reverse("konta:profil", args=[self.b.username]))
        o2 = self.client.get(reverse("konta:profil", args=["nie-ma-takiego"]))
        self.assertEqual(self.porownywalna(o1), self.porownywalna(o2))


class Scenariusz14CacheTest(TestBezpieczenstwa):
    def test_strony_zalogowanego_no_store(self):
        self.zaloguj(self.a)
        odp = self.client.get(reverse("posty:tablica"))
        self.assertIn("no-store", odp["Cache-Control"])
        self.assertIn("private", odp["Cache-Control"])

    def test_wylogowanie_czysci_dane_witryny(self):
        self.zaloguj(self.a)
        odp = self.client.post(reverse("konta:wylogowanie"))
        self.assertIn('"cache"', odp["Clear-Site-Data"])
        self.assertIn('"cookies"', odp["Clear-Site-Data"])
        # Po wylogowaniu prywatna strona przekierowuje do logowania.
        self.assertEqual(self.client.get(reverse("posty:tablica")).status_code, 302)

    def test_wylogowanie_tylko_post(self):
        self.zaloguj(self.a)
        self.assertEqual(self.client.get(reverse("konta:wylogowanie")).status_code, 405)
