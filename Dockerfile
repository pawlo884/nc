# Wybierz obraz bazowy
FROM python:3.13-slim

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
    chmod 777 /var/lib/celery && \
    chmod +x /app/docker-entrypoint.sh && \
    ln -s /app/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Ustaw domyślny command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]