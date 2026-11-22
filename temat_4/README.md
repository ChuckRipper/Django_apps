# Temat 4 – Krąg: portal społecznościowy w Django

Autor: Cezary Kalinowski (136168), WSB Merito Chorzów, „Aplikacje internetowe w Django”.

Krąg to portal społecznościowy: posty z wyborem widoczności, znajomi, grupy publiczne
i prywatne, prywatne wiadomości oraz moderacja. Każdy użytkownik widzi wyłącznie treści
przeznaczone dla niego. Głównym celem zadania jest odporność na podmianę identyfikatorów
w adresach (IDOR) i inne próby dostępu do cudzych danych.

**Adres wdrożenia:** _(uzupełnić po wdrożeniu)_

## Uruchomienie lokalne (SQLite)

Temat 4 wymaga Django 5.2 (główne `.venv` repozytorium ma Django 6), dlatego ma własne środowisko:

```powershell
cd temat_4
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py dane_demo            # konta testowe + przykładowe treści
python manage.py runserver
```

Testy: `python manage.py test` (67 testów).

## Uruchomienie w Dockerze (PostgreSQL, tryb produkcyjny)

```bash
cp .env.example .env                  # uzupełnij DJANGO_SECRET_KEY i hasła
docker compose up --build
docker compose exec web python manage.py dane_demo --haslo "<mocne hasło>"
docker compose run --rm -e DJANGO_DEBUG=1 web python manage.py test   # testy na PostgreSQL
```

## Konta testowe (`dane_demo`)

| Login | Rola | Uwagi |
|---|---|---|
| `admin` | Administrator | zarządza rolami, blokadami i grupami |
| `moderator` | Moderator | ma jedno zgłoszenie do rozpatrzenia (spam od `celina`) |
| `anna` | Użytkownik | znajoma `bartek`; ma posty publiczne, „znajomi” i „tylko ja” |
| `bartek` | Użytkownik | założyciel prywatnej grupy „Klub książki” |
| `celina` | Użytkownik | nie jest niczyją znajomą; czeka na akceptację w „Klubie książki” |

Hasło lokalne: `Demo!Haslo2026`. Na produkcji `dane_demo` wymaga podania hasła
(`--haslo` albo `DJANGO_DEMO_HASLO`), żeby na publicznym serwerze nie było kont
ze znanym hasłem z README.

## Role i uprawnienia

| Działanie | Użytkownik | Moderator | Administrator |
|---|:-:|:-:|:-:|
| posty, komentarze, polubienia, znajomi, grupy, wiadomości | ✔ | ✔ | ✔ |
| panel zgłoszeń, decyzje (usuń / ukryj / odrzuć / zablokuj autora), historia | – | ✔ | ✔ |
| tymczasowa blokada konta | – | tylko konta o niższej roli | ✔ |
| nadawanie ról, zdejmowanie blokad, usuwanie dowolnych grup | – | – | ✔ (nie na własnym koncie) |
| czytanie cudzych wiadomości prywatnych | – | – | – (nikt) |
| podgląd postów „znajomi” / „tylko ja” bez zgłoszenia | – | – | – (nikt) |

Role nadaje wyłącznie administrator. Rejestracja zawsze tworzy konto z rolą Użytkownik.
Zablokowane konto nie może się zalogować (otwarta sesja wygasa przy następnym żądaniu)
ani niczego publikować.

## Adresy URL

| Adres | Metoda | Kto ma dostęp |
|---|---|---|
| `/konta/rejestracja/`, `/konta/logowanie/` | GET, POST | wszyscy |
| `/konta/wylogowanie/` | POST | zalogowani |
| `/` | GET | zalogowani – tablica: własne posty, posty znajomych i publiczne |
| `/posty/nowy/` | POST | zalogowani, niezablokowani |
| `/posty/<uuid>/` | GET | ci, którzy widzą post (`Post.objects.widoczne_dla`) |
| `/posty/<uuid>/edycja/` | GET, POST | autor |
| `/posty/<uuid>/usun/` | GET, POST | autor, założyciel grupy (dla postów w grupie) |
| `/posty/<uuid>/komentarz/`, `/posty/<uuid>/polub/` | POST | ci, którzy widzą post |
| `/komentarze/<uuid>/usun/` | POST | autor komentarza, autor posta |
| `/pliki/posty/<uuid>/` | GET | ci, którzy widzą post (zdjęcie serwowane przez widok) |
| `/pliki/avatary/<uuid>/` | GET | ci, którzy mogą oglądać profil |
| `/profil/edycja/` | GET, POST | właściciel (adres bez ID) |
| `/u/<login>/` | GET | zalogowani, bez blokady między osobami |
| `/szukaj/` | GET | zalogowani (tylko login i avatar; zablokowani ukryci) |
| `/znajomi/…` | GET, POST | zalogowani – wyłącznie własne relacje |
| `/grupy/`, `/grupy/nowa/`, `/grupy/<uuid>/` | GET, POST | zalogowani; posty grupy prywatnej widzą tylko członkowie |
| `/grupy/<uuid>/czlonkowie/<uuid>/akceptuj|usun/` | POST | założyciel grupy |
| `/grupy/<uuid>/usun/` | GET, POST | założyciel, administrator |
| `/wiadomosci/`, `/wiadomosci/<uuid>/` | GET, POST | wyłącznie uczestnicy rozmowy |
| `/wiadomosci/do/<login>/` | POST | zalogowani, bez blokady między osobami |
| `/zglos/<post|komentarz|uzytkownik>/<id>/` | GET, POST | ci, którzy widzą zgłaszaną treść |
| `/moderacja/`, `/moderacja/<uuid>/`, `/moderacja/historia/` | GET, POST | Moderator+ |
| `/panel/uzytkownicy/`, `/panel/uzytkownicy/<uuid>/` | GET, POST | Administrator |
| `/zaplecze-admin/` | – | superuser Django (adres zmienny: `DJANGO_ADMIN_URL`) |

## Bezpieczeństwo w skrócie

Szczegóły w [`docs/BEZPIECZENSTWO.md`](docs/BEZPIECZENSTWO.md).

- Reguły dostępu są w metodach QuerySet (`widoczne_dla`, `edytowalne_przez`, `usuwalne_przez`,
  `dostepne_dla`). W widokach nie ma `get(pk=...)` bez zawężenia zbioru.
- Odmowa daje neutralne 403 „Ta treść nie jest przeznaczona dla Ciebie.”, identyczne dla obiektu
  nieistniejącego i cudzego. Wszystkie obiekty mają UUID.
- Formularze mają jawne listy pól; autor, nadawca, rola i właściciel są ustawiane w widoku.
- Pliki nie mają publicznego `MEDIA_URL`. Są serwowane przez widoki, przekodowywane do WebP
  (bez EXIF) i dostają losowe nazwy.
- CSP z nonce, Bootstrap trzymany lokalnie (bez CDN), HSTS, ciasteczka `__Host-`, `no-store`,
  `Clear-Site-Data` przy wylogowaniu, Argon2, django-axes (5 prób, potem 30 minut blokady).
- Log audytu `bezpieczenstwo.log`: odmowy, zmiany ról, blokady, decyzje moderatorów.

## Wdrożenie (Render)

1. New → Web Service → repozytorium, Root Directory `temat_4`, Runtime Docker.
2. Dodaj bazę PostgreSQL (Render), jej adres wpisz do `DATABASE_URL`.
3. Zmienne: `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=<nazwa>.onrender.com`,
   `DJANGO_CSRF_TRUSTED_ORIGINS=https://<nazwa>.onrender.com`, `DJANGO_DEMO_HASLO`.
4. Po starcie, w Shell: `python manage.py dane_demo`.

**Uwaga (darmowy plan Render):** dysk kontenera nie jest trwały, więc przesłane avatary
i zdjęcia znikają po każdym ponownym wdrożeniu lub uśpieniu usługi. Dane w PostgreSQL zostają.
Prowadzący dopuszcza to ograniczenie, jeśli jest opisane.

## Struktura

```
config/      ustawienia (env, CSP, axes, argon2, audyt), adresy, obsługa błędów
konta/       model użytkownika z rolą i blokadą, uprawnienia.py, middleware, walidacja obrazów, dane_demo
relacje/     znajomości (zaproszenia) i blokady osób
posty/       posty, komentarze, polubienia, serwowanie zdjęć przez widok
grupy/       grupy publiczne i prywatne, członkostwa
wiadomosci/  rozmowy 1:1
moderacja/   zgłoszenia, decyzje, historia działań
templates/   szablony (Bootstrap 5, własny wygląd), strony 400/403/404/500
```
