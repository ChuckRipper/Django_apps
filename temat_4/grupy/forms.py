from django import forms

from .models import Grupa


class GrupaForm(forms.ModelForm):
    class Meta:
        model = Grupa
        fields = ("nazwa", "opis", "prywatna")  # założyciel z request.user
