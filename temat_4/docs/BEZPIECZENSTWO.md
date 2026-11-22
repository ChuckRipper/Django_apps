# Krąg – model zagrożeń i mechanizmy bezpieczeństwa

Dokument opisuje, przed czym chroni portal, jak to robi i który test to sprawdza.
Kategorie według OWASP Top 10:2025.

## 1. Kontrola dostępu do obiektów (A01: Broken Access Control)

Podstawowe zagrożenie w tym projekcie to **IDOR**: użytkownik podmienia identyfikator w adresie
(posta, zdjęcia, rozmowy, grupy) i dostaje cudze dane. Obrona ma trzy warstwy.

| Warstwa | Mechanizm | Gdzie |
|---|---|---|
| 1. Zbiór zawężony do użytkownika | Reguły są **tylko** w metodach QuerySet: `Post.objects.widoczne_dla(user)`, `edytowalne_przez`, `usuwalne_przez`, `Komentarz…`, `Rozmowa.objects.dostepne_dla`, `Grupa…zarzadzane_przez`, `relacje.uslugi.widoczni_dla`. Widok nigdy nie robi `get(pk=...)` na pełnej tabeli. | `*/models.py`, `relacje/uslugi.py` |
| 2. Bezpieczne domyślne zachowanie | `ObiektDlaUzytkownikaMixin.get_queryset()` rzuca `ImproperlyConfigured`, dopóki widok go nie nadpisze, więc pominięcie reguły to błąd od razu, a nie cicha dziura. `pobierz_lub_odmow()` zastępuje `get_object_or_404`. | `konta/uprawnienia.py` |
| 3. Nieprzewidywalne identyfikatory | UUID dla użytkowników, postów, komentarzy, grup, członkostw, rozmów, wiadomości, zgłoszeń i akcji moderatorów. | modele |

Pozostałe zasady:

- **Nie istnieje = nie dla Ciebie.** Brak obiektu w zbiorze daje zawsze to samo 403. Testy
  porównują treść odpowiedzi dla cudzego obiektu i dla losowego UUID (scenariusz 13).
- **GET i POST chronione tak samo.** `dispatch()` pobiera obiekt przed obsługą metody, a akcje
  zmieniające dane (polubienie, komentarz, zaproszenie) najpierw pobierają cel z zawężonego zbioru.
- **Brak wyjątków dla ról.** Moderator i administrator nie widzą postów „znajomi” i „tylko ja”
  ani rozmów prywatnych. Moderator widzi zgłoszoną treść tylko przez zgłoszenie (kopia z chwili
  zgłoszenia + zdjęcie przez osobny widok `moderacja:zdjecie`). To decyzja *privacy by design*:
  „pełny dostęp” administratora dotyczy zarządzania, nie czytania prywatnych treści.
- **Blokada osoby działa w obie strony** i obejmuje profil, posty, komentarze, avatar,
  wiadomości, zaproszenia i wyszukiwarkę.

## 2. Mass assignment i integralność danych (A08)

- Formularze mają jawne `fields`, nigdy `"__all__"`.
- Pola wrażliwe są ustawiane w widoku lub w `save()`, a nie z żądania: `autor`, `nadawca`,
  `zglaszajacy`, `zalozyciel`, `grupa`, `rola`, `is_staff`, `is_superuser`, `zablokowany_do`,
  `ukryty`.
- Ograniczenia bazy danych: jedno polubienie na osobę, jedna rozmowa na parę, unikalne zaproszenie,
  brak relacji z samym sobą (`UniqueConstraint`, `CheckConstraint`).

## 3. Uwierzytelnianie i sesje (A07, A04)

| Zagrożenie | Obrona |
|---|---|
| Łamanie hashy po wycieku bazy | Argon2 (`Argon2PasswordHasher`) |
| Słabe hasła | min. 10 znaków, brak podobieństwa do loginu, brak na liście popularnych haseł, nie same cyfry |
| Brute force | django-axes: 5 nieudanych prób dla pary (login, IP), potem 30 minut blokady (HTTP 429) |
| Sprawdzanie, czy konto istnieje | jeden komunikat dla złego hasła, braku konta i konta zablokowanego |
| Session fixation | `login()` zmienia identyfikator sesji |
| Kradzież ciasteczka | `HttpOnly`, `Secure`, prefiks `__Host-`, `SameSite`, sesja 8 h lub do zamknięcia przeglądarki |
| Blokada konta | `TylkoNiezablokowaniBackend.user_can_authenticate()` działa przy logowaniu **i** przy każdym żądaniu, więc otwarta sesja wygasa |

## 4. Ataki cross-site (A01, A05)

| Atak | Obrona |
|---|---|
| CSRF | `CsrfViewMiddleware`, `{% csrf_token %}`, brak `csrf_exempt`; wylogowanie i wszystkie zmiany danych tylko przez POST; `CSRF_COOKIE_SAMESITE=Strict`; własna strona błędu CSRF bez szczegółów technicznych |
| XSS | autoescape szablonów, brak `\|safe` na danych użytkownika, CSP: `script-src 'self' 'nonce-…'`, `object-src 'none'`, `base-uri 'self'` |
| Clickjacking | `X-Frame-Options: DENY` + `frame-ancestors 'none'` |
| Wycieki między kartami / XS-Leaks | `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Resource-Policy: same-origin` |
| Kompromitacja CDN | Bootstrap trzymany lokalnie w `static/vendor`; CSP dopuszcza tylko `'self'` |

## 5. Wspólny komputer – „Wstecz” po wylogowaniu (scenariusz 14)

Po wylogowaniu przeglądarka może pokazać kopię prywatnej strony z pamięci podręcznej
(HTTP cache albo back/forward cache). Sama sesja nie wraca, ale prywatne dane są widoczne
na ekranie. Obrona jest czterowarstwowa:

1. `Cache-Control: no-store, private` (oraz `Pragma`, `Expires`) na każdej stronie
   zalogowanego użytkownika (`BrakCacheDlaZalogowanychMiddleware`),
2. `Clear-Site-Data: "cache", "cookies", "storage"` w odpowiedzi na wylogowanie,
3. skrypt `pageshow`: strona przywrócona z bfcache przeładowuje się, a serwer
   przekierowuje na logowanie,
4. krótka sesja i `SESSION_EXPIRE_AT_BROWSER_CLOSE`.

## 6. Pliki użytkowników (A01, A05)

- Projekt nie ma publicznego `MEDIA_URL`. Zdjęcie posta zwraca widok, który sprawdza
  `Post.objects.widoczne_dla` (scenariusz 3); avatar – widok, który sprawdza `widoczni_dla`.
- Walidacja zawartości (Pillow), a nie rozszerzenia: tylko JPEG, PNG i WebP, maks. 5 MB,
  limit pikseli (ochrona przed bombą dekompresyjną).
- Każdy obraz jest **przekodowany do WebP**: usuwa to EXIF (np. GPS) i doklejony ładunek
  (pliki poliglotyczne). Nazwa pliku jest losowa (brak path traversal i wycieku nazwy).
- `X-Content-Type-Options: nosniff`.

## 7. Minimalizacja danych (A04)

E-maile nie pojawiają się nigdzie poza formularzem rejestracji. Wyszukiwarka zwraca login
i avatar. Data urodzenia i miasto są widoczne tylko dla znajomych. Lista w panelu
administratora pokazuje login, rolę i status. Wiadomości nie są zarejestrowane w panelu admina.

## 8. Audyt i błędy (A09, A10)

- Logger `bezpieczenstwo` (plik z rotacją) zapisuje każdą odmowę (kto, IP, metoda, adres,
  powód), zmiany ról, blokady kont i osób, decyzje moderatorów oraz rejestracje. django-axes
  loguje nieudane logowania.
- Historia działań moderatorów i administratorów (`AkcjaModeratora`) jest tylko dopisywana;
  w panelu admina nie można jej edytować ani usuwać.
- Własne strony 400, 403, 403 CSRF, 404 i 500 bez szczegółów technicznych. Strona 500 nie
  dziedziczy z `base.html`, więc działa nawet przy awarii szablonów.

## 9. Konfiguracja produkcyjna (A02, A03)

- `DEBUG=False`, `SECRET_KEY` ze zmiennej środowiskowej (min. 50 znaków, inaczej aplikacja
  nie wystartuje), `SECRET_KEY_FALLBACKS` do rotacji klucza.
- HTTPS: `SECURE_SSL_REDIRECT`, HSTS na rok (z `preload`), `SECURE_PROXY_SSL_HEADER`.
- `python manage.py check --deploy` bez ostrzeżeń.
- Panel admina pod adresem z `DJANGO_ADMIN_URL`.
- Docker: obraz bez sekretów, proces jako użytkownik bez uprawnień roota, PostgreSQL;
  zależności przypięte w `requirements.txt`.

## 10. Testy

67 testów (`python manage.py test`), w tym co najmniej jeden na każdy z 14 scenariuszy
prowadzącego (`posty/tests/test_scenariusze.py`). Każdy test odmowy sprawdza status 403,
neutralny komunikat i brak chronionych danych (`assertOdmowaBezDanych`). Testy dodatkowe
(`konta/tests/test_dodatkowe.py`) obejmują: CSRF z `enforce_csrf_checks=True`, nagłówki
i nonce CSP, XSS, fałszywe i za duże pliki, moderację (widoczność tylko zgłoszonej treści,
blokada autora, zakaz blokowania wyższej roli), akceptację w grupach, relacje, django-axes
oraz to, że każda strona działa dla każdej roli.

## 11. Znane ograniczenia

- Bez weryfikacji adresu e-mail i bez 2FA (możliwe rozszerzenie: `django-otp`).
- Limit prób dotyczy logowania; dla innych formularzy (np. wiadomości) przydałby się
  rate limiting na poziomie serwera (nginx `limit_req`) lub aplikacji.
- Na darmowym planie Render przesłane pliki znikają po ponownym wdrożeniu (brak trwałego dysku).
