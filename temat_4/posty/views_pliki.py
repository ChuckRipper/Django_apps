"""
Serwowanie plików użytkowników PRZEZ WIDOK (scenariusz 3).

Pliki leżą w MEDIA_ROOT, ale aplikacja nie wystawia MEDIA_URL – nie istnieje
„bezpośredni adres pliku”. Zdjęcie posta dostaje tylko ktoś, kto widzi post
(Post.objects.widoczne_dla), avatar – ktoś, kto może oglądać profil.
"""

from django.http import FileResponse

from konta.uprawnienia import WymaganaRolaMixin, odmow_dostepu, pobierz_lub_odmow
from relacje.uslugi import widoczni_dla
from django.views import View

from .models import Post


def _odpowiedz_pliku(plik):
    odpowiedz = FileResponse(plik.open("rb"), content_type="image/webp")
    odpowiedz["Content-Disposition"] = "inline"
    odpowiedz["X-Content-Type-Options"] = "nosniff"
    return odpowiedz


class ZdjeciePostuView(WymaganaRolaMixin, View):
    def get(self, request, pk):
        post = pobierz_lub_odmow(request, Post.objects.widoczne_dla(request.user).exclude(obraz=""), pk=pk)
        return _odpowiedz_pliku(post.obraz)


class AvatarView(WymaganaRolaMixin, View):
    def get(self, request, pk):
        osoba = pobierz_lub_odmow(request, widoczni_dla(request.user).exclude(avatar=""), pk=pk)
        return _odpowiedz_pliku(osoba.avatar)
