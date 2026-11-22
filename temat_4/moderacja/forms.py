from django import forms

from .models import Zgloszenie


class ZgloszenieForm(forms.ModelForm):
    class Meta:
        model = Zgloszenie
        fields = ("powod", "opis")  # typ, obiekt, zgłaszający – z widoku


class DecyzjaForm(forms.Form):
    AKCJE = [
        ("odrzuc", "Odrzuć zgłoszenie"),
        ("ukryj", "Ukryj treść"),
        ("usun", "Usuń treść"),
        ("zablokuj", "Zablokuj autora"),
    ]
    akcja = forms.ChoiceField(choices=AKCJE, widget=forms.RadioSelect)
    dni = forms.IntegerField(label="Dni blokady", min_value=1, max_value=30, initial=3, required=False)
    uzasadnienie = forms.CharField(max_length=500, required=False, widget=forms.Textarea(attrs={"rows": 2}))
