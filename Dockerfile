# Prosty Dockerfile - bez problemów z cache
FROM python:3.13-slim

# Zainstaluj pakiety systemowe
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Utwórz użytkownika
RUN groupadd -r celery && useradd -r -g celery -u 1001 celery

# Ustaw katalog roboczy
WORKDIR /app

# Skopiuj requirements i zainstaluj zależności
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Skopiuj cały projekt
COPY . .

# Utwórz katalogi
RUN mkdir -p /app/staticfiles /app/logs/matterhorn /var/lib/celery

# Ustaw uprawnienia
RUN chown -R celery:celery /app /var/lib/celery && \
    chmod 755 /var/lib/celery && \
    chmod 755 /app/logs/matterhorn && \
    chmod +x /app/docker-entrypoint.sh

# Uruchom migracje (potrzebne dla admin_interface)
RUN python manage.py migrate --noinput

# Zbierz pliki statyczne
RUN python manage.py collectstatic --noinput --clear

# Zmień właściciela plików statycznych
RUN chown -R celery:celery /app/staticfiles

# Przełącz na użytkownika celery
USER celery

# Ustaw zmienną środowiskową
ENV DJANGO_SETTINGS_MODULE=nc.settings.prod