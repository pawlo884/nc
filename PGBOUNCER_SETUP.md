# PgBouncer Setup - Connection Pooler dla PostgreSQL

## Problem
- `CONN_MAX_AGE = 0` zamyka połączenia natychmiast → wolne
- Każde zapytanie = nowe połączenie TCP do PostgreSQL
- PostgreSQL musi obsłużyć setki połączeń → overhead

## Rozwiązanie: PgBouncer
**Connection Pooler** między Django a PostgreSQL:
- Django otwiera/zamyka połączenia szybko (do PgBouncer)
- PgBouncer utrzymuje pool połączeń do PostgreSQL
- PostgreSQL widzi tylko 25-50 połączeń zamiast setek

## Architektura

```
┌─────────┐                 ┌──────────────┐                ┌────────────┐
│  Django │ ──(setki)──→   │  PgBouncer   │ ──(25-50)──→  │ PostgreSQL │
│  Celery │  połączeń       │ Connection   │  połączeń      │            │
│  API    │  CONN_MAX_AGE=0 │    Pooler    │  utrzymywane   │            │
└─────────┘                 └──────────────┘                └────────────┘
```

## Instalacja

### 1. Uruchom PgBouncer
```bash
docker-compose -f docker-compose.pgbouncer.yml up -d
```

### 2. Skonfiguruj hasła w pgbouncer.ini

**WAŻNE:** Przed uruchomieniem edytuj `docker/pgbouncer/pgbouncer.ini` i zamień `password=prod_password` na prawdziwe hasła:

```bash
# Edytuj docker/pgbouncer/pgbouncer.ini
nano docker/pgbouncer/pgbouncer.ini

# Zmień:
zzz_default = host=postgres port=5432 dbname=zzz_default user=nc password=TWOJE_HASLO_DEFAULT pool_size=25
zzz_matterhorn1 = host=postgres port=5432 dbname=zzz_matterhorn1 user=nc password=TWOJE_HASLO_MATTERHORN1 pool_size=25
zzz_MPD = host=postgres port=5432 dbname=zzz_MPD user=nc password=TWOJE_HASLO_MPD pool_size=25
```

### 3. Zmień `.env.prod` - Podłącz Django do PgBouncer
```bash
# Zamiast:
# DEFAULT_DB_HOST=postgres
# DEFAULT_DB_PORT=5432

# Użyj:
DEFAULT_DB_HOST=pgbouncer
DEFAULT_DB_PORT=5432

# To samo dla pozostałych:
MATTERHORN1_DB_HOST=pgbouncer
MPD_DB_HOST=pgbouncer
```

### 3. Restart aplikacji
```bash
docker-compose -f docker-compose.prod.yml restart web celery-default celery-import celery-beat
```

## Konfiguracja

### Wszystkie bazy danych Django
PgBouncer jest skonfigurowany dla **wszystkich 3 baz** używanych przez Django:
```yaml
DATABASE_URLS: |
  zzz_default=postgres://user:pass@postgres:5432/zzz_default
  zzz_matterhorn1=postgres://user:pass@postgres:5432/zzz_matterhorn1
  zzz_MPD=postgres://user:pass@postgres:5432/zzz_MPD
```

Django routing (`default`, `matterhorn1`, `MPD`) działa przez PgBouncer.

### Pool Mode: `transaction`
- Kompatybilny z `CONN_MAX_AGE = 0`
- Połączenie zwalniane po każdej transakcji
- Idealny dla Django ORM

### Pool Size: 25 połączeń per baza
```
DEFAULT_POOL_SIZE: 25       # Normalne połączenia
RESERVE_POOL_SIZE: 10       # Dodatkowe w szczycie
MAX_DB_CONNECTIONS: 100     # Max do pojedynczej bazy
```

### Client Connections: 1000
```
MAX_CLIENT_CONN: 1000       # Django może otworzyć max 1000
```

### Timeouts
```
SERVER_CONNECT_TIMEOUT: 15  # 15s na połączenie do PostgreSQL
QUERY_WAIT_TIMEOUT: 120     # 2 min czekania na wolne połączenie
SERVER_IDLE_TIMEOUT: 600    # 10 min idle
```

## Monitoring

### Status PgBouncer
```bash
# Połącz się do PgBouncer admin console
docker exec -it nc-pgbouncer psql -p 5432 -U nc pgbouncer

# Pokaż statistyki
SHOW STATS;

# Pokaż połączenia
SHOW POOLS;

# Pokaż klientów
SHOW CLIENTS;

# Pokaż serwery
SHOW SERVERS;

# Config
SHOW CONFIG;
```

### Przykładowy output SHOW POOLS:
```
 database  | user | cl_active | cl_waiting | sv_active | sv_idle | sv_used
-----------+------+-----------+------------+-----------+---------+---------
 zzz_...   | nc   |         5 |          0 |         3 |      22 |       0
 matterhorn1| nc  |        12 |          0 |         8 |      17 |       0
```

**Interpretacja:**
- `cl_active`: aktywne połączenia od Django
- `sv_active`: aktywne połączenia do PostgreSQL
- `sv_idle`: wolne połączenia w pool (reużywane)

## Korzyści

### ⚡ Szybkość
- **10-50x szybsze** nawiązywanie połączeń
- Django łączy się do PgBouncer (localhost) zamiast PostgreSQL
- PgBouncer reużywa istniejących połączeń

### 📊 Mniej obciążenia PostgreSQL
- PostgreSQL widzi 25-50 połączeń zamiast setek
- Mniej overhead na fork/spawn procesów
- Mniej zużycia RAM

### 🛡️ Ochrona przed przeciążeniem
- Django nie może otworzyć więcej niż MAX_CLIENT_CONN
- PostgreSQL chroniony przed connection exhaustion

### ✅ Kompatybilność z CONN_MAX_AGE=0
- Transaction pooling mode idealny dla Django
- Każde request = nowe połączenie (do PgBouncer)
- PgBouncer utrzymuje pool do PostgreSQL

## Troubleshooting

### "No more connections allowed"
```bash
# Zwiększ MAX_CLIENT_CONN w docker-compose.pgbouncer.yml
MAX_CLIENT_CONN: 2000
```

### "Query wait timeout"
```bash
# Zwiększ pool size
DEFAULT_POOL_SIZE: 50
RESERVE_POOL_SIZE: 20
```

### Logi PgBouncer
```bash
docker logs nc-pgbouncer -f
```

## Rollback

Jeśli coś nie działa, przywróć bezpośrednie połączenie:

```bash
# .env.prod
DEFAULT_DB_HOST=postgres
DEFAULT_DB_PORT=5432

# Restart
docker-compose -f docker-compose.prod.yml restart web celery-default celery-import celery-beat
```

## Monitoring w produkcji

### Metryki do zbierania:
- `cl_active` - aktywne połączenia od Django
- `cl_waiting` - czekające połączenia (powinno być 0)
- `sv_active` - użyte połączenia do PostgreSQL
- `sv_idle` - wolne połączenia w pool
- `avg_query_time` - średni czas zapytania

### Alert gdy:
- `cl_waiting > 10` → Za mały pool size
- `sv_active == DEFAULT_POOL_SIZE` → Pool pełny, zwiększ
- `avg_query_time > 1000ms` → Wolne zapytania SQL

## Następne kroki

Po wdrożeniu PgBouncer:
1. ✅ Monitoruj `SHOW STATS` przez 24h
2. ✅ Sprawdź `cl_waiting` (powinno być 0)
3. ✅ Dostosuj `DEFAULT_POOL_SIZE` jeśli potrzeba
4. ✅ Porównaj czasy response przed/po

**CONN_MAX_AGE=0 + PgBouncer = 💪 Szybko + Bezpiecznie**

