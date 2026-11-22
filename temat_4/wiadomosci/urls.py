from django.urls import path

from . import views

app_name = "wiadomosci"

urlpatterns = [
    path("", views.ListaRozmowView.as_view(), name="lista"),
    path("<uuid:pk>/", views.RozmowaView.as_view(), name="rozmowa"),
    path("do/<str:username>/", views.NowaRozmowaView.as_view(), name="nowa"),
]
