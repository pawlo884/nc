# Wybierz obraz bazowy
FROM python:3.13-slim

# Utwórz użytkownika celery z dedykowanym UID/GID
RUN groupadd -r celery && useradd -r -g celery -u 1001 celery

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
    chown -R celery:celery /app /var/lib/celery && \
    chmod 755 /var/lib/celery && \
    chmod 755 /app/logs/matterhorn && \
    chmod +x /app/docker-entrypoint.sh && \
    ln -s /app/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Zbierz statyczne pliki jako root (potrzebne dla collectstatic)
RUN python manage.py collectstatic --noinput

# Zmień właściciela plików statycznych na celery
RUN chown -R celery:celery /app/staticfiles

# Przełącz na użytkownika celery
USER celery