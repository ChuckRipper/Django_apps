# Temat 3 – System zarządzania biblioteką

Aplikacja Django do zarządzania księgozbiorem: CRUD książek z wyszukiwarką, panel admina oraz system wypożyczeń dla czytelników.

## Zrealizowane punkty

### Część podstawowa

| Funkcja | Adres | Stan |
|---|---|---|
| Lista książek (tabela Bootstrap, licznik, akcje) | `/` | ✅ |
| Wyszukiwanie po tytule, autorze, ISBN | `/?q=fraza` | ✅ |
| Dodawanie z walidacją i komunikatem | `/dodaj/` | ✅ |
| Edycja | `/<id>/edytuj/` | ✅ |
| Usuwanie (potwierdzenie, tylko POST) | `/<id>/usun/` | ✅ |
| Panel admina: lista, filtry, wyszukiwarka, edycja liczby egzemplarzy | `/admin/` | ✅ |

### Zadanie dodatkowe – wymagania obowiązkowe (6 pkt)

| Wymaganie | Stan |
|---|---|
| Model `Czytelnik` (imię, nazwisko, unikalny e-mail i nr karty), pełny CRUD + admin | ✅ |
| Model `Wypozyczenie` (FK do książki i czytelnika, termin zwrotu domyślnie +30 dni, data zwrotu) | ✅ |
| Kolumna „Dostępne” (`Ksiazka.dostepne()`), przycisk „Wypożycz” nieaktywny przy 0 | ✅ |
| Formularz odrzuca wypożyczenie bez wolnych egzemplarzy (`clean()`) | ✅ |
| Strona „Wypożyczenia”, „Zwróć” metodą POST, wiersze po terminie na czerwono (`table-danger`) | ✅ |

### Wymagania rozszerzone

| Wymaganie | Stan |
|---|---|
| Dodawanie/edycja/usuwanie tylko dla zalogowanych (`@login_required`), lista dla wszystkich | ✅ |
| Paginacja po 10 pozycji (Bootstrap `pagination`) | ✅ |
| Sortowanie po kliknięciu nagłówka (tytuł, autor, rok) | ✅ |
| Szczegóły czytelnika z historią wypożyczeń | ✅ |
| Wypożyczenia jako `TabularInline` na stronie książki w adminie | ✅ |
| Testy (`ksiazki/tests.py`): dodawanie książki, blokada wypożyczenia bez wolnych egzemplarzy i inne | ✅ |

Testy: 9 (`python manage.py test`).

## Uruchomienie

```
python -m venv venv
venv\Scripts\activate            # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Strona: http://127.0.0.1:8000/ · logowanie: http://127.0.0.1:8000/konto/login/ · admin: http://127.0.0.1:8000/admin/

Konto utworzone przez `createsuperuser` służy też do logowania na stronie (dodawanie, czytelnicy, wypożyczenia).
