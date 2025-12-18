# 🚀 Quick Start - NC Project

## Pierwsze uruchomienie (5 minut)

### 1️⃣ Sklonuj projekt (już masz ✅)
```powershell
cd C:\Users\pawlo\Desktop\kodowanie\nc_project
```

### 2️⃣ Skonfiguruj środowisko
```powershell
# Skopiuj przykładowy .env
# (plik .env.dev już istnieje - sprawdź konfigurację)
```

### 3️⃣ Zbuduj obrazy Docker (z cache!)
```powershell
# Windows
.\scripts\build\build-fast.ps1

# Linux/Mac
./scripts/build/build-fast.sh
```
⏱️ Pierwszy build: ~5-10 minut (pobieranie pakietów)

### 4️⃣ Uruchom kontenery
```powershell
docker-compose -f docker-compose.dev.yml up -d
```
⏱️ Start: ~30 sekund

### 5️⃣ Sprawdź status
```powershell
docker-compose -f docker-compose.dev.yml ps
```

### 6️⃣ Otwórz aplikację
```
🌐 Django Admin: http://localhost:8000/admin/
🌸 Flower (Celery): http://localhost:5555
📊 API Docs: http://localhost:8000/api/schema/swagger-ui/
```

---

## Codzienne użycie

### Uruchomienie aplikacji
```powershell
docker-compose -f docker-compose.dev.yml up -d
```

### Zatrzymanie aplikacji
```powershell
docker-compose -f docker-compose.dev.yml down
```

### Zobacz logi
```powershell
# Wszystkie serwisy
docker-compose -f docker-compose.dev.yml logs -f

# Tylko web
docker-compose -f docker-compose.dev.yml logs -f web

# Tylko celery
docker-compose -f docker-compose.dev.yml logs -f celery-default
```

### Restart po zmianie kodu
```powershell
# Opcja 1: Rebuild (jeśli zmieniłeś requirements.txt)
.\scripts\build\build-fast.ps1
docker-compose -f docker-compose.dev.yml up -d --force-recreate

# Opcja 2: Restart (jeśli tylko kod)
docker-compose -f docker-compose.dev.yml restart web
```

---

## Deployment do Production

### Blue-Green Deploy (prod)
```bash
export ENVIRONMENT=prod
./scripts/deploy/deploy-blue-green.sh deploy
./scripts/deploy/deploy-blue-green.sh status
```

### Rollback
```powershell
# Rollback (blue-green)
./scripts/deploy/deploy-blue-green.sh rollback
```

---

## Przydatne komendy

### Docker
```powershell
# Status wszystkich kontenerów
docker-compose -f docker-compose.dev.yml ps

# Restart konkretnego serwisu
docker-compose -f docker-compose.dev.yml restart web

# Wejdź do kontenera
docker-compose -f docker-compose.dev.yml exec web bash

# Zobacz zużycie zasobów
docker stats

# Wyczyść nieużywane obrazy
docker system prune -a
```

### Django
```powershell
# Wejdź do shell Django
docker-compose -f docker-compose.dev.yml exec web python manage.py shell --settings=nc.settings.dev

# Stwórz superusera
docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser --settings=nc.settings.dev

# Migracje
docker-compose -f docker-compose.dev.yml exec web python manage.py makemigrations --settings=nc.settings.dev
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate --database=zzz_default --settings=nc.settings.dev

# Collectstatic
docker-compose -f docker-compose.dev.yml exec web python manage.py collectstatic --noinput --settings=nc.settings.dev
```

### Celery
```powershell
# Lista aktywnych tasków
docker-compose -f docker-compose.dev.yml exec celery-default celery -A nc.celery inspect active

# Lista scheduled tasków
docker-compose -f docker-compose.dev.yml exec celery-beat celery -A nc.celery inspect scheduled

# Restart celery worker
docker-compose -f docker-compose.dev.yml restart celery-default

# Purge all tasks
docker-compose -f docker-compose.dev.yml exec celery-default celery -A nc.celery purge
```

### Redis
```powershell
# Połącz się z Redis (hasło: dev_password)
docker-compose -f docker-compose.dev.yml exec redis redis-cli -a dev_password

# Sprawdź statystyki
docker-compose -f docker-compose.dev.yml exec redis redis-cli -a dev_password INFO

# Wyczyść cache
docker-compose -f docker-compose.dev.yml exec redis redis-cli -a dev_password FLUSHALL
```

---

## Troubleshooting

### Problem: Kontenery nie startują
```powershell
# Sprawdź logi
docker-compose -f docker-compose.dev.yml logs

# Sprawdź co jest używane
docker ps -a

# Zatrzymaj wszystko i zacznij od nowa
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d
```

### Problem: Port już zajęty (8000, 5555, 6379)
```powershell
# Windows - sprawdź co używa portu
netstat -ano | findstr :8000

# Zabij proces (zmień PID)
taskkill /PID <PID> /F

# Lub zmień port w docker-compose.dev.yml
# ports:
#   - "8001:8000"  # zmień 8000 na 8001
```

### Problem: Brak miejsca na dysku
```powershell
# Sprawdź zużycie
docker system df

# Wyczyść nieużywane zasoby
docker system prune -a

# Wyczyść volumes (UWAGA: usuwa dane!)
docker volume prune
```

### Problem: Build trwa zbyt długo
```powershell
# Sprawdź czy BuildKit jest włączony
$env:DOCKER_BUILDKIT
# Powinno zwrócić: 1

# Włącz BuildKit
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"

# Rebuild
.\scripts\build\build-fast.ps1
```

### Problem: Baza danych nie działa
```powershell
# Sprawdź logi PostgreSQL na hoście
# Połączenie jest do hosta, nie kontenera!

# Sprawdź connection string w .env.dev
# DB_HOST=host.docker.internal  # lub IP hosta
```

---

## Monitoring

### Flower (Celery)
```
http://localhost:5555
```
- Zobacz aktywne taski
- Monitor workers
- Task history
- Task routing

### Docker Stats
```powershell
docker stats
```
- CPU usage
- Memory usage
- Network I/O
- Disk I/O

### Logi
```powershell
# Tail logs
docker-compose -f docker-compose.dev.yml logs -f

# Ostatnie 100 linii
docker-compose -f docker-compose.dev.yml logs --tail=100

# Logi z timestamp
docker-compose -f docker-compose.dev.yml logs -f -t
```

---

## Performance Tips

### 1. Używaj BuildKit cache
```powershell
.\scripts\build\build-fast.ps1  # Nie docker-compose build!
```

### 2. Zmniejsz liczbę rebuilds
- Zmieniaj tylko kod? Nie rebuild, tylko restart
- Dodałeś pakiet? Rebuild z cache będzie szybki

### 3. Limit memory dla Celery
```yaml
# W docker-compose.dev.yml
deploy:
  resources:
    limits:
      memory: 256M
```

### 4. Używaj Redis do cache
```python
# settings/dev.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://:dev_password@redis:6379/1',
    }
}
```

---

## Następne kroki

1. 📚 Przeczytaj dokumentację:
   - [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md)
   - [BUILD_OPTIMIZATION.md](BUILD_OPTIMIZATION.md)
   - [DEPLOYMENT_SCRIPTS.md](DEPLOYMENT_SCRIPTS.md)

2. 🧪 Przetestuj deployment:
   ```bash
   ./scripts/deploy/deploy-blue-green.sh status
   ```

3. 🔙 Przetestuj rollback:
   ```powershell
   ./scripts/deploy/deploy-blue-green.sh rollback
   ```

4. 📊 Sprawdź monitoring:
   - Flower: http://localhost:5555
   - Django Admin: http://localhost:8000/admin/

---

## Szybka pomoc

```powershell
# Start wszystkiego
docker-compose -f docker-compose.dev.yml up -d

# Stop wszystkiego
docker-compose -f docker-compose.dev.yml down

# Rebuild i restart
.\scripts\build\build-fast.ps1
docker-compose -f docker-compose.dev.yml up -d --force-recreate

# Logi
docker-compose -f docker-compose.dev.yml logs -f

# Rollback
./scripts/deploy/deploy-blue-green.sh rollback

# Cleanup
docker system prune -a
```

---

**Happy coding! 🚀**

Potrzebujesz pomocy? Sprawdź [README.md](../README.md) lub [DEPLOYMENT_SCRIPTS.md](DEPLOYMENT_SCRIPTS.md)

