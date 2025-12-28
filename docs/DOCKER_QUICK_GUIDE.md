# 🚀 Docker - Szybki przewodnik

## 📋 Wybór środowiska

```bash
# 🛠️ DEVELOPMENT (twój komputer)
docker-compose -f docker-compose.dev.yml [command]

# 🚀 PRODUCTION (blue-green)
docker-compose -f docker-compose.blue-green.yml [command]
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
- 🌐 Django: http://localhost:8080
- 🌺 Flower (Celery monitoring): http://localhost:5555
- 📊 Django Admin: http://localhost:8080/admin
- 📖 API Docs: http://localhost:8000/api/schema/swagger-ui/

---

## 🚀 Production (blue-green)

### Deploy (przez GitHub Actions)
```bash
# Push na main - automatyczny deploy
git add .
git commit -m "feat: nowa funkcja"
git push origin main

# GitHub Actions automatycznie:
# 1. Wypchnie zmiany na serwer
# 2. Uruchomi blue-green deployment
```

### Ręczny deploy na serwerze
```bash
# SSH na serwer
ssh user@your-server

# Przejdź do katalogu
cd /srv/app

# Pull zmian z repo
git pull origin main

# Deploy (blue-green, zero-downtime)
./scripts/deploy/deploy-blue-green.sh deploy

# Sprawdź status
docker-compose -f docker-compose.blue-green.yml ps

# Logi
docker-compose -f docker-compose.blue-green.yml logs -f web-blue
docker-compose -f docker-compose.blue-green.yml logs -f web-green
```

### Monitoring produkcji
```bash
# Status wszystkich kontenerów
docker-compose -f docker-compose.blue-green.yml ps

# Użycie zasobów
docker stats

# Logi ostatnie 100 linii
docker logs nc-web-blue --tail 100
docker logs nc-web-green --tail 100

# Logi na żywo (kilka serwisów)
docker-compose -f docker-compose.blue-green.yml logs -f celery-import celery-default
```

### Rollback (awaria)
```bash
# Rollback
./scripts/deploy/deploy-blue-green.sh rollback
```

---

## 🔍 Diagnostyka

### Sprawdź używane pliki
```bash
# Dev
ls -la | grep -E "Dockerfile.dev|docker-compose.dev.yml"

# Prod
ls -la | grep -E "Dockerfile.prod|docker-compose.blue-green.yml|nginx-blue-green.conf"
```

### Sprawdź settings Django
```bash
# Dev
docker-compose -f docker-compose.dev.yml exec web python -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])"
# Powinno: zzz_default

# Prod (sprawdź na aktywnym kontenerze: nc-web-blue lub nc-web-green)
docker exec nc-web-blue python -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])"
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
| **Start** | `docker-compose -f docker-compose.dev.yml up -d` | `./scripts/deploy/deploy-blue-green.sh deploy` |
| **Logs** | `docker-compose -f docker-compose.dev.yml logs -f` | `docker-compose -f docker-compose.blue-green.yml logs -f` |
| **Shell** | `docker-compose -f docker-compose.dev.yml exec web bash` | `docker exec -it nc-web-blue bash` |
| **Stop** | `docker-compose -f docker-compose.dev.yml down` | `docker-compose -f docker-compose.blue-green.yml stop web-blue web-green nginx-router celery-default celery-import celery-beat flower` |

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
alias dc-prod='docker-compose -f docker-compose.blue-green.yml'
alias dc-prod-logs='docker-compose -f docker-compose.blue-green.yml logs -f'
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

