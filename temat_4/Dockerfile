# Obraz aplikacji „Krąg”: Python 3.13, gunicorn, użytkownik bez uprawnień roota.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# collectstatic w czasie budowania (klucz tymczasowy – obraz nie zawiera sekretów).
RUN DJANGO_DEBUG=0 DJANGO_SECRET_KEY=tylko-do-collectstatic-tylko-do-collectstatic-tylko \
    python manage.py collectstatic --noinput \
 && useradd --create-home --uid 10001 krag \
 && mkdir -p /app/media /app/logs \
 && chown -R krag:krag /app/media /app/logs

USER krag
ENV DJANGO_MEDIA_ROOT=/app/media DJANGO_LOG_AUDYTU=/app/logs/bezpieczenstwo.log
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --access-logfile -"]
