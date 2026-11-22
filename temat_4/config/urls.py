"""
Główne adresy. Panel admina Django pod niestandardowym adresem (DJANGO_ADMIN_URL).
Brak `static(MEDIA_URL, ...)` – pliki użytkowników idą wyłącznie przez widoki.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("konta.urls")),
    path("", include("posty.urls")),
    path("", include("moderacja.urls")),
    path("znajomi/", include("relacje.urls")),
    path("grupy/", include("grupy.urls")),
    path("wiadomosci/", include("wiadomosci.urls")),
]

handler400 = "konta.views.blad_400"
handler403 = "konta.views.blad_403"
handler404 = "konta.views.blad_404"
handler500 = "konta.views.blad_500"
