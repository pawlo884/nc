# 🚀 Docker - Szybki przewodnik

## 📋 Wybór środowiska

```bash
# 🛠️ DEVELOPMENT (twój komputer)
docker-compose -f docker-compose.dev.yml [command]

# 🚀 PRODUCTION (serwer Digital Ocean)
docker-compose -f docker-compose.prod.yml [command]
```

---

## 💻 Development (localhost)

### Start projektu
```bash
# Build (pierwszy raz lub po zmianach w Dockerfile.dev)
docker-compose -f docker-compose.dev.yml build

# Uruchom wszystko
docker-compose -f docker-compose.dev.yml up -d

# Sprawdź status
docker-compose -f docker-compose.dev.yml ps

# Logi (na żywo)
docker-compose -f docker-compose.dev.yml logs -f web
docker-compose -f docker-compose.dev.yml logs -f celery-import
```

### Praca z kontenerami
```bash
# Wejdź do kontenera
docker-compose -f docker-compose.dev.yml exec web bash

# Django shell
docker-compose -f docker-compose.dev.yml exec web python manage.py shell

# Migracje
docker-compose -f docker-compose.dev.yml exec web python manage.py makemigrations
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate --database=zzz_default

# Stop wszystkiego
docker-compose -f docker-compose.dev.yml down

# Stop + usuń volumes (UWAGA: usuwa dane!)
docker-compose -f docker-compose.dev.yml down -v
```

### Rebuild po zmianach
```bash
# Szybki rebuild (tylko kod)
docker-compose -f docker-compose.dev.yml up -d --build

# Pełny rebuild (czysty cache)
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

### Dostęp
- 🌐 Django: http://localhost:8000
- 🌺 Flower (Celery monitoring): http://localhost:5555
- 📊 Django Admin: http://localhost:8000/admin
- 📖 API Docs: http://localhost:8000/api/schema/swagger-ui/

---

## 🚀 Production (Digital Ocean)

### Deploy (przez GitHub Actions)
```bash
# Push na main - automatyczny deploy
git add .
git commit -m "feat: nowa funkcja"
git push origin main

# GitHub Actions automatycznie:
# 1. Zbuduje Dockerfile.prod
# 2. Wypchnie na Docker Hub
# 3. Zdeployuje na DO z docker-compose.prod.yml
```

### Ręczny deploy na serwerze
```bash
# SSH na serwer
ssh user@your-server

# Przejdź do katalogu
cd /srv/app

# Pull zmian z repo
git pull origin main

# Deploy (zero-downtime)
bash deploy-from-registry.sh

# Sprawdź status
docker-compose -f docker-compose.prod.yml ps

# Logi
docker-compose -f docker-compose.prod.yml logs -f web
```

### Monitoring produkcji
```bash
# Status wszystkich kontenerów
docker-compose -f docker-compose.prod.yml ps

# Użycie zasobów
docker stats

# Logi ostatnie 100 linii
docker-compose -f docker-compose.prod.yml logs --tail=100 web

# Logi na żywo (kilka serwisów)
docker-compose -f docker-compose.prod.yml logs -f web celery-import celery-default
```

### Rollback (awaria)
```bash
# Znajdź backup tag
docker images | grep django-app

# Rollback
docker tag django-app:backup-20251007-120000 django-app:current
docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## 🔍 Diagnostyka

### Sprawdź używane pliki
```bash
# Dev
ls -la | grep -E "Dockerfile.dev|docker-compose.dev.yml"

# Prod  
ls -la | grep -E "Dockerfile.prod|docker-compose.prod.yml"
```

### Sprawdź settings Django
```bash
# Dev
docker-compose -f docker-compose.dev.yml exec web python -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])"
# Powinno: zzz_default

# Prod
docker-compose -f docker-compose.prod.yml exec web python -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])"
# Powinno: default (bez zzz_)
```

### Sprawdź połączenia
```bash
# Redis
docker-compose -f docker-compose.dev.yml exec web python -c "import redis; r=redis.Redis(host='redis', port=6379, password='dev_password'); print(r.ping())"

# PostgreSQL
docker-compose -f docker-compose.dev.yml exec web python manage.py dbshell
```

---

## 🧹 Czyszczenie

### Bezpieczne (tylko stopped containers)
```bash
docker system prune

# Usuń nieużywane obrazy
docker image prune -a
```

### Uwaga - usuwa volumes!
```bash
# Usuń wszystko łącznie z danymi
docker-compose -f docker-compose.dev.yml down -v
docker system prune -a --volumes
```

---

## 📊 Porównanie komend

| Akcja | Development | Production |
|-------|-------------|------------|
| **Build** | `docker-compose -f docker-compose.dev.yml build` | GitHub Actions |
| **Start** | `docker-compose -f docker-compose.dev.yml up -d` | `bash deploy-from-registry.sh` |
| **Logs** | `docker-compose -f docker-compose.dev.yml logs -f` | `docker-compose -f docker-compose.prod.yml logs -f` |
| **Shell** | `docker-compose -f docker-compose.dev.yml exec web bash` | `docker-compose -f docker-compose.prod.yml exec web bash` |
| **Stop** | `docker-compose -f docker-compose.dev.yml down` | `docker-compose -f docker-compose.prod.yml down` |

---

## ⚡ Pro Tips

### Aliasy (dodaj do ~/.bashrc lub ~/.zshrc)
```bash
# Development
alias dc-dev='docker-compose -f docker-compose.dev.yml'
alias dc-dev-up='docker-compose -f docker-compose.dev.yml up -d'
alias dc-dev-logs='docker-compose -f docker-compose.dev.yml logs -f'
alias dc-dev-shell='docker-compose -f docker-compose.dev.yml exec web bash'

# Production
alias dc-prod='docker-compose -f docker-compose.prod.yml'
alias dc-prod-logs='docker-compose -f docker-compose.prod.yml logs -f'
```

Użycie:
```bash
dc-dev up          # Zamiast docker-compose -f docker-compose.dev.yml up -d
dc-dev-logs web    # Szybkie logi
dc-dev-shell       # Szybki shell
```

---

## 🆘 Najczęstsze problemy

### "Cannot connect to database"
```bash
# Sprawdź czy Redis działa
docker-compose -f docker-compose.dev.yml ps redis

# Restart Redis
docker-compose -f docker-compose.dev.yml restart redis
```

### "Port already in use"
```bash
# Znajdź proces na porcie 8000
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill procesu
kill -9 <PID>
```

### "Out of disk space"
```bash
# Sprawdź użycie
docker system df

# Cleanup
docker system prune -a
docker volume prune
```

---

**Więcej info**: [DOCKER_STRUCTURE.md](DOCKER_STRUCTURE.md)

