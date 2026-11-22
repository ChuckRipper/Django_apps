from django.urls import path

from . import views

app_name = "grupy"

urlpatterns = [
    path("", views.ListaGrupView.as_view(), name="lista"),
    path("nowa/", views.NowaGrupaView.as_view(), name="nowa"),
    path("<uuid:pk>/", views.SzczegolyGrupyView.as_view(), name="szczegoly"),
    path("<uuid:pk>/dolacz/", views.DolaczView.as_view(), name="dolacz"),
    path("<uuid:pk>/opusc/", views.OpuscView.as_view(), name="opusc"),
    path("<uuid:pk>/usun/", views.UsunGrupeView.as_view(), name="usun"),
    path("<uuid:pk>/czlonkowie/<uuid:czl_pk>/akceptuj/",
         views.ZarzadzajCzlonkiemView.as_view(akcja="akceptuj"), name="akceptuj"),
    path("<uuid:pk>/czlonkowie/<uuid:czl_pk>/usun/",
         views.ZarzadzajCzlonkiemView.as_view(akcja="usun"), name="usun_czlonka"),
]
