"""Formularze treści – jawne pola; autor/grupa ustawiane w widoku z request.user."""

from django import forms

from konta.obrazy import przetworz_obraz

from .models import Komentarz, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("tresc", "obraz", "widocznosc")
        widgets = {"tresc": forms.Textarea(attrs={"rows": 4, "placeholder": "Co słychać?"})}

    def __init__(self, *args, w_grupie=False, **kwargs):
        super().__init__(*args, **kwargs)
        if w_grupie:
            # W grupie o widoczności decyduje typ grupy.
            del self.fields["widocznosc"]

    def clean_obraz(self):
        plik = self.cleaned_data.get("obraz")
        if plik and hasattr(plik, "content_type"):
            return przetworz_obraz(plik)
        return plik


class KomentarzForm(forms.ModelForm):
    class Meta:
        model = Komentarz
        fields = ("tresc",)
        widgets = {"tresc": forms.Textarea(attrs={"rows": 2, "placeholder": "Napisz komentarz…"})}
        labels = {"tresc": ""}
