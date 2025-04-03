# Wybierz obraz bazowy
FROM python:3.12-slim

# Ustaw katalog roboczy
WORKDIR /app

# Skopiuj plik z zależnościami i zainstaluj je
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj pliki projektu do kontenera
COPY . /app/

# Ustaw zmienną środowiskową dla Django
ENV DJANGO_SETTINGS_MODULE=nc.settings.dev

# Zbierz statyczne pliki
RUN python manage.py collectstatic --noinput

# Uruchom migracje i Gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn nc.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]