from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CzytelnikForm, KsiazkaForm, WypozyczenieForm
from .models import Czytelnik, Ksiazka, Wypozyczenie

# Kolumny, po których można sortować listę książek (parametr ?sort=)
SORTOWANIE = {'tytul', '-tytul', 'autor', '-autor', 'rok_wydania', '-rok_wydania'}


# ---------- Książki ----------

def lista(request):
    ksiazki = Ksiazka.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        ksiazki = ksiazki.filter(Q(tytul__icontains=q) | Q(autor__icontains=q) | Q(isbn__icontains=q))

    sort = request.GET.get('sort', 'tytul')
    if sort not in SORTOWANIE:
        sort = 'tytul'
    ksiazki = ksiazki.order_by(sort, 'tytul')

    strona = Paginator(ksiazki, 10).get_page(request.GET.get('strona'))
    return render(request, 'ksiazki/lista.html', {
        'strona': strona, 'liczba': strona.paginator.count, 'q': q, 'sort': sort,
    })


@login_required
def dodaj(request):
    form = KsiazkaForm(request.POST or None)
    if form.is_valid():
        ksiazka = form.save()
        messages.success(request, f'Dodano książkę „{ksiazka.tytul}”.')
        return redirect('lista')
    return render(request, 'ksiazki/formularz.html', {'form': form, 'naglowek': 'Dodaj książkę'})


@login_required
def edytuj(request, pk):
    ksiazka = get_object_or_404(Ksiazka, pk=pk)
    form = KsiazkaForm(request.POST or None, instance=ksiazka)
    if form.is_valid():
        form.save()
        messages.success(request, f'Zapisano zmiany w „{ksiazka.tytul}”.')
        return redirect('lista')
    return render(request, 'ksiazki/formularz.html', {'form': form, 'naglowek': 'Edytuj książkę'})


@login_required
def usun(request, pk):
    ksiazka = get_object_or_404(Ksiazka, pk=pk)
    if request.method == 'POST':
        try:
            ksiazka.delete()
            messages.success(request, f'Usunięto książkę „{ksiazka.tytul}”.')
        except ProtectedError:
            messages.error(request, f'Nie można usunąć „{ksiazka.tytul}” – książka ma historię wypożyczeń.')
        return redirect('lista')
    return render(request, 'ksiazki/usun.html', {'obiekt': ksiazka, 'powrot': 'lista'})


# ---------- Czytelnicy ----------

@login_required
def czytelnicy(request):
    return render(request, 'ksiazki/czytelnicy.html', {'czytelnicy': Czytelnik.objects.all()})


@login_required
def czytelnik_szczegoly(request, pk):
    czytelnik = get_object_or_404(Czytelnik, pk=pk)
    historia = czytelnik.wypozyczenie_set.select_related('ksiazka').order_by('-data_wypozyczenia')
    return render(request, 'ksiazki/czytelnik.html', {'czytelnik': czytelnik, 'historia': historia})


@login_required
def czytelnik_dodaj(request):
    form = CzytelnikForm(request.POST or None)
    if form.is_valid():
        czytelnik = form.save()
        messages.success(request, f'Dodano czytelnika {czytelnik.imie} {czytelnik.nazwisko}.')
        return redirect('czytelnicy')
    return render(request, 'ksiazki/formularz.html', {'form': form, 'naglowek': 'Dodaj czytelnika', 'powrot': 'czytelnicy'})


@login_required
def czytelnik_edytuj(request, pk):
    czytelnik = get_object_or_404(Czytelnik, pk=pk)
    form = CzytelnikForm(request.POST or None, instance=czytelnik)
    if form.is_valid():
        form.save()
        messages.success(request, f'Zapisano zmiany: {czytelnik.imie} {czytelnik.nazwisko}.')
        return redirect('czytelnicy')
    return render(request, 'ksiazki/formularz.html', {'form': form, 'naglowek': 'Edytuj czytelnika', 'powrot': 'czytelnicy'})


@login_required
def czytelnik_usun(request, pk):
    czytelnik = get_object_or_404(Czytelnik, pk=pk)
    if request.method == 'POST':
        try:
            czytelnik.delete()
            messages.success(request, f'Usunięto czytelnika {czytelnik.imie} {czytelnik.nazwisko}.')
        except ProtectedError:
            messages.error(request, 'Nie można usunąć czytelnika, który ma historię wypożyczeń.')
        return redirect('czytelnicy')
    return render(request, 'ksiazki/usun.html', {'obiekt': czytelnik, 'powrot': 'czytelnicy'})


# ---------- Wypożyczenia ----------

@login_required
def wypozyczenia(request):
    aktywne = (Wypozyczenie.objects.filter(data_zwrotu__isnull=True)
               .select_related('ksiazka', 'czytelnik'))
    return render(request, 'ksiazki/wypozyczenia.html', {'wypozyczenia': aktywne})


@login_required
def wypozycz(request):
    # ?ksiazka=<id> z przycisku "Wypożycz" na liście wstępnie wybiera książkę
    poczatkowe = {'ksiazka': request.GET.get('ksiazka')}
    form = WypozyczenieForm(request.POST or None, initial=poczatkowe)
    if form.is_valid():
        w = form.save()
        messages.success(request, f'Wypożyczono „{w.ksiazka.tytul}” – zwrot do {w.termin_zwrotu:%d.%m.%Y}.')
        return redirect('wypozyczenia')
    return render(request, 'ksiazki/formularz.html', {'form': form, 'naglowek': 'Nowe wypożyczenie', 'powrot': 'wypozyczenia'})


@login_required
@require_POST
def zwroc(request, pk):
    w = get_object_or_404(Wypozyczenie, pk=pk, data_zwrotu__isnull=True)
    w.data_zwrotu = timezone.localdate()
    w.save()
    messages.success(request, f'Zwrócono „{w.ksiazka.tytul}”.')
    return redirect('wypozyczenia')
