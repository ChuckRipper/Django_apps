from django.urls import path

from . import views

app_name = "konta"

urlpatterns = [
    path("konta/rejestracja/", views.RejestracjaView.as_view(), name="rejestracja"),
    path("konta/logowanie/", views.LogowanieView.as_view(), name="logowanie"),
    path("konta/wylogowanie/", views.WylogowanieView.as_view(), name="wylogowanie"),
    path("profil/", views.MojProfilView.as_view(), name="moj_profil"),
    path("profil/edycja/", views.EdycjaProfiluView.as_view(), name="profil_edycja"),
    path("u/<str:username>/", views.ProfilView.as_view(), name="profil"),
    path("szukaj/", views.SzukajView.as_view(), name="szukaj"),
    path("panel/uzytkownicy/", views.ListaUzytkownikowView.as_view(), name="panel_uzytkownicy"),
    path("panel/uzytkownicy/<uuid:pk>/", views.ZarzadzanieKontemView.as_view(), name="panel_konto"),
]
