# 🐳 Struktura plików Docker

## 📁 Uporządkowana struktura

Projekt używa CZYTELNEJ struktury z osobnymi plikami dla dev i prod:

```
nc_project/
├── Dockerfile.dev              # Development - Python 3.12 + Django
├── Dockerfile.prod             # Production - zoptymalizowany dla CI/CD
├── docker-compose.dev.yml      # Local development (localhost)
├── docker-compose.prod.yml     # Production (Digital Ocean)
└── requirements.txt            # Wspólne dependencje (bez PyTorch)
```

---

## 🔧 Development (Lokalne środowisko)

### Pliki:
- **Dockerfile.dev** - obraz dla developmentu
  - Python 3.12-slim
  - Django settings: `nc.settings.dev`
  - Cache dla apt i pip (szybki rebuild)
  - Wszystkie pliki projektu skopiowane

- **docker-compose.dev.yml** - orkiestracja local dev
  - Bazy danych z prefiksem `zzz_*`
  - Redis z hasłem `dev_password`
  - Flower bez autentykacji
  - Hot-reload dla gunicorn
  - Volumes z kodem (live editing)

### Użycie:
```bash
# Build
docker-compose -f docker-compose.dev.yml build

# Uruchom
docker-compose -f docker-compose.dev.yml up -d

# Logi
docker-compose -f docker-compose.dev.yml logs -f web

# Stop
docker-compose -f docker-compose.dev.yml down
```

### Env file: `.env.dev`
```env
DB_NAME=zzz_default
REDIS_PASSWORD=dev_password
DJANGO_SETTINGS_MODULE=nc.settings.dev
```

---

## 🚀 Production (Serwer Digital Ocean)

### Pliki:
- **Dockerfile.prod** - zoptymalizowany obraz produkcyjny
  - Python 3.12-slim
  - Django settings: `nc.settings.prod`
  - Tylko potrzebne pliki (bez dev tools)
  - BuildKit cache (szybki rebuild w CI/CD)
  - Collectstatic w czasie buildu

- **docker-compose.prod.yml** - orkiestracja prod
  - **Używa gotowych obrazów z Docker Hub**
  - Bazy danych bez prefiksu `zzz_`
  - Redis z hasłem `prod_password`
  - Flower z basic auth
  - Memory limits dla kontenerów
  - Health checks
  - Restart policies

### Użycie (na serwerze):
```bash
# Pull gotowego obrazu z Docker Hub
docker pull pawlo884/django-app:latest

# Deploy z zero-downtime
bash scripts/deploy/deploy-from-registry.sh

# Lub ręcznie
docker-compose -f docker-compose.prod.yml up -d
```

### Env file: `.env.prod`
```env
DB_NAME=default
REDIS_PASSWORD=prod_password
DJANGO_SETTINGS_MODULE=nc.settings.prod
```

---

## 🔄 GitHub Actions CI/CD

### Deploy workflow (`.github/workflows/deploy.yml`):

```yaml
jobs:
  build-and-deploy:
    steps:
      # 1. Build obrazu z cache
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          file: ./Dockerfile.prod  # ← Używa Dockerfile.prod
          cache-from: type=registry,ref=pawlo884/django-app:buildcache
          cache-to: type=registry,ref=pawlo884/django-app:buildcache,mode=max
          
      # 2. Deploy na Digital Ocean
      - name: Deploy
        run: bash scripts/deploy/deploy-from-registry.sh  # ← Używa docker-compose.prod.yml
```

### Czasy buildów:
| Zmiana | Czas | Cache |
|--------|------|-------|
| Tylko kod | ~2-3 min | ✅ Pełny |
| + requirements | ~4-5 min | ⚡ Częściowy |
| Wszystko od zera | ~8-10 min | ❌ Brak |

---

## 🎯 Kluczowe różnice DEV vs PROD

| Aspekt | Development | Production |
|--------|-------------|------------|
| **Dockerfile** | `Dockerfile.dev` | `Dockerfile.prod` |
| **Compose** | `docker-compose.dev.yml` | `docker-compose.prod.yml` |
| **Build** | Lokalnie | GitHub Actions |
| **Image source** | Build local | Pull z Docker Hub |
| **Bazy danych** | Prefiks `zzz_*` | Bez prefiksu |
| **Redis password** | `dev_password` | `prod_password` |
| **Django settings** | `nc.settings.dev` | `nc.settings.prod` |
| **Debug** | `DEBUG=True` | `DEBUG=False` |
| **Hot reload** | ✅ Tak | ❌ Nie |
| **Volumes** | Kod z hosta | Tylko dane |
| **Memory limits** | ❌ Brak | ✅ Tak |
| **Flower auth** | ❌ Bez | ✅ Basic auth |

---

## 📦 Dependencje

### requirements.txt (wspólne):
```txt
Django==5.2.4
celery==5.5.0
kombu==5.5.2
redis==5.2.1
psycopg2-binary==2.9.10
djangorestframework==3.16.0
# ...

# ML/AI - WYŁĄCZONE (zbyt długi build z PyTorch ~20min)
# sentence-transformers==3.3.1
# qdrant-client==1.12.0
# scikit-learn==1.5.2
# numpy==2.2.0
```

💡 **Uwaga**: Pakiety ML zakomentowane dla szybszego builda. 
Jeśli potrzebujesz ML, możesz:
1. Odkomentować pakiety
2. Lub stworzyć osobny kontener ML (zobacz ML_CONTAINER.md)

---

## 🔍 Diagnostyka

### Sprawdź używany Dockerfile:
```bash
# Dev
grep "dockerfile:" docker-compose.dev.yml
# Powinno: dockerfile: Dockerfile.dev

# Prod
grep "image:" docker-compose.prod.yml
# Powinno: image: ${DOCKERHUB_USERNAME}/django-app:latest
```

### Sprawdź settings Django:
```bash
# Dev
docker-compose -f docker-compose.dev.yml exec web python -c "from django.conf import settings; print(settings.SETTINGS_MODULE)"
# Powinno: nc.settings.dev

# Prod
docker-compose -f docker-compose.prod.yml exec web python -c "from django.conf import settings; print(settings.SETTINGS_MODULE)"
# Powinno: nc.settings.prod
```

---

## 🚦 Quick Start

### Dla developera (lokalne środowisko):
```bash
# 1. Skopiuj env
cp .env.sample .env.dev

# 2. Build i uruchom
docker-compose -f docker-compose.dev.yml up -d

# 3. Sprawdź
docker-compose -f docker-compose.dev.yml ps
```

### Dla CI/CD (GitHub Actions):
```bash
# 1. Push na main
git push origin main

# 2. GitHub Actions automatycznie:
#    - Zbuduje Dockerfile.prod
#    - Wypchnie na Docker Hub
#    - Zdeployuje na Digital Ocean z docker-compose.prod.yml
```

---

## 📚 Powiązane dokumenty

- [BUILD_OPTIMIZATION.md](BUILD_OPTIMIZATION.md) - Optymalizacja buildów
- [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md) - Zero-downtime deploy
- [GITHUB_AUTO_DEPLOY.md](GITHUB_AUTO_DEPLOY.md) - GitHub Actions setup

---

## ✅ Checklist migracji

Jeśli migrujesz ze starej struktury:

- [x] ~~Dockerfile~~ → **Dockerfile.dev** + **Dockerfile.prod**
- [x] ~~Dockerfile.simple~~ → Usunięty
- [x] ~~docker-compose.yml~~ → **docker-compose.dev.yml** + **docker-compose.prod.yml**
- [x] GitHub Actions używa **Dockerfile.prod**
- [x] Deploy script używa **docker-compose.prod.yml**
- [x] Dokumentacja zaktualizowana

---

**Ostatnia aktualizacja**: 2025-10-07

