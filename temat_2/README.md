# Temat 2 – Blog (`blog_cw1`)

Blog w Django 5.2: lista postów, szczegóły, dodawanie, edycja i usuwanie wpisów z obrazkiem (CRUD) oraz formularz kontaktowy zapisujący wiadomości do CSV.

## Zrealizowane punkty

| Punkt | Stan |
|---|---|
| Część podstawowa (model `Product`, media, admin, `ProductForm`, widoki CRUD, `path()`, szablony, testy) | ✅ |
| Zadanie 1: formularz kontaktowy `/contact/` → `responses.csv`, `success.html`, link „Kontakt” | ✅ |
| Pole `author` + migracja, autor widoczny na liście | ✅ |
| Sortowanie od najnowszego (`order_by('-created_at')`) | ✅ |
| Adres szczegółów jako slug: `/post/moj-pierwszy-post/` (`SlugField`, `<slug:slug>`) | ✅ |
| Wspólny `base.html` z menu, pozostałe szablony przez `{% extends %}` / `{% block %}` | ✅ |
| Test formularza kontaktowego (zapis + przekierowanie na `contact_success`) | ✅ |

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

Strona: http://127.0.0.1:8000/ · panel admina: http://127.0.0.1:8000/admin/

## Adresy

| Adres | Widok |
|---|---|
| `/` | lista postów |
| `/post/<slug>/` | szczegóły posta |
| `/add/` | nowy post |
| `/edit/<id>/` | edycja |
| `/delete/<id>/` | potwierdzenie usunięcia |
| `/contact/` | formularz kontaktowy |
| `/admin/` | panel admina |
