"""
Formularze kont. Zawsze JAWNA lista pól (nigdy "__all__") – pola wrażliwe
(rola, is_staff, is_superuser, zablokowany_do) nie istnieją w formularzach
użytkownika, więc dopisanie ich do żądania nic nie da (mass assignment).
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone

from .models import Rola, Uzytkownik
from .obrazy import przetworz_obraz


class RejestracjaForm(UserCreationForm):
    email = forms.EmailField(label="Adres e-mail")

    class Meta:
        model = Uzytkownik
        fields = ("username", "email")  # hasła dokłada UserCreationForm

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Uzytkownik.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ten adres e-mail jest już używany.")
        return email

    def clean_username(self):
        login = self.cleaned_data["username"]
        if Uzytkownik.objects.filter(username__iexact=login).exists():
            raise forms.ValidationError("Ten login jest już zajęty.")
        return login

    def save(self, commit=True):
        uzytkownik = super().save(commit=False)
        # Twarde wartości po stronie serwera – niezależnie od tego, co przyszło w POST.
        uzytkownik.rola = Rola.UZYTKOWNIK
        uzytkownik.is_staff = False
        uzytkownik.is_superuser = False
        uzytkownik.zablokowany_do = None
        if commit:
            uzytkownik.save()
        return uzytkownik


class LogowanieForm(AuthenticationForm):
    error_messages = {
        # Jeden komunikat dla złego hasła, nieistniejącego i zablokowanego konta –
        # nie da się w ten sposób sprawdzać, czy konto istnieje (enumeracja).
        "invalid_login": "Niepoprawny login lub hasło albo konto jest zablokowane.",
        "inactive": "Niepoprawny login lub hasło albo konto jest zablokowane.",
    }


class ProfilForm(forms.ModelForm):
    class Meta:
        model = Uzytkownik
        fields = ("avatar", "opis", "miasto", "data_urodzenia")
        widgets = {"data_urodzenia": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def clean_avatar(self):
        plik = self.cleaned_data.get("avatar")
        if plik and hasattr(plik, "content_type"):  # nowo przesłany plik
            return przetworz_obraz(plik, maks_bok=512)
        return plik

    def clean_data_urodzenia(self):
        data = self.cleaned_data.get("data_urodzenia")
        if data and data > timezone.localdate():
            raise forms.ValidationError("Data urodzenia nie może być z przyszłości.")
        return data


class ZarzadzanieKontemForm(forms.ModelForm):
    """Panel administratora: rola i blokada. Bez e-maila, hasła, flag Django."""

    class Meta:
        model = Uzytkownik
        fields = ("rola", "zablokowany_do")
        widgets = {"zablokowany_do": forms.DateTimeInput(attrs={"type": "datetime-local"},
                                                          format="%Y-%m-%dT%H:%M")}
        help_texts = {"zablokowany_do": "Puste = brak blokady."}


class BlokadaKontaForm(forms.Form):
    """Moderator: blokada czasowa (1–30 dni)."""

    dni = forms.IntegerField(label="Liczba dni blokady", min_value=1, max_value=30, initial=3)
