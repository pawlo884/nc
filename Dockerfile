# Wybierz obraz bazowy
FROM python:3.12-slim

# Zainstaluj psql
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Ustaw katalog roboczy
WORKDIR /app

# Skopiuj plik z zależnościami i zainstaluj je
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj pliki projektu do kontenera
COPY . /app/

# Ustaw zmienną środowiskową dla Django podczas budowania
ENV DJANGO_SETTINGS_MODULE=nc.settings.prod

# Utwórz niezbędne katalogi z odpowiednimi uprawnieniami
RUN mkdir -p /app/static /app/staticfiles /app/logs/matterhorn /var/lib/celery && \
    chmod 777 /var/lib/celery

# Dodaj skrypt inicjalizacyjny
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Zbierz statyczne pliki
RUN python manage.py collectstatic --noinput

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "python manage.py migrate && gunicorn nc.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]