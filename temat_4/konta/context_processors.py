from .models import Rola


def role(request):
    """Udostępnia szablonom stałe ról (do ukrywania linków – ochrona i tak jest w widokach)."""
    return {"Rola": Rola}
