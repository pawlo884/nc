# ✅ Naprawa - PostgreSQL chroniony przed odtwarzaniem podczas deploy

## Problem który był

```bash
# STARE (NIEBEZPIECZNE):
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d --force-recreate  # ❌ ODTWARZA WSZYSTKO!
```

**`--force-recreate`** odtwarzał **WSZYSTKIE** kontenery, włączając:
- ❌ PostgreSQL (baza danych)
- ❌ Redis (cache)

**Skutek:** Jeśli volume był pusty/uszkodzony → **UTRATA DANYCH**

## Rozwiązanie

```bash
# NOWE (BEZPIECZNE):

# 1. Zatrzymaj tylko kontenery aplikacji
docker-compose -f docker-compose.prod.yml stop web celery-default celery-import celery-beat flower nginx static-init

# 2. Rebuild tylko aplikacji
docker-compose -f docker-compose.prod.yml build --no-cache web celery-default celery-import celery-beat flower static-init

# 3. Uruchom wszystko (postgres i redis pozostają NIETKNIĘTE)
docker-compose -f docker-compose.prod.yml up -d
```

## Co się zmienia podczas deploy

### Kontenery które SĄ odtwarzane:
- ✅ `web` - aplikacja Django
- ✅ `celery-default` - worker Celery
- ✅ `celery-import` - worker importu
- ✅ `celery-beat` - scheduler
- ✅ `flower` - monitoring Celery
- ✅ `nginx` - reverse proxy
- ✅ `static-init` - inicjalizacja plików statycznych

### Kontenery które POZOSTAJĄ nietknięte:
- 🛡️ `postgres` - **NIGDY nie jest odtwarzany**
- 🛡️ `redis` - **NIGDY nie jest odtwarzany**

## Jak to działa

### 1. `docker-compose stop` (tylko aplikacja)
```bash
docker-compose stop web celery-default celery-import celery-beat flower nginx static-init
```
- Zatrzymuje tylko kontenery aplikacji
- **Postgres i Redis działają dalej**
- Brak przestoju bazy danych

### 2. `docker-compose build` (tylko aplikacja)
```bash
docker-compose build --no-cache web celery-default celery-import celery-beat flower static-init
```
- Przebudowuje tylko obrazy aplikacji
- Postgres i Redis nie są buildowane (używają gotowych obrazów)

### 3. `docker-compose up -d` (wszystko)
```bash
docker-compose up -d
```
- Uruchamia WSZYSTKIE kontenery
- Postgres i Redis: jeśli działają → **pozostają nietknięte**
- Aplikacja: nowe kontenery z nowym kodem

## Bezpieczeństwo

### Co jest chronione:
- ✅ **Volume PostgreSQL** - `/mnt/data2tb/docker/volumes/nc_postgres_data`
- ✅ **Volume Redis** - `/mnt/data2tb/docker/volumes/nc_redis_data`
- ✅ **Dane pozostają** nawet podczas deploy
- ✅ **Brak ryzyka** utraty danych

### Co się dzieje jeśli:

**Postgres lub Redis są zatrzymane:**
```bash
docker-compose up -d  # Uruchomi je ponownie
```
- Kontener zostanie utworzony
- **Volume zostanie zamontowany**
- Dane są BEZPIECZNE

**Postgres lub Redis działają:**
```bash
docker-compose up -d  # Zostawi je w spokoju
```
- Kontenery pozostają NIETKNIĘTE
- Żadne odtwarzanie
- Zero przestoju

## Weryfikacja

### Sprawdź który kontener został utworzony kiedy:

```bash
# Na serwerze:
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
```

**Oczekiwany wynik po deploy:**
```
NAMES                    STATUS              CREATED
nc-web-1                Up 2 minutes        2025-12-03 15:30:00  ← NOWY
nc-celery-default-1     Up 2 minutes        2025-12-03 15:30:00  ← NOWY
nc-celery-import-1      Up 2 minutes        2025-12-03 15:30:00  ← NOWY
nc-postgres-1           Up 5 days           2025-11-28 10:00:00  ← STARY (nietknięty)
nc-redis-1              Up 5 days           2025-11-28 10:00:00  ← STARY (nietknięty)
```

### Sprawdź logi deploy:

```bash
# W GitHub Actions lub lokalnie:
```

Powinno pokazać:
```
🛑 Zatrzymywanie kontenerów aplikacji (postgres i redis zostają nietknięte)...
Stopping nc-web-1 ... done
Stopping nc-celery-default-1 ... done
...

🔨 Rebuilding kontenerów aplikacji...
Building web
Building celery-default
...

🚀 Uruchamianie wszystkich kontenerów (postgres i redis pozostają nietknięte)...
nc-postgres-1 is up-to-date
nc-redis-1 is up-to-date
Starting nc-web-1 ... done
...
```

**Klucz:** `is up-to-date` = kontener **NIE został odtworzony** ✅

## Podsumowanie

| Przed | Po |
|-------|-----|
| ❌ `--force-recreate` odtwarza WSZYSTKO | ✅ Odtwarza tylko aplikację |
| ❌ Postgres może być odtworzony | ✅ Postgres NIGDY nie jest odtwarzany |
| ❌ Redis może być odtworzony | ✅ Redis NIGDY nie jest odtwarzany |
| ❌ Ryzyko utraty danych | ✅ Dane są BEZPIECZNE |

## Dodatkowe zabezpieczenia (opcjonalne)

### 1. Exclude postgres i redis z rebuild

W `docker-compose.prod.yml` dodaj label:

```yaml
postgres:
  image: postgres:18-alpine
  labels:
    - "nc.protected=true"  # Oznacz jako chroniony
  # ... reszta konfiguracji
```

### 2. Automatyczny backup przed deploy

Dodaj do `.github/workflows/deploy-vps.yml` PRZED rebuild:

```yaml
- name: Backup database
  run: |
    ssh ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} << 'EOF'
      mkdir -p /home/pawel/backups
      docker exec nc-postgres-1 pg_dumpall -U postgres > /home/pawel/backups/pre_deploy_$(date +%Y%m%d_%H%M%S).sql
    EOF
```

### 3. Healthcheck przed kontynuacją

```bash
# Po restart sprawdź czy postgres działa
echo "🏥 Sprawdzanie PostgreSQL..."
docker exec nc-postgres-1 pg_isready -U postgres || exit 1
echo "✅ PostgreSQL działa poprawnie"
```

---

**Wniosek:** PostgreSQL i Redis są teraz **w pełni chronione** podczas deploy! 🛡️


