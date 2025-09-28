# Wybierz obraz bazowy
FROM python:3.13-slim

# Wyłącz cache dla tego build
ARG BUILDKIT_INLINE_CACHE=0

# Zaktualizuj system i zainstaluj niezbędne pakiety systemowe
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Utwórz użytkownika celery z dedykowanym UID/GID
RUN groupadd -r celery && useradd -r -g celery -u 1001 celery

# Ustaw katalog roboczy
WORKDIR /app

# Skopiuj plik z zależnościami i zainstaluj je
COPY requirements.txt /app/
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt \
    && pip cache purge

# Skopiuj pliki projektu do kontenera (optymalizacja: kopiuj najpierw pliki, które rzadko się zmieniają)
COPY manage.py /app/
COPY nc/ /app/nc/
COPY matterhorn/ /app/matterhorn/
COPY matterhorn1/ /app/matterhorn1/
COPY MPD/ /app/MPD/
COPY web_agent/ /app/web_agent/
COPY static/ /app/static/

# Skopiuj pliki konfiguracyjne
COPY nginx.conf /app/
COPY redis.conf /app/
COPY docker-compose.yml /app/
COPY docker-compose.dev.yml /app/
COPY package.json /app/
COPY docker-entrypoint.sh /app/

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
RUN python manage.py collectstatic --noinput --clear

# Sprawdź czy pliki admin_interface zostały skopiowane
RUN find /app/staticfiles -name "*admin*" -type f | head -10

# Zmień właściciela plików statycznych na celery
RUN chown -R celery:celery /app/staticfiles

# Przełącz na użytkownika celery
USER celery