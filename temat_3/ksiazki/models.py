from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone


class Ksiazka(models.Model):
    tytul = models.CharField('Tytuł', max_length=200)
    autor = models.CharField('Autor', max_length=200)
    isbn = models.CharField('ISBN', max_length=17, unique=True, blank=True, null=True)
    rok_wydania = models.PositiveIntegerField('Rok wydania', blank=True, null=True)
    gatunek = models.CharField('Gatunek', max_length=100, blank=True)
    liczba_egzemplarzy = models.PositiveIntegerField('Liczba egzemplarzy', default=1)
    dodano = models.DateTimeField('Dodano', auto_now_add=True)

    class Meta:
        verbose_name = 'Książka'
        verbose_name_plural = 'Książki'
        ordering = ['tytul']

    def __str__(self):
        return f'{self.tytul} – {self.autor}'

    def aktywne_wypozyczenia(self):
        return self.wypozyczenie_set.filter(data_zwrotu__isnull=True).count()

    def dostepne(self):
        """Liczba egzemplarzy, które można teraz wypożyczyć."""
        return max(self.liczba_egzemplarzy - self.aktywne_wypozyczenia(), 0)


class Czytelnik(models.Model):
    imie = models.CharField('Imię', max_length=100)
    nazwisko = models.CharField('Nazwisko', max_length=100)
    email = models.EmailField('E-mail', unique=True)
    numer_karty = models.CharField('Numer karty', max_length=20, unique=True)

    class Meta:
        verbose_name = 'Czytelnik'
        verbose_name_plural = 'Czytelnicy'
        ordering = ['nazwisko', 'imie']

    def __str__(self):
        return f'{self.imie} {self.nazwisko} ({self.numer_karty})'

    def get_absolute_url(self):
        return reverse('czytelnik_szczegoly', args=[self.pk])


def domyslny_termin_zwrotu():
    return timezone.now().date() + timedelta(days=30)


class Wypozyczenie(models.Model):
    ksiazka = models.ForeignKey(Ksiazka, on_delete=models.PROTECT, verbose_name='Książka')
    czytelnik = models.ForeignKey(Czytelnik, on_delete=models.PROTECT, verbose_name='Czytelnik')
    data_wypozyczenia = models.DateField('Data wypożyczenia', default=timezone.localdate)
    termin_zwrotu = models.DateField('Termin zwrotu', default=domyslny_termin_zwrotu)
    data_zwrotu = models.DateField('Data zwrotu', blank=True, null=True)

    class Meta:
        verbose_name = 'Wypożyczenie'
        verbose_name_plural = 'Wypożyczenia'
        ordering = ['termin_zwrotu']

    def __str__(self):
        return f'{self.ksiazka.tytul} → {self.czytelnik}'

    @property
    def po_terminie(self):
        return self.data_zwrotu is None and self.termin_zwrotu < timezone.localdate()
