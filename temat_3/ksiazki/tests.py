from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import WypozyczenieForm
from .models import Czytelnik, Ksiazka, Wypozyczenie


class BibliotekaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('bibliotekarz', password='haslo123')
        self.czytelnik = Czytelnik.objects.create(
            imie='Anna', nazwisko='Nowak', email='anna@example.com', numer_karty='K001')

    def zaloguj(self):
        self.client.login(username='bibliotekarz', password='haslo123')

    def test_lista_dostepna_dla_wszystkich(self):
        Ksiazka.objects.create(tytul='Lalka', autor='Bolesław Prus')
        r = self.client.get(reverse('lista'))
        self.assertContains(r, 'Lalka')

    def test_dodawanie_wymaga_logowania(self):
        r = self.client.get(reverse('dodaj'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('login'), r.url)

    def test_dodanie_ksiazki(self):
        self.zaloguj()
        r = self.client.post(reverse('dodaj'), {
            'tytul': 'Solaris', 'autor': 'Stanisław Lem', 'isbn': '',
            'rok_wydania': 1961, 'gatunek': 'SF', 'liczba_egzemplarzy': 2,
        })
        self.assertRedirects(r, reverse('lista'))
        k = Ksiazka.objects.get(tytul='Solaris')
        self.assertIsNone(k.isbn)  # pusty ISBN zapisany jako NULL

    def test_dwie_ksiazki_bez_isbn(self):
        self.zaloguj()
        for tytul in ('A', 'B'):
            self.client.post(reverse('dodaj'), {'tytul': tytul, 'autor': 'X', 'isbn': '', 'liczba_egzemplarzy': 1})
        self.assertEqual(Ksiazka.objects.filter(isbn__isnull=True).count(), 2)

    def test_wyszukiwanie_bez_wielkosci_liter(self):
        Ksiazka.objects.create(tytul='Solaris', autor='Stanisław Lem')
        Ksiazka.objects.create(tytul='Lalka', autor='Bolesław Prus')
        r = self.client.get(reverse('lista'), {'q': 'lem'})
        self.assertContains(r, 'Solaris')
        self.assertNotContains(r, 'Lalka')

    def test_blokada_wypozyczenia_bez_wolnych_egzemplarzy(self):
        k = Ksiazka.objects.create(tytul='Solaris', autor='Lem', liczba_egzemplarzy=1)
        Wypozyczenie.objects.create(ksiazka=k, czytelnik=self.czytelnik)
        self.assertEqual(k.dostepne(), 0)
        form = WypozyczenieForm(data={
            'ksiazka': k.pk, 'czytelnik': self.czytelnik.pk,
            'termin_zwrotu': (timezone.localdate() + timedelta(days=30)).isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('Brak wolnych egzemplarzy', str(form.non_field_errors()))

    def test_wypozyczenie_i_zwrot(self):
        self.zaloguj()
        k = Ksiazka.objects.create(tytul='Solaris', autor='Lem', liczba_egzemplarzy=1)
        r = self.client.post(reverse('wypozycz'), {
            'ksiazka': k.pk, 'czytelnik': self.czytelnik.pk,
            'termin_zwrotu': (timezone.localdate() + timedelta(days=30)).isoformat(),
        })
        self.assertRedirects(r, reverse('wypozyczenia'))
        w = Wypozyczenie.objects.get()
        self.assertEqual(k.dostepne(), 0)
        self.assertEqual(self.client.get(reverse('zwroc', args=[w.pk])).status_code, 405)  # tylko POST
        self.client.post(reverse('zwroc', args=[w.pk]))
        w.refresh_from_db()
        self.assertIsNotNone(w.data_zwrotu)
        self.assertEqual(k.dostepne(), 1)

    def test_domyslny_termin_i_po_terminie(self):
        k = Ksiazka.objects.create(tytul='Solaris', autor='Lem')
        w = Wypozyczenie.objects.create(ksiazka=k, czytelnik=self.czytelnik)
        self.assertEqual(w.termin_zwrotu, timezone.localdate() + timedelta(days=30))
        self.assertFalse(w.po_terminie)
        w.termin_zwrotu = timezone.localdate() - timedelta(days=1)
        self.assertTrue(w.po_terminie)

    def test_edycja_nieistniejacej_404(self):
        self.zaloguj()
        self.assertEqual(self.client.get(reverse('edytuj', args=[9999])).status_code, 404)
