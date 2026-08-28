# Redis → PostgreSQL: cache, blokady i result backend

Branch `feat/redis-to-postgres`. Cel: ograniczyć Redis do **jednej** roli —
brokera Celery — a resztę przenieść na PostgreSQL (który i tak jest krytyczny).

## Co się zmieniło

| Obszar | Przed | Po |
|---|---|---|
| Cache Django (`CACHES`) | Redis (db 1) — `django-redis` (prod) / `RedisCache` (base) | `DatabaseCache`, tabela `nc_cache_table` w bazie `default` |
| Blokady tasków tabu/mada | `cache.add(key, id, ttl)` na Redisie | PostgreSQL advisory locks — `core.pg_locks.advisory_lock` |
| Blokada importu matterhorn1 | `cache.add` na Redisie | `cache.add` **na DatabaseCache** (bez zmian w kodzie — spleciona z rekoncyliacją DB) |
| Celery result backend | Redis (db 0) | `django-db` (`django-celery-results`, tabele w `default`) |
| `django-redis` | w requirements | usunięte (biblioteka `redis` zostaje — kombu jej używa do brokera) |
| Redis `maxmemory-policy` | `allkeys-lru` | `noeviction` (broker nie może gubić zadań przez LRU) |

Redis nadal jest wymagany jako **broker** (`CELERY_BROKER_URL=redis://...`).

## Dlaczego broker został na Redisie

Celery nie ma produkcyjnego wsparcia dla PostgreSQL jako brokera (transport
SQLAlchemy w kombu jest nieutrzymywany). Pełne zejście z Redisa wymagałoby wymiany
Celery na kolejkę natywnie postgresową (`procrastinate`, `django-tasks`) — to
osobny projekt. Dodatkowo prod łączy się z Postgresem po sieci/tunelu, więc ruch
brokera (stały polling) obciążałby to łącze.

## `core.pg_locks.advisory_lock`

```python
from core.pg_locks import advisory_lock

with advisory_lock('tabu:sync_tabu_stock') as acquired:
    if not acquired:
        return {'status': 'skipped', 'reason': 'already_running'}
    ...  # sekcja krytyczna
```

* Blokada trzymana na **dedykowanym połączeniu** do bazy (nie ORM-owym), żeby
  recykling połączeń Django w trakcie taska jej nie zerwał.
* Zwalnia się automatycznie przy wyjściu z bloku **oraz** gdy proces padnie
  (zniknie połączenie) — **nie ma "martwych" locków**, nie trzeba watchdoga.
* `tabu.tasks.watchdog_tabu_stock_lock` jest teraz no-opem (PeriodicTask z migracji
  `tabu/0013` zostaje dla kompatybilności; kolejny release może go usunąć).

## Deployment — WYMAGANY krok

Tabelę cache tworzy `manage.py createcachetable` (idempotentne). Dodane do:

* `deployments/k8s/nc-prod/migrate-job.yaml`, `deployments/k8s/nc-test/migrate-job.yaml`
* `scripts/migrations/run-migrations-dev.sh`
* `docker-compose/docker-compose.dev.yml` (komenda serwisu `web`)
* `scripts/deploy/run-migrations.sh` (blue-green — **deprecated**)

Kolejność przy wdrożeniu tej zmiany:

1. `migrate` (django_celery_results już zmigrowane — bez nowych migracji aplikacyjnych)
2. `python manage.py createcachetable --database=default`
3. rollout nowych obrazów (worker/web/beat)
4. Redis: cache w db 1 można wyczyścić (`redis-cli -n 1 flushdb` — jeśli komenda nie jest zablokowana) — nie jest to konieczne, klucze i tak wygasną / nie będą używane.

`CELERY_RESULT_BACKEND` w env musi być **puste** (k8s: `""`). `core/settings` ustawia
`django-db` na stałe; niepusta wartość w env nadpisałaby to (Celery `__autoset`).

## Odwrót (rollback)

1. Przywróć poprzednie `CACHES` / `CELERY_RESULT_BACKEND` w `core/settings`.
2. `pip install django-redis==7.0.0` (wróć wpis w requirements).
3. Przywróć `CELERY_RESULT_BACKEND=redis://...` w compose/k8s.
4. Kod tasków tabu/mada: wersja z `cache.add` (git revert commita z advisory locks).

Tabela `nc_cache_table` i wiersze w `django_celery_results_taskresult` mogą zostać —
są nieszkodliwe.

## Uwagi

* **Flower**: monitoring live (eventy przez broker) działa bez zmian. Historyczny
  podgląd wyników jest słabszy przy backendzie DB — dlatego `CELERY_RESULT_EXTENDED=True`
  (nazwa taska/argumenty w `django_celery_results` → admin Django).
* **Czyszczenie starych wyników**: task `celery.backend_cleanup` (dodawany
  automatycznie przez beat) usuwa wyniki starsze niż `result_expires` (domyślnie 1 dzień).
* **Throttling DRF** korzysta z `CACHES['default']` — po zmianie działa na PostgreSQL.
