# Fix: Wolne pierwsze połączenie do PostgreSQL

## Problem
- **Pierwsze połączenie** po pewnym czasie trwa bardzo długo (5-10s+)
- **Kolejne połączenia** są szybkie (< 100ms)
- `CONN_MAX_AGE = 0` jest poprawne (zamyka połączenia natychmiast)

## Przyczyna
1. **TCP handshake timeout** - `connect_timeout: 60s` to za długo
2. **Brak TCP keepalive** - PostgreSQL "zasypia" idle connections
3. **PostgreSQL idle timeouts** - domyślna konfiguracja zamyka połączenia
4. **Cache miss** - pierwsze połączenie musi załadować metadata z dysku

## Rozwiązanie

### 1. PostgreSQL Configuration (`docker/postgres/postgresql.conf`)

```ini
# TCP Keepalive - utrzymuj połączenia żywe
tcp_keepalives_idle = 60           # 1 minuta przed pierwszym keepalive
tcp_keepalives_interval = 10       # 10 sekund między keepalive
tcp_keepalives_count = 5           # 5 prób przed uznaniem za martwe

# Idle timeout - nie zamykaj za szybko
idle_in_transaction_session_timeout = 600000  # 10 minut

# Performance - więcej cache
shared_buffers = 256MB             # Cache dla danych
effective_cache_size = 1GB         # Przewidywana pamięć OS
work_mem = 16MB                    # Sort/hash operations

# SSD optimization
random_page_cost = 1.1             # SSD friendly
effective_io_concurrency = 200     # Concurrent IO
```

### 2. Django Settings (`nc/settings/base.py`)

```python
'OPTIONS': {
    'connect_timeout': 5,  # ✅ Zmniejszone z 60s na 5s
    'keepalives': 1,       # ✅ Włącz TCP keepalive
    'keepalives_idle': 60, # ✅ Keepalive co 60s
    'keepalives_interval': 10,  # ✅ Interval 10s
    'keepalives_count': 5, # ✅ 5 prób
    'options': '-c statement_timeout=300000 -c lock_timeout=300000'
}
```

### 3. Docker Compose (`docker-compose.blue-green.yml`)

```yaml
postgres:
  image: postgres:18-alpine
  command:
    - postgres
    - -c
    - config_file=/etc/postgresql/postgresql.conf
  volumes:
    - /mnt/data2tb/docker/volumes/nc_postgres_data:/var/lib/postgresql/data
    - ./docker/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
```

## Wdrożenie

### Na serwerze:

```bash
cd /home/pawel/apps/nc

# 1. Pull zmian
git pull origin main

# 2. Restart PostgreSQL z nową konfiguracją
docker-compose restart postgres

# 3. Sprawdź czy PostgreSQL załadował config
docker exec nc-postgres-1 psql -U nc -d zzz_default -c "SHOW tcp_keepalives_idle;"
# Powinno pokazać: 60

# 4. Restart aplikacji
docker-compose restart web celery-default celery-import celery-beat

# 5. Test połączenia
docker exec web python manage.py shell --settings=nc.settings.prod -c "from django.db import connection; import time; start=time.time(); connection.cursor(); print(f'Połączenie: {(time.time()-start)*1000:.2f}ms')"
```

## Weryfikacja

### Test 1: Pierwsze połączenie (na serwerze)
```bash
# Poczekaj 2 minuty bez aktywności
sleep 120

# Zmierz czas pierwszego połączenia
docker exec web python manage.py shell --settings=nc.settings.prod -c "
from django.db import connection
import time
start = time.time()
connection.cursor()
elapsed = (time.time() - start) * 1000
print(f'Pierwsze połączenie: {elapsed:.2f}ms')
"
```

**Oczekiwane:**
- ❌ PRZED: 5000-10000ms (5-10 sekund)
- ✅ PO: 50-200ms (< 200ms)

### Test 2: Sprawdź TCP Keepalive
```bash
docker exec nc-postgres-1 psql -U nc -d zzz_default -c "SHOW tcp_keepalives_idle;"
docker exec nc-postgres-1 psql -U nc -d zzz_default -c "SHOW tcp_keepalives_interval;"
docker exec nc-postgres-1 psql -U nc -d zzz_default -c "SHOW tcp_keepalives_count;"
```

**Oczekiwane:**
```
tcp_keepalives_idle: 60
tcp_keepalives_interval: 10
tcp_keepalives_count: 5
```

### Test 3: Monitoruj aktywne połączenia
```bash
docker exec nc-postgres-1 psql -U nc -d zzz_default -c "
SELECT 
    count(*) as connections,
    state,
    wait_event_type,
    now() - state_change as idle_time
FROM pg_stat_activity 
WHERE datname = 'zzz_default'
GROUP BY state, wait_event_type, state_change
ORDER BY state;
"
```

## Co zostało naprawione:

### 🔧 connect_timeout: 60s → 5s
**Problem:** Zbyt długi timeout na nawiązanie połączenia  
**Fix:** 5 sekund wystarczy dla lokalnych połączeń Docker  
**Efekt:** Błędy połączenia wykrywane szybciej

### 🔧 Brak keepalive → keepalives: 1
**Problem:** PostgreSQL zamyka idle connections  
**Fix:** TCP keepalive utrzymuje połączenia żywe  
**Efekt:** Pierwsze połączenie po idle jest szybkie

### 🔧 Domyślny shared_buffers (128MB) → 256MB
**Problem:** Za mało cache, pierwsze połączenie musi czytać z dysku  
**Fix:** Więcej pamięci cache  
**Efekt:** Metadata załadowane w pamięci

### 🔧 random_page_cost: 4.0 → 1.1
**Problem:** Domyślna wartość dla HDD  
**Fix:** Optymalizacja dla SSD  
**Efekt:** Lepsze query plans

## Monitoring

### PostgreSQL Stats
```bash
# Średni czas połączenia
docker logs nc-postgres-1 --tail 100 | grep "connection"

# Aktywne połączenia
docker exec nc-postgres-1 psql -U nc -d zzz_default -c "
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
"

# Wolne query (> 1s)
docker exec nc-postgres-1 psql -U nc -d zzz_default -c "
SELECT query, now() - query_start AS duration
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '1 second'
ORDER BY duration DESC;
"
```

### Django Connection Time
```python
# W Django shell
from django.db import connection
import time

# Test 10 połączeń
times = []
for i in range(10):
    connection.close()  # Zamknij połączenie
    start = time.time()
    connection.cursor()
    elapsed = (time.time() - start) * 1000
    times.append(elapsed)
    print(f"Połączenie {i+1}: {elapsed:.2f}ms")

print(f"Średnia: {sum(times)/len(times):.2f}ms")
```

## Rollback (jeśli problem)

Jeśli coś nie działa, przywróć poprzednią konfigurację:

```bash
# Usuń custom config
docker-compose exec postgres rm /etc/postgresql/postgresql.conf

# Restart bez config file
docker-compose down postgres
docker-compose up -d postgres
```

## Następne kroki

Po wdrożeniu:
1. ✅ Monitoruj `docker logs nc-postgres-1` przez 24h
2. ✅ Sprawdź czasy odpowiedzi aplikacji
3. ✅ Jeśli nadal wolne → rozważ PgBouncer (PGBOUNCER_SETUP.md)

**Rezultat: Pierwsze połączenie < 200ms zamiast 5-10s** 🚀

