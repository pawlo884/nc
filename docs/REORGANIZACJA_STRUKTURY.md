# 🔄 Dokumentacja Reorganizacji Struktury Projektu NC

## 📋 Spis Treści

1. [Przegląd zmian](#przegląd-zmian)
2. [Nowa struktura folderów](#nowa-struktura-folderów)
3. [Mapa przeniesień plików](#mapa-przeniesień-plików)
4. [Zmiany w kodzie Django](#zmiany-w-kodzie-django)
5. [Zmiany w Docker](#zmiany-w-docker)
6. [Zmiany w skryptach](#zmiany-w-skryptach)
7. [Zmiany w GitHub Actions](#zmiany-w-github-actions)
8. [Instrukcje wykonania](#instrukcje-wykonania)
9. [Rozwiązanie dla aplikacji Django](#rozwiązanie-dla-aplikacji-django)

---

## 📊 Przegląd zmian

### Cel reorganizacji

Uporządkowanie struktury projektu zgodnie z najlepszymi praktykami:

- **Infrastruktura i deployment** → `deployments/`
- **Kod źródłowy Django** → `src/`
- **Skrypty pomocnicze** → `scripts/` (z podfolderami)
- **Dokumentacja** → `docs/` (już istnieje)

### Główne zmiany

- `nc/` → `src/core/` (ustawienia, urls, celery, middleware)
- Aplikacje Django → `src/apps/` (MPD, matterhorn1, web_agent, tabu)
- Dockerfiles → `deployments/docker/`
- docker-compose files → `docker-compose/`
- Scripts → `scripts/` z podfolderami (db/, git/, migrations/, ops/)

---

## 📁 Nowa struktura folderów

```
NC_PROJECT/
├── .cursor/                    # Foldery narzędziowe (zostają w root)
├── .github/                    # GitHub workflows
├── .husky/                     # Git hooks
│
├── deployments/                # --- INFRASTRUKTURA I DEPLOY ---
│   ├── docker/
│   │   ├── Dockerfile.dev
│   │   ├── Dockerfile.prod
│   │   ├── Dockerfile.ml
│   │   └── docker-entrypoint.sh
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── nginx-blue-green.conf
│   └── redis.conf
│
├── docker-compose/             # Pliki compose w jednym miejscu
│   ├── docker-compose.dev.yml
│   ├── docker-compose.dev.ml.yml
│   ├── docker-compose.blue-green.yml
│   └── docker-compose.blue-green.ml.yml
│
├── scripts/                    # --- SKRYPTY POMOCNICZE ---
│   ├── db/
│   │   ├── clean_test_databases.py
│   │   └── clean-test-databases.ps1
│   ├── git/
│   │   ├── commit-test-fixes.sh
│   │   └── commit-test-fixes.ps1
│   ├── migrations/
│   │   ├── run-migrations-dev.sh
│   │   └── run-migrations-dev.ps1
│   ├── ops/
│   │   ├── deploy-blue-green.sh
│   │   └── switch-blue-green.sh
│   ├── build/                  # (już istnieje)
│   ├── deploy/                 # (już istnieje)
│   ├── monitoring/             # (już istnieje)
│   └── security/               # (już istnieje)
│
├── docs/                       # --- DOKUMENTACJA ---
│   ├── BLUE_GREEN_DEPLOYMENT.md
│   ├── CHANGELOG.md
│   └── ... (pozostałe pliki)
│
├── src/                        # --- KOD ŹRÓDŁOWY (DJANGO) ---
│   ├── manage.py
│   ├── requirements.txt
│   ├── requirements.ml.txt
│   ├── core/                   # (obecne "nc" - ustawienia)
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   └── prod.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   ├── asgi.py
│   │   ├── celery.py
│   │   ├── middleware.py
│   │   ├── db_routers.py
│   │   ├── views.py
│   │   └── db_backend/
│   ├── apps/                   # Aplikacje Django
│   │   ├── __init__.py
│   │   ├── MPD/
│   │   ├── matterhorn1/
│   │   ├── web_agent/
│   │   └── tabu/
│   ├── templates/              # (przeniesione z root)
│   ├── static/                 # (jeśli istnieje)
│   └── tests/                  # (jeśli istnieje)
│
├── .env.dev                    # (zostaje w root)
├── .gitignore
├── package.json
├── package-lock.json
├── .prettierrc
├── commitlint.config.mjs
├── .releaserc.json
└── README.md
```

---

## 🗺️ Mapa przeniesień plików

### Infrastruktura (deployments/)

| Stara lokalizacja             | Nowa lokalizacja                          |
| ----------------------------- | ----------------------------------------- |
| `Dockerfile.dev`              | `deployments/docker/Dockerfile.dev`       |
| `Dockerfile.prod`             | `deployments/docker/Dockerfile.prod`      |
| `Dockerfile.ml`               | `deployments/docker/Dockerfile.ml`        |
| `docker/docker-entrypoint.sh` | `deployments/docker/docker-entrypoint.sh` |
| `nginx.conf`                  | `deployments/nginx/nginx.conf`            |
| `nginx-blue-green.conf`       | `deployments/nginx/nginx-blue-green.conf` |
| `redis.conf`                  | `deployments/redis.conf`                  |

### Docker Compose (docker-compose/)

| Stara lokalizacja                  | Nowa lokalizacja                                  |
| ---------------------------------- | ------------------------------------------------- |
| `docker-compose.dev.yml`           | `docker-compose/docker-compose.dev.yml`           |
| `docker-compose.dev.ml.yml`        | `docker-compose/docker-compose.dev.ml.yml`        |
| `docker-compose.blue-green.yml`    | `docker-compose/docker-compose.blue-green.yml`    |
| `docker-compose.blue-green.ml.yml` | `docker-compose/docker-compose.blue-green.ml.yml` |

### Skrypty (scripts/)

| Stara lokalizacja          | Nowa lokalizacja                            |
| -------------------------- | ------------------------------------------- |
| `clean_test_databases.py`  | `scripts/db/clean_test_databases.py`        |
| `clean-test-databases.ps1` | `scripts/db/clean-test-databases.ps1`       |
| `commit-test-fixes.sh`     | `scripts/git/commit-test-fixes.sh`          |
| `commit-test-fixes.ps1`    | `scripts/git/commit-test-fixes.ps1`         |
| `run-migrations-dev.sh`    | `scripts/migrations/run-migrations-dev.sh`  |
| `run-migrations-dev.ps1`   | `scripts/migrations/run-migrations-dev.ps1` |
| `deploy-blue-green.sh`     | `scripts/ops/deploy-blue-green.sh`          |
| `switch-blue-green.sh`     | `scripts/ops/switch-blue-green.sh`          |

### Kod źródłowy (src/)

| Stara lokalizacja     | Nowa lokalizacja          |
| --------------------- | ------------------------- |
| `nc/`                 | `src/core/`               |
| `MPD/`                | `src/apps/MPD/`           |
| `matterhorn1/`        | `src/apps/matterhorn1/`   |
| `web_agent/`          | `src/apps/web_agent/`     |
| `tabu/`               | `src/apps/tabu/`          |
| `manage.py`           | `src/manage.py`           |
| `requirements.txt`    | `src/requirements.txt`    |
| `requirements.ml.txt` | `src/requirements.ml.txt` |
| `templates/`          | `src/templates/`          |

### Dokumentacja (docs/)

| Stara lokalizacja          | Nowa lokalizacja                          |
| -------------------------- | ----------------------------------------- |
| `BLUE_GREEN_DEPLOYMENT.md` | `docs/BLUE_GREEN_DEPLOYMENT.md` (już tam) |
| `CHANGELOG.md`             | `docs/CHANGELOG.md` (już tam)             |

---

## ⚙️ Zmiany w kodzie Django

### 1. BASE_DIR w settings

**Plik:** `src/core/settings/base.py`

**Przed:**

```python
BASE_DIR = Path(__file__).resolve().parent.parent.parent
```

**Po:**

```python
# BASE_DIR wskazuje na root projektu (tam gdzie jest manage.py, .env.dev, etc.)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
```

**Wyjaśnienie:**

- Przed: `nc/settings/base.py` → `parent.parent.parent` = root
- Po: `src/core/settings/base.py` → `parent.parent.parent.parent` = root

### 2. Ścieżki do plików w settings

**Plik:** `src/core/settings/base.py`

**Zmiany:**

```python
# Przed:
TEMPLATES = [
    {
        'DIRS': [BASE_DIR / 'templates'],
    },
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]

# Po:
TEMPLATES = [
    {
        'DIRS': [BASE_DIR / 'src' / 'templates'],
    },
]
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Zostaje w root
STATICFILES_DIRS = [BASE_DIR / 'src' / 'static'] if os.path.exists(BASE_DIR / 'src' / 'static') else []
LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]  # Zostaje w root jeśli istnieje
```

### 3. ROOT_URLCONF

**Plik:** `src/core/settings/base.py`

**Przed:**

```python
ROOT_URLCONF = 'nc.urls'
```

**Po:**

```python
ROOT_URLCONF = 'core.urls'
```

### 4. WSGI_APPLICATION

**Plik:** `src/core/settings/base.py`

**Przed:**

```python
WSGI_APPLICATION = 'nc.wsgi.application'
```

**Po:**

```python
WSGI_APPLICATION = 'core.wsgi.application'
```

### 5. INSTALLED_APPS

**Plik:** `src/core/settings/base.py`

**Uwaga:** INSTALLED_APPS pozostaje **bez zmian** dzięki dodaniu `src/apps/` do `sys.path`.

```python
# Pozostaje bez zmian:
INSTALLED_APPS = [
    # ...
    'MPD',
    'matterhorn1',
    'web_agent',
    'tabu',
]
```

### 6. Importy w settings/dev.py

**Plik:** `src/core/settings/dev.py`

**Przed:**

```python
from nc.middleware import get_debug
```

**Po:**

```python
from core.middleware import get_debug
```

### 7. Importy w celery.py

**Plik:** `src/core/celery.py`

**Przed:**

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'nc.settings.dev'))
app = Celery('nc')
```

**Po:**

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'core.settings.dev'))
app = Celery('core')  # Opcjonalnie: może pozostać 'nc' dla kompatybilności
```

### 8. Importy w urls.py

**Plik:** `src/core/urls.py`

**Przed:**

```python
from nc.views import index, health_check
```

**Po:**

```python
from core.views import index, health_check
```

### 9. Importy w middleware

**Plik:** `src/core/middleware.py`

Jeśli są importy z `nc.*`, zmienić na `core.*`.

### 10. Importy w wsgi.py/asgi.py

**Plik:** `src/core/wsgi.py`, `src/core/asgi.py`

**Przed:**

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings')
```

**Po:**

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
```

### 11. manage.py

**Plik:** `src/manage.py`

**Przed:**

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings')
```

**Po:**

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# Dodaj src/apps/ do sys.path, żeby Django mógł znaleźć aplikacje
BASE_DIR = Path(__file__).resolve().parent
APPS_DIR = BASE_DIR / 'apps'
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
```

---

## 🐳 Zmiany w Docker

### 1. Dockerfile.dev

**Plik:** `deployments/docker/Dockerfile.dev`

**Główne zmiany:**

- `WORKDIR /app` → zmienić na `WORKDIR /app/src` LUB pozostawić `/app` i kopiować z `src/`
- `COPY requirements.txt .` → `COPY src/requirements.txt .`
- `COPY . .` → `COPY src/ .` (lub inna strategia)
- `ENV DJANGO_SETTINGS_MODULE=nc.settings.dev` → `ENV DJANGO_SETTINGS_MODULE=core.settings.dev`
- `RUN python manage.py collectstatic` → ścieżka do `src/manage.py`

**Przykład:**

```dockerfile
# syntax=docker/dockerfile:1.4
FROM python:3.13-slim

# ... instalacja pakietów ...

# Ustaw katalog roboczy
WORKDIR /app

# Skopiuj requirements i zainstaluj
COPY src/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --break-system-packages -r requirements.txt

# Dodaj src/ do PYTHONPATH, żeby Python mógł znaleźć aplikacje
ENV PYTHONPATH=/app:/app/apps

# Skopiuj cały kod źródłowy
COPY src/ .

# ... reszta ...
ENV DJANGO_SETTINGS_MODULE=core.settings.dev

# Zbierz pliki statyczne
RUN python manage.py collectstatic --noinput --skip-checks
```

### 2. Dockerfile.prod

**Plik:** `deployments/docker/Dockerfile.prod`

Podobne zmiany jak w Dockerfile.dev:

```dockerfile
WORKDIR /app
ENV PYTHONPATH=/app:/app/apps
COPY src/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --break-system-packages -r requirements.txt

COPY src/manage.py .
COPY src/core/ ./core/
COPY src/apps/ ./apps/
COPY src/templates/ ./templates/
COPY deployments/nginx/nginx.conf ./nginx.conf
COPY deployments/redis.conf ./redis.conf
COPY deployments/docker/docker-entrypoint.sh ./docker/docker-entrypoint.sh

ENV DJANGO_SETTINGS_MODULE=core.settings.prod
RUN python manage.py collectstatic --noinput --clear
```

### 3. Dockerfile.ml

**Plik:** `deployments/docker/Dockerfile.ml`

Podobne zmiany jak w Dockerfile.prod.

### 4. docker-compose.dev.yml

**Plik:** `docker-compose/docker-compose.dev.yml`

**Zmiany:**

```yaml
services:
  static-init:
    build:
      context: .
      dockerfile: deployments/docker/Dockerfile.dev # Zmiana ścieżki
    environment:
      - DJANGO_SETTINGS_MODULE=core.settings.dev # Zmiana
    volumes:
      - ./src:/app # Zmiana z .:/app na ./src:/app

  web:
    build:
      context: .
      dockerfile: deployments/docker/Dockerfile.dev # Zmiana ścieżki
    environment:
      - DJANGO_SETTINGS_MODULE=core.settings.dev # Zmiana
    volumes:
      - ./src:/app # Zmiana
      - static_volume:/app/staticfiles
    command:
      - '/bin/bash'
      - '-c'
      - 'python manage.py makemigrations && python manage.py migrate --database=zzz_default && gunicorn core.wsgi:application --bind 0.0.0.0:8000 ...' # core.wsgi

  nginx:
    volumes:
      - ./deployments/nginx/nginx.conf:/etc/nginx/conf.d/default.conf # Zmiana ścieżki
      - static_volume:/app/staticfiles

  redis:
    volumes:
      - ./deployments/redis.conf:/usr/local/etc/redis/redis.conf:ro # Zmiana ścieżki


  # ... wszystkie inne serwisy z podobnymi zmianami ...
```

### 5. docker-compose.blue-green.yml

**Plik:** `docker-compose/docker-compose.blue-green.yml`

Podobne zmiany:

- `dockerfile: Dockerfile.prod` → `dockerfile: deployments/docker/Dockerfile.prod`
- `gunicorn nc.wsgi:application` → `gunicorn core.wsgi:application`
- `DJANGO_SETTINGS_MODULE=nc.settings.prod` → `DJANGO_SETTINGS_MODULE=core.settings.prod`
- Volumes: `.:/app` → `./src:/app`

### 6. docker-entrypoint.sh

**Plik:** `deployments/docker/docker-entrypoint.sh`

Jeśli są ścieżki do plików, sprawdzić czy wymagają aktualizacji.

---

## 📜 Zmiany w skryptach

### 1. Scripts w scripts/db/

**Pliki:** `scripts/db/clean_test_databases.py`, `scripts/db/clean-test-databases.ps1`

Sprawdzić importy Django - mogą wymagać aktualizacji ścieżek.

### 2. Scripts w scripts/migrations/

**Pliki:** `scripts/migrations/run-migrations-dev.sh`, `scripts/migrations/run-migrations-dev.ps1`

**Zmiany:**

```bash
# Przed:
cd /path/to/project
python manage.py migrate --database=zzz_default --settings=nc.settings.dev

# Po:
cd /path/to/project/src
python manage.py migrate --database=zzz_default --settings=core.settings.dev
```

### 3. Scripts w scripts/ops/

**Pliki:** `scripts/ops/deploy-blue-green.sh`, `scripts/ops/switch-blue-green.sh`

**Zmiany w deploy-blue-green.sh:**

```bash
# Przed:
COMPOSE_FILE="$APP_DIR/docker-compose.blue-green.yml"

# Po:
COMPOSE_FILE="$APP_DIR/docker-compose/docker-compose.blue-green.yml"
```

### 4. Scripts w scripts/deploy/

Sprawdzić wszystkie skrypty w `scripts/deploy/` - mogą zawierać ścieżki do docker-compose lub Dockerfile.

### 5. Scripts w scripts/build/

**Pliki:** `scripts/build/build-fast.sh`, `scripts/build/build-fast.ps1`

Sprawdzić ścieżki do Dockerfile:

```bash
# Przed:
dockerfile: ./Dockerfile.dev

# Po:
dockerfile: ./deployments/docker/Dockerfile.dev
```

---

## 🔄 Zmiany w GitHub Actions

### 1. .github/workflows/deploy.yml

**Zmiany:**

```yaml
- name: Build and push main app
  uses: docker/build-push-action@v4
  with:
    context: .
    file: ./deployments/docker/Dockerfile.prod # Zmiana ścieżki
    # ...

- name: Build and push ML app
  uses: docker/build-push-action@v4
  with:
    context: .
    file: ./deployments/docker/Dockerfile.ml # Zmiana ścieżki
```

### 2. .github/workflows/deploy-vps.yml

Sprawdzić wszystkie ścieżki do docker-compose i Dockerfile.

---

## 🔧 Rozwiązanie dla aplikacji Django

### Problem

Aplikacje Django (`MPD`, `matterhorn1`, `web_agent`, `tabu`) będą w folderze `src/apps/`, ale Django domyślnie szuka aplikacji w `sys.path` lub w katalogu projektu.

### Rozwiązanie

#### Opcja 1: Dodanie do sys.path w manage.py (ZALECANE)

**Plik:** `src/manage.py`

Dodać na początku (przed importem Django):

```python
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APPS_DIR = BASE_DIR / 'apps'
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))
```

#### Opcja 2: Ustawienie PYTHONPATH w Dockerfile

**Plik:** `deployments/docker/Dockerfile.dev` (i inne)

```dockerfile
ENV PYTHONPATH=/app:/app/apps
```

Lub:

```dockerfile
ENV PYTHONPATH=/app/src:/app/src/apps
```

#### Opcja 3: Używanie pełnych ścieżek w INSTALLED_APPS (NIE ZALECANE)

**Plik:** `src/core/settings/base.py`

```python
INSTALLED_APPS = [
    # ...
    'apps.MPD',
    'apps.matterhorn1',
    'apps.web_agent',
    'apps.tabu',
]
```

**Uwaga:** Ta opcja wymaga aktualizacji wszystkich importów w aplikacjach Django (np. `from apps.MPD.models import ...`).

### ✅ Rekomendowane rozwiązanie

**Użyć Opcji 1 + Opcji 2 razem:**

- Opcja 1 (manage.py) - działa lokalnie
- Opcja 2 (PYTHONPATH w Docker) - działa w kontenerach

**INSTALLED_APPS pozostaje bez zmian:**

```python
INSTALLED_APPS = [
    # ...
    'MPD',
    'matterhorn1',
    'web_agent',
    'tabu',
]
```

---

## 📝 Instrukcje wykonania

### ⚠️ UWAGA: To duża zmiana!

**Zalecane kroki:**

1. ✅ Utwórz branch: `git checkout -b reorganizacja-struktury`
2. ✅ Zrób backup: `git tag backup-przed-reorganizacja`
3. ✅ Przetestuj na środowisku dev
4. ✅ Sprawdź czy wszystko działa
5. ✅ Dopiero potem merge do main

### Krok 1: Utworzenie nowej struktury folderów

```bash
# Utwórz nowe foldery
mkdir -p deployments/docker
mkdir -p deployments/nginx
mkdir -p docker-compose
mkdir -p scripts/db
mkdir -p scripts/git
mkdir -p scripts/migrations
mkdir -p scripts/ops
mkdir -p src/core
mkdir -p src/apps
mkdir -p src/templates
```

### Krok 2: Przeniesienie plików infrastruktury

```bash
# Dockerfiles
mv Dockerfile.dev deployments/docker/
mv Dockerfile.prod deployments/docker/
mv Dockerfile.ml deployments/docker/
mv docker/docker-entrypoint.sh deployments/docker/
rmdir docker 2>/dev/null || true

# Nginx
mv nginx.conf deployments/nginx/
mv nginx-blue-green.conf deployments/nginx/ 2>/dev/null || true

# Redis
mv redis.conf deployments/

# Docker Compose
mv docker-compose.dev.yml docker-compose/
mv docker-compose.dev.ml.yml docker-compose/
mv docker-compose.blue-green.yml docker-compose/
mv docker-compose.blue-green.ml.yml docker-compose/
```

### Krok 3: Przeniesienie skryptów

```bash
# DB scripts
mv clean_test_databases.py scripts/db/
mv clean-test-databases.ps1 scripts/db/

# Git scripts
mv commit-test-fixes.sh scripts/git/
mv commit-test-fixes.ps1 scripts/git/

# Migration scripts
mv run-migrations-dev.sh scripts/migrations/
mv run-migrations-dev.ps1 scripts/migrations/

# Ops scripts
mv deploy-blue-green.sh scripts/ops/
mv switch-blue-green.sh scripts/ops/
```

### Krok 4: Przeniesienie kodu źródłowego

```bash
# Core (nc -> src/core)
mv nc src/core

# Aplikacje
mv MPD src/apps/
mv matterhorn1 src/apps/
mv web_agent src/apps/
mv tabu src/apps/

# Manage.py i requirements
mv manage.py src/
mv requirements.txt src/
mv requirements.ml.txt src/

# Templates
mv templates src/
```

### Krok 5: Aktualizacja kodu Django

Zaktualizuj wszystkie pliki zgodnie z sekcją [Zmiany w kodzie Django](#zmiany-w-kodzie-django).

### Krok 6: Aktualizacja Docker

Zaktualizuj wszystkie pliki zgodnie z sekcją [Zmiany w Docker](#zmiany-w-docker).

### Krok 7: Aktualizacja skryptów

Zaktualizuj wszystkie skrypty zgodnie z sekcją [Zmiany w skryptach](#zmiany-w-skryptach).

### Krok 8: Aktualizacja GitHub Actions

Zaktualizuj workflow zgodnie z sekcją [Zmiany w GitHub Actions](#zmiany-w-github-actions).

### Krok 9: Aktualizacja dokumentacji

Zaktualizuj:

- `README.md` - ścieżki do plików
- `docs/HOW_TO_CREATE_NEW_APP.md` - ścieżki do settings
- Inne pliki dokumentacji z ścieżkami

### Krok 10: Testowanie

```bash
# W katalogu src/
cd src
python manage.py check --settings=core.settings.dev
python manage.py migrate --database=zzz_default --settings=core.settings.dev
python manage.py runserver --settings=core.settings.dev
```

### Krok 11: Testowanie Docker

```bash
# Z katalogu głównego projektu
docker-compose -f docker-compose/docker-compose.dev.yml build
docker-compose -f docker-compose/docker-compose.dev.yml up -d
```

---

## ✅ Checklist wykonania

- [ ] Utworzono nową strukturę folderów
- [ ] Przeniesiono pliki infrastruktury (deployments/)
- [ ] Przeniesiono docker-compose files
- [ ] Przeniesiono skrypty
- [ ] Przeniesiono kod źródłowy (src/)
- [ ] Zaktualizowano BASE_DIR w settings
- [ ] Zaktualizowano ROOT_URLCONF
- [ ] Zaktualizowano WSGI_APPLICATION
- [ ] Zaktualizowano DJANGO_SETTINGS_MODULE (wszędzie)
- [ ] Zaktualizowano importy (nc._ → core._)
- [ ] Zaktualizowano manage.py (dodano sys.path)
- [ ] Zaktualizowano Dockerfiles
- [ ] Zaktualizowano docker-compose files
- [ ] Zaktualizowano skrypty
- [ ] Zaktualizowano GitHub Actions
- [ ] Zaktualizowano dokumentację
- [ ] Przetestowano lokalnie
- [ ] Przetestowano w Docker
- [ ] Wszystko działa ✅

---

## 🐛 Potencjalne problemy i rozwiązania

### Problem 1: Django nie znajduje aplikacji

**Rozwiązanie:** Sprawdź czy `src/apps/` jest w `sys.path` (manage.py) i `PYTHONPATH` (Dockerfile).

### Problem 2: ImportError: No module named 'nc'

**Rozwiązanie:** Zmień wszystkie importy z `nc.*` na `core.*`.

### Problem 3: Docker build nie znajduje plików

**Rozwiązanie:** Sprawdź `context` i ścieżki w Dockerfile (COPY commands).

### Problem 4: Celery nie znajduje tasków

**Rozwiązanie:** Sprawdź `DJANGO_SETTINGS_MODULE` w kontenerze celery.

### Problem 5: Nginx nie znajduje konfiguracji

**Rozwiązanie:** Sprawdź volume mount w docker-compose: `./deployments/nginx/nginx.conf:/etc/nginx/conf.d/default.conf`

---

## 📚 Dodatkowe informacje

### Dokumentacja Django

Django nie wymusza konkretnej struktury folderów. Aplikacje mogą być:

- W root projektu (jak było)
- W folderze `apps/` (jak będzie)
- W folderze `src/apps/` (jak będzie)

Kluczowe jest, żeby Python mógł je znaleźć przez `sys.path` lub `PYTHONPATH`.

### Best Practices

1. **Separation of Concerns**: Infrastruktura oddzielona od kodu
2. **Clear Structure**: Łatwiejsze znalezienie plików
3. **Scalability**: Łatwiejsze dodawanie nowych aplikacji
4. **Maintainability**: Łatwiejsze zarządzanie projektem

---

## 📞 Wsparcie

Jeśli masz pytania lub problemy podczas reorganizacji:

1. Sprawdź ten dokument
2. Sprawdź logi Django/Docker
3. Sprawdź czy wszystkie ścieżki są poprawne
4. Przetestuj na środowisku dev przed produkcją

---

**Data utworzenia:** 2025-01-XX  
**Ostatnia aktualizacja:** 2025-01-XX  
**Autor:** Dokumentacja reorganizacji struktury projektu NC
