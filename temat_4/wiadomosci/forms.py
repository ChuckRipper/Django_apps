from django import forms

from .models import Wiadomosc


class WiadomoscForm(forms.ModelForm):
    class Meta:
        model = Wiadomosc
        fields = ("tresc",)  # nadawca i rozmowa – z widoku
        widgets = {"tresc": forms.Textarea(attrs={"rows": 2, "placeholder": "Napisz wiadomość…"})}
        labels = {"tresc": ""}
