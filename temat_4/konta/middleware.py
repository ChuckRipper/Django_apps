"""Middleware bezpieczeństwa."""


class BrakCacheDlaZalogowanychMiddleware:
    """
    Strony zalogowanego użytkownika nie trafiają do cache przeglądarki ani proxy.
    Scenariusz „wspólny komputer”: po wylogowaniu przycisk „Wstecz” nie pokaże
    prywatnych danych (uzupełnia Clear-Site-Data wysyłane przy wylogowaniu).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        odpowiedz = self.get_response(request)
        uzytkownik = getattr(request, "user", None)
        if uzytkownik is not None and uzytkownik.is_authenticated:
            odpowiedz["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
            odpowiedz["Pragma"] = "no-cache"
            odpowiedz["Expires"] = "0"
        return odpowiedz


class NaglowkiBezpieczenstwaMiddleware:
    """Nagłówki, których Django nie ustawia samo."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        odpowiedz = self.get_response(request)
        odpowiedz.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        # Zasoby portalu (np. prywatne zdjęcia) nie mogą być osadzane przez inne domeny.
        odpowiedz.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return odpowiedz
