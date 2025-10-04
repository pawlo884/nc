# Prosty Dockerfile - bez problemów z cache
FROM python:3.13-slim

# Zainstaluj pakiety systemowe
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    nginx \
    cron \
    iptables \
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
RUN mkdir -p /app/staticfiles /app/logs/matterhorn /app/logs/nginx_security /var/lib/celery /var/log/nginx

# Ustaw uprawnienia
RUN chown -R celery:celery /app /var/lib/celery && \
    chmod 755 /var/lib/celery && \
    chmod 755 /app/logs/matterhorn && \
    chmod 755 /app/logs/nginx_security && \
    chmod 755 /var/log/nginx && \
    chmod +x /app/docker-entrypoint.sh && \
    chmod +x /app/nginx_security_setup.sh && \
    chmod +x /app/nginx_monitor.py

# Zbierz pliki statyczne (bez migracji - będą uruchomione w entrypoint)
# Używamy --skip-checks aby ominąć sprawdzanie bazy danych
RUN python manage.py collectstatic --noinput --clear --skip-checks

# Zmień właściciela plików statycznych
RUN chown -R celery:celery /app/staticfiles

# Przełącz na użytkownika celery
USER celery

# Ustaw zmienną środowiskową
ENV DJANGO_SETTINGS_MODULE=nc.settings.prod