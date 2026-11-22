from django.urls import path

from . import views, views_pliki

app_name = "posty"

urlpatterns = [
    path("", views.TablicaView.as_view(), name="tablica"),
    path("posty/nowy/", views.NowyPostView.as_view(), name="nowy"),
    path("posty/<uuid:pk>/", views.SzczegolyPostuView.as_view(), name="szczegoly"),
    path("posty/<uuid:pk>/edycja/", views.EdycjaPostuView.as_view(), name="edycja"),
    path("posty/<uuid:pk>/usun/", views.UsunPostView.as_view(), name="usun"),
    path("posty/<uuid:pk>/komentarz/", views.DodajKomentarzView.as_view(), name="komentarz"),
    path("posty/<uuid:pk>/polub/", views.PolubView.as_view(), name="polub"),
    path("komentarze/<uuid:pk>/usun/", views.UsunKomentarzView.as_view(), name="usun_komentarz"),
    path("pliki/posty/<uuid:pk>/", views_pliki.ZdjeciePostuView.as_view(), name="zdjecie"),
    path("pliki/avatary/<uuid:pk>/", views_pliki.AvatarView.as_view(), name="avatar"),
]
