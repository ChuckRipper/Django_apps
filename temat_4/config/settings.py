"""
Ustawienia portalu społecznościowego „Krąg” (Temat 4).

Zasady:
  * tryb deweloperski (DEBUG=True) działa od razu, bez konfiguracji (SQLite),
  * tryb produkcyjny (DJANGO_DEBUG=0) WYMUSZA bezpieczne ustawienia: klucz ze
    zmiennej środowiskowej, HTTPS, ciasteczka z prefiksem __Host-, HSTS,
  * baza: DATABASE_URL (np. PostgreSQL w docker-compose), domyślnie SQLite.

Żadnych sekretów w repozytorium – patrz .env.example.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from csp.constants import NONCE, NONE, SELF
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
TESTY = len(sys.argv) > 1 and sys.argv[1] == "test"


def _env_bool(nazwa: str, domyslnie: bool = False) -> bool:
    """Zmienna środowiskowa jako bool ("1", "true", "tak", "on" => True)."""
    wartosc = os.environ.get(nazwa)
    if wartosc is None:
        return domyslnie
    return wartosc.strip().lower() in {"1", "true", "yes", "tak", "on"}


# ---------------------------------------------------------------------------
# Podstawy
# ---------------------------------------------------------------------------

DEBUG = _env_bool("DJANGO_DEBUG", True)

_KLUCZ_DEWELOPERSKI = "dev-tylko-lokalnie-NIE-UZYWAC-NA-PRODUKCJI-krag-4f9e2a"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _KLUCZ_DEWELOPERSKI)
if not DEBUG and (SECRET_KEY == _KLUCZ_DEWELOPERSKI or len(SECRET_KEY) < 50):
    raise ImproperlyConfigured("Na produkcji ustaw DJANGO_SECRET_KEY (min. 50 znaków).")
# Rotacja klucza bez wylogowania wszystkich: stary klucz jako fallback.
SECRET_KEY_FALLBACKS = [k for k in os.environ.get("DJANGO_SECRET_KEY_FALLBACKS", "").split(",") if k]

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver").split(",")
    if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]


# ---------------------------------------------------------------------------
# Aplikacje i middleware
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",        # blokada po serii nieudanych logowań (brute force)
    "csp",         # Content-Security-Policy z nonce
    # Aplikacje portalu:
    "konta",       # użytkownicy, role, profil, blokady kont, warstwa uprawnień
    "relacje",     # znajomi, zaproszenia, blokowanie osób
    "posty",       # posty, komentarze, polubienia, zdjęcia (serwowane przez widok)
    "grupy",       # grupy publiczne i prywatne
    "wiadomosci",  # prywatne rozmowy 1:1
    "moderacja",   # zgłoszenia, decyzje, historia działań
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    # Własne: no-store dla zalogowanych, dodatkowe nagłówki bezpieczeństwa.
    "konta.middleware.BrakCacheDlaZalogowanychMiddleware",
    "konta.middleware.NaglowkiBezpieczenstwaMiddleware",
    # axes musi być ostatni.
    "axes.middleware.AxesMiddleware",
]

if DEBUG or TESTY:
    # Lokalnie pliki statyczne serwuje runserver (staticfiles); WhiteNoise jest
    # potrzebny dopiero na produkcji, po collectstatic.
    MIDDLEWARE.remove("whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "konta.context_processors.role",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# Baza danych: DATABASE_URL (PostgreSQL zalecany na serwerze), domyślnie SQLite
# ---------------------------------------------------------------------------

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60,
        conn_health_checks=True,
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Uwierzytelnianie
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "konta.Uzytkownik"
LOGIN_URL = "konta:logowanie"
LOGIN_REDIRECT_URL = "posty:tablica"
LOGOUT_REDIRECT_URL = "konta:logowanie"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",        # najpierw sprawdza blokadę po próbach
    "konta.backends.TylkoNiezablokowaniBackend",  # zablokowane konto = brak logowania
]

# Argon2 – zwycięzca Password Hashing Competition, odporny na łamanie na GPU.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
if TESTY:
    # Testy tworzą setki kont – szybki hasher wyłącznie w testach.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# django-axes: 5 nieudanych prób dla pary (login, IP) = blokada na 30 minut.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=30)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "konta/zablokowane_logowanie.html"
AXES_VERBOSE = False


# ---------------------------------------------------------------------------
# Sesje, ciasteczka, nagłówki
# ---------------------------------------------------------------------------

SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Content-Security-Policy: wszystko tylko z własnej domeny (Bootstrap jest w static/vendor,
# bez CDN – brak zależności od cudzego serwera), skrypty inline wyłącznie z nonce.
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF, NONCE],
        "style-src": [SELF],
        "img-src": [SELF, "data:"],
        "font-src": [SELF],
        "connect-src": [SELF],
        "object-src": [NONE],
        "base-uri": [SELF],
        "form-action": [SELF],
        "frame-ancestors": [NONE],
    },
}

if not DEBUG:
    SECURE_SSL_REDIRECT = _env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Prefiks __Host-: przeglądarka przyjmie ciasteczko tylko z HTTPS, bez Domain,
    # z Path=/ – nie podrzuci go subdomena.
    SESSION_COOKIE_NAME = "__Host-sesja"
    CSRF_COOKIE_NAME = "__Host-csrf"
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    if _env_bool("DJANGO_BEHIND_PROXY", True):
        # Render / PythonAnywhere / nginx terminują TLS i przekazują ten nagłówek.
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ---------------------------------------------------------------------------
# Pliki statyczne i przesyłane
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
if TESTY or DEBUG:
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}

# Pliki użytkowników NIE mają publicznego MEDIA_URL – są serwowane wyłącznie
# przez widoki sprawdzające uprawnienia (posty.views_pliki).
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))
if TESTY:
    import tempfile
    MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="krag_media_"))

MAKS_ROZMIAR_OBRAZU = 5 * 1024 * 1024  # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024


# ---------------------------------------------------------------------------
# Lokalizacja
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

ADMIN_URL = os.environ.get("DJANGO_ADMIN_URL", "zaplecze-admin/")


# ---------------------------------------------------------------------------
# Logowanie zdarzeń bezpieczeństwa (audyt)
# ---------------------------------------------------------------------------

LOG_AUDYTU = Path(os.environ.get("DJANGO_LOG_AUDYTU", BASE_DIR / "bezpieczenstwo.log"))
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "audyt": {"format": "{asctime} [{levelname}] {name}: {message}", "style": "{"},
    },
    "handlers": {
        "konsola": {"class": "logging.StreamHandler", "formatter": "audyt"},
        "plik_audytu": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_AUDYTU,
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "audyt",
        },
    },
    "loggers": {
        "bezpieczenstwo": {"handlers": ["konsola", "plik_audytu"], "level": "INFO", "propagate": False},
        "axes": {"handlers": ["konsola", "plik_audytu"], "level": "WARNING", "propagate": False},
        "django.request": {"handlers": ["konsola"], "level": "ERROR", "propagate": False},
    },
}
if TESTY:
    # Testy symulują setki ataków – nie zaśmiecamy prawdziwego logu.
    # assertLogs() działa niezależnie od handlerów.
    LOGGING["handlers"] = {"cisza": {"class": "logging.NullHandler"}}
    for _nazwa in LOGGING["loggers"]:
        LOGGING["loggers"][_nazwa]["handlers"] = ["cisza"]

# Wygasły/brakujący token CSRF – własna, neutralna strona.
CSRF_FAILURE_VIEW = "konta.views.blad_csrf"
