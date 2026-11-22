from django.urls import path

from . import views

app_name = "relacje"

urlpatterns = [
    path("", views.ZnajomiView.as_view(), name="znajomi"),
    path("zapros/<str:username>/", views.ZaprosView.as_view(), name="zapros"),
    path("zaproszenia/<uuid:pk>/akceptuj/", views.OdpowiedzNaZaproszenieView.as_view(akceptuj=True), name="akceptuj"),
    path("zaproszenia/<uuid:pk>/odrzuc/", views.OdpowiedzNaZaproszenieView.as_view(akceptuj=False), name="odrzuc"),
    path("<uuid:pk>/usun/", views.UsunZnajomoscView.as_view(), name="usun"),
    path("zablokuj/<str:username>/", views.ZablokujView.as_view(), name="zablokuj"),
    path("blokady/<uuid:pk>/odblokuj/", views.OdblokujView.as_view(), name="odblokuj"),
]
