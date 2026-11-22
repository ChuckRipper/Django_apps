from django.urls import path

from . import views

app_name = "moderacja"

urlpatterns = [
    path("zglos/<str:typ>/<str:ident>/", views.ZglosView.as_view(), name="zglos"),
    path("moderacja/", views.PanelModeratoraView.as_view(), name="panel"),
    path("moderacja/historia/", views.HistoriaView.as_view(), name="historia"),
    path("moderacja/<uuid:pk>/", views.ZgloszenieView.as_view(), name="zgloszenie"),
    path("moderacja/<uuid:pk>/zdjecie/", views.ZdjecieZgloszeniaView.as_view(), name="zdjecie"),
]
