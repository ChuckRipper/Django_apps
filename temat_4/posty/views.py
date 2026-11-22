"""
Posty, komentarze, polubienia.

Każdy widok pobiera obiekt ze zbioru zawężonego do użytkownika (widoczne_dla /
edytowalne_przez / usuwalne_przez). Brak w zbiorze = neutralne 403, także dla
POST – bo dispatch() -> get_object() działa przed obsługą metody (scenariusz 4).
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from konta.models import Rola
from konta.uprawnienia import (
    ObiektDlaUzytkownikaMixin,
    WymaganaRolaMixin,
    pobierz_lub_odmow,
)

from .forms import KomentarzForm, PostForm
from .models import Komentarz, Polubienie, Post


class TablicaView(WymaganaRolaMixin, View):
    """Posty znajomych, publiczne i własne (poza grupami), od najnowszych, stronicowane."""

    def get(self, request):
        posty = Post.objects.widoczne_dla(request.user).filter(grupa__isnull=True).z_licznikami(request.user)
        strona = Paginator(posty, 10).get_page(request.GET.get("strona"))
        return render(request, "posty/tablica.html", {"strona": strona, "form": PostForm()})


class NowyPostView(WymaganaRolaMixin, CreateView):
    """Autor = request.user (nie ma go w formularzu – wstrzyknięte `autor` jest ignorowane)."""

    minimalna_rola = Rola.UZYTKOWNIK  # ma_role() odrzuca zablokowane konta
    form_class = PostForm
    template_name = "posty/post_formularz.html"

    def form_valid(self, form):
        form.instance.autor = self.request.user
        form.instance.grupa = None
        messages.success(self.request, "Opublikowano.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("posty:szczegoly", args=[self.object.pk])


class SzczegolyPostuView(ObiektDlaUzytkownikaMixin, DetailView):
    template_name = "posty/post_szczegoly.html"
    context_object_name = "post"

    def get_queryset(self):
        return Post.objects.widoczne_dla(self.request.user).z_licznikami(self.request.user)

    def get_context_data(self, **kwargs):
        kontekst = super().get_context_data(**kwargs)
        kontekst["komentarze"] = Komentarz.objects.widoczne_dla(self.request.user) \
            .filter(post=self.object).select_related("autor")
        kontekst["form_komentarza"] = KomentarzForm()
        kontekst["moze_usunac"] = Post.objects.usuwalne_przez(self.request.user).filter(pk=self.object.pk).exists()
        return kontekst


class EdycjaPostuView(ObiektDlaUzytkownikaMixin, UpdateView):
    """Tylko autor. Zmiana widoczności możliwa; autor i grupa – nie."""

    minimalna_rola = Rola.UZYTKOWNIK
    template_name = "posty/post_formularz.html"
    context_object_name = "post"

    def get_queryset(self):
        return Post.objects.edytowalne_przez(self.request.user)

    def get_form(self, form_class=None):
        return PostForm(w_grupie=self.object.grupa_id is not None, **self.get_form_kwargs())

    def get_success_url(self):
        return reverse("posty:szczegoly", args=[self.object.pk])


class UsunPostView(ObiektDlaUzytkownikaMixin, DeleteView):
    """Autor albo założyciel grupy. GET = potwierdzenie, POST = usunięcie."""

    template_name = "posty/post_usun.html"
    context_object_name = "post"
    success_url = reverse_lazy("posty:tablica")

    def get_queryset(self):
        return Post.objects.usuwalne_przez(self.request.user)

    def form_valid(self, form):
        if self.object.obraz:
            self.object.obraz.delete(save=False)
        messages.info(self.request, "Post usunięty.")
        return super().form_valid(form)


@method_decorator(require_POST, name="dispatch")
class DodajKomentarzView(WymaganaRolaMixin, View):
    """Komentarz tylko pod postem, który widzę (scenariusz 11) – inaczej 403 i nic nie zapisujemy."""

    minimalna_rola = Rola.UZYTKOWNIK

    def post(self, request, pk):
        post = pobierz_lub_odmow(request, Post.objects.widoczne_dla(request.user), pk=pk)
        form = KomentarzForm(request.POST)
        if form.is_valid():
            form.instance.post = post
            form.instance.autor = request.user
            form.save()
        else:
            messages.error(request, "Komentarz nie może być pusty ani dłuższy niż 1000 znaków.")
        return redirect("posty:szczegoly", post.pk)


@method_decorator(require_POST, name="dispatch")
class UsunKomentarzView(WymaganaRolaMixin, View):
    def post(self, request, pk):
        komentarz = pobierz_lub_odmow(request, Komentarz.objects.usuwalne_przez(request.user), pk=pk)
        post_id = komentarz.post_id
        komentarz.delete()
        messages.info(request, "Komentarz usunięty.")
        return redirect("posty:szczegoly", post_id)


@method_decorator(require_POST, name="dispatch")
class PolubView(WymaganaRolaMixin, View):
    """Przełącznik polubienia; jedno na osobę (UniqueConstraint), tylko dla widocznych postów."""

    minimalna_rola = Rola.UZYTKOWNIK

    def post(self, request, pk):
        post = pobierz_lub_odmow(request, Post.objects.widoczne_dla(request.user), pk=pk)
        polubienie, utworzone = Polubienie.objects.get_or_create(post=post, uzytkownik=request.user)
        if not utworzone:
            polubienie.delete()
        nastepny = request.POST.get("nastepny", "")
        if nastepny == "tablica":
            return redirect(f"{reverse('posty:tablica')}#post-{post.pk}")
        return redirect("posty:szczegoly", post.pk)
