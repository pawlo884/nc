# syntax=docker/dockerfile:1.4
# Dockerfile dla ML Container (PyTorch, Sentence Transformers)
FROM python:3.13-slim

# Argument dla daty budowania (wymusza rebuild)
ARG BUILD_DATE
ENV BUILD_DATE=${BUILD_DATE}

# Zainstaluj pakiety systemowe z cache'owaniem apt
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev

# Utwórz użytkownika
RUN groupadd -r celery && useradd -r -g celery -u 1001 celery

# Ustaw katalog roboczy
WORKDIR /app

# WARSTWA 1: Podstawowe zależności (cache rzadko się zmienia)
COPY src/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --break-system-packages -r requirements.txt

# WARSTWA 2: ML zależności ~2-3GB (cache osobno, zmienia się rzadko)
COPY src/requirements.ml.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --break-system-packages -r requirements.ml.txt

# Dodaj src/ do PYTHONPATH, żeby Python mógł znaleźć aplikacje
ENV PYTHONPATH=/app:/app/apps

# Skopiuj tylko potrzebne pliki
COPY src/manage.py .
COPY src/core/ ./core/
COPY src/apps/matterhorn1/ ./matterhorn1/
COPY src/apps/MPD/ ./MPD/
COPY src/apps/web_agent/ ./web_agent/ 2>/dev/null || true
COPY deployments/nginx/nginx.conf ./nginx.conf
COPY deployments/redis.conf ./redis.conf
COPY package.json .
COPY deployments/docker/docker-entrypoint.sh ./docker-entrypoint.sh

# Utwórz katalogi
RUN mkdir -p /app/staticfiles /app/logs/matterhorn /var/lib/celery /var/lib/flower

# Utwórz pliki logów
RUN touch /app/logs/security.log /app/logs/django.log && \
    chmod 666 /app/logs/security.log /app/logs/django.log

# Ustaw uprawnienia
RUN chown -R celery:celery /app /var/lib/celery /var/lib/flower && \
    chmod 755 /var/lib/celery /var/lib/flower && \
    chmod 755 /app/logs/matterhorn && \
    chmod +x /app/docker-entrypoint.sh || true

# Ustaw zmienną środowiskową PRZED collectstatic
ENV DJANGO_SETTINGS_MODULE=core.settings.prod

# Zbierz pliki statyczne
RUN python manage.py collectstatic --noinput --clear

# Zmień właściciela plików statycznych
RUN chown -R celery:celery /app/staticfiles

# Przełącz na użytkownika celery
USER celery

