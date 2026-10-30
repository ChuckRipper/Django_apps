from django import forms

from .models import Czytelnik, Ksiazka, Wypozyczenie


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css


class KsiazkaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Ksiazka
        fields = ['tytul', 'autor', 'isbn', 'rok_wydania', 'gatunek', 'liczba_egzemplarzy']

    def clean_isbn(self):
        # Puste ISBN zapisujemy jako NULL, żeby nie łamać unikalności
        return self.cleaned_data['isbn'] or None


class CzytelnikForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Czytelnik
        fields = ['imie', 'nazwisko', 'email', 'numer_karty']


class WypozyczenieForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Wypozyczenie
        fields = ['ksiazka', 'czytelnik', 'termin_zwrotu']
        widgets = {'termin_zwrotu': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def clean(self):
        cleaned = super().clean()
        ksiazka = cleaned.get('ksiazka')
        if ksiazka and ksiazka.dostepne() == 0:
            raise forms.ValidationError(
                f'Brak wolnych egzemplarzy książki „{ksiazka.tytul}”. '
                'Wszystkie są wypożyczone.'
            )
        return cleaned
