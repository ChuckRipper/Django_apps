# blog/forms.py - formularze bloga
from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'author', 'description', 'image']  # slug i daty ustawia Django

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label='Imię')
    email = forms.EmailField(label='E-mail')
    phone = forms.CharField(max_length=15, required=False, label='Telefon')
    subject = forms.CharField(max_length=100, label='Temat')
    message = forms.CharField(widget=forms.Textarea, label='Wiadomość')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
