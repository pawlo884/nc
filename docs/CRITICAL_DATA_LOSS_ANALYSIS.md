# 🚨 KRYTYCZNA ANALIZA - Utrata danych PostgreSQL

## Problem

PostgreSQL został **ODTWORZONY DZISIAJ** (2025-12-03 10:18:58) podczas deploy!

## Co się stało

### Timeline:
1. **2025-11-27 - 2025-12-02**: Dane były importowane normalnie
2. **2025-12-03 10:18**: Deploy z `--force-recreate`
3. **PostgreSQL został odtworzony** (kontener + prawdopodobnie baza)
4. **7 dni danych znikło** (27.11 - 02.12)

### Mechanizm utraty:

```bash
# W deploy-vps.yml linia 76:
docker-compose -f docker-compose.blue-green.yml up -d --force-recreate
```

**`--force-recreate` odtwarza WSZYSTKIE kontenery**, włączając PostgreSQL!

## Możliwe scenariusze

### Scenariusz 1: Volume został usunięty
```bash
# Ktoś mógł przypadkowo wykonać:
docker volume rm nc_postgres_data
# lub
rm -rf /mnt/data2tb/docker/volumes/nc_postgres_data
```

### Scenariusz 2: Volume był pusty
- Volume istniał ale był pusty
- PostgreSQL utworzył nową bazę od zera
- Wszystkie dane znikły

### Scenariusz 3: Permissions problem
- PostgreSQL nie mógł odczytać starego volume (uprawnienia)
- Utworzył nową bazę w innym miejscu

### Scenariusz 4: Initdb.d nadpisał bazę
- Skrypty w `deployments/docker/postgres/initdb.d/` nadpisały dane
- **ALE:** katalog jest pusty, więc to NIE TO

## Weryfikacja

### Krok 1: Sprawdź volume na serwerze
```bash
ssh pawel@VPS_IP
cd /home/pawel/apps/nc
bash check_postgres_volume.sh
```

### Krok 2: Sprawdź logi PostgreSQL
```bash
docker logs nc-postgres-1 --tail 100
```

Szukaj:
- `initdb: database system was initialized`
- `PostgreSQL init process complete`
- Błędów uprawnień

### Krok 3: Sprawdź czy są backupy
```bash
ls -lah /mnt/data2tb/backups/postgres/ 2>/dev/null
ls -lah /home/pawel/backups/ 2>/dev/null
```

## Rozwiązanie

### Natychmiastowe (jeśli są backupy):
```bash
# 1. Zatrzymaj PostgreSQL
docker stop nc-postgres-1

# 2. Przywróć backup
docker exec -i nc-postgres-1 psql -U postgres -d matterhorn1 < backup.sql

# 3. Uruchom PostgreSQL
docker start nc-postgres-1
```

### Jeśli NIE MA backupów:
```bash
# Odzyskaj dane z API (27.11 - 02.12)
docker exec -it nc-web-1 python manage.py shell --settings=nc.settings.prod
```

```python
from matterhorn1.models import ApiSyncLog
from datetime import datetime
import pytz

# Utwórz rekord z datą 26 listopada
ApiSyncLog.objects.using('matterhorn1').create(
    sync_type='items_import',
    status='completed',
    started_at=datetime(2025, 11, 26, 0, 0, 0, tzinfo=pytz.UTC),
    completed_at=datetime(2025, 11, 26, 0, 0, 1, tzinfo=pytz.UTC),
    records_processed=0,
    records_created=0,
    records_updated=0,
    records_errors=0
)

# Uruchom import - pobierze dane od 26.11
from matterhorn1.tasks import full_import_and_update
result = full_import_and_update()
print(result)
```

## Zabezpieczenie na przyszłość

### 1. NIE używaj `--force-recreate` dla PostgreSQL

**PRZED** (deploy-vps.yml linia 75-76):
```bash
docker-compose -f docker-compose.blue-green.yml build --no-cache
docker-compose -f docker-compose.blue-green.yml up -d --force-recreate  # ❌ KASUJE WSZYSTKO
```

**PO**:
```bash
# Zatrzymaj tylko kontenery aplikacji (BEZ postgres i redis)
docker-compose -f docker-compose.blue-green.yml stop web-blue web-green celery-default celery-import celery-beat flower nginx-router

# Rebuild tylko aplikacji
docker-compose -f docker-compose.blue-green.yml build --no-cache web-blue web-green celery-default celery-import celery-beat flower

# Uruchom (postgres i redis zostają NIETKNIĘTE)
docker-compose -f docker-compose.blue-green.yml up -d
```

### 2. Automatyczny backup przed deploy

Dodaj do `.github/workflows/deploy-vps.yml` PRZED migracjami:

```yaml
- name: Backup database before deploy
  run: |
    echo "💾 Tworzenie backup bazy danych..."
    ssh ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} << 'EOF'
      cd /home/pawel/apps/nc
      
      # Utwórz katalog na backupy
      mkdir -p /home/pawel/backups/postgres
      
      # Backup wszystkich baz
      docker exec nc-postgres-1 pg_dumpall -U postgres > /home/pawel/backups/postgres/backup_$(date +%Y%m%d_%H%M%S).sql
      
      # Zachowaj tylko ostatnie 7 backupów
      cd /home/pawel/backups/postgres
      ls -t backup_*.sql | tail -n +8 | xargs -r rm
      
      echo "✅ Backup utworzony"
    EOF
```

### 3. Monitoring volume

Dodaj do periodic tasks:

```python
@shared_task
def check_postgres_volume():
    """Sprawdza czy volume PostgreSQL jest OK"""
    import subprocess
    
    result = subprocess.run(
        ['docker', 'exec', 'nc-postgres-1', 'psql', '-U', 'postgres', '-c', 'SELECT COUNT(*) FROM pg_database'],
        capture_output=True
    )
    
    if result.returncode != 0:
        logger.error("⚠️ PostgreSQL volume problem!")
        # Wyślij alert
```

## Podsumowanie

**Przyczyna:** `--force-recreate` odtworzył PostgreSQL, prawdopodobnie z pustym volume  
**Skutek:** Utrata 7 dni danych (27.11 - 02.12)  
**Rozwiązanie:** 
1. Sprawdź czy są backupy
2. Jeśli nie - odzyskaj z API
3. Napraw deploy workflow (NIE używaj --force-recreate dla postgres)
4. Dodaj automatyczne backupy

## Następne kroki

1. ✅ Uruchom `check_postgres_volume.sh` na serwerze
2. ⏳ Sprawdź logi PostgreSQL
3. ⏳ Szukaj backupów
4. ⏳ Odzyskaj dane (backup lub API)
5. ✅ Napraw deploy workflow (już zrobione w poprzednich commitach)

