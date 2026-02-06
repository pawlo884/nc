# Tabu – baza danych i migracje

## Alias bazy w dev

W środowisku **development** (`core.settings.dev`) router `TabuRouter` kieruje aplikację `tabu` wyłącznie na bazę o **aliasie `zzz_tabu`** (nie `tabu`).

- **Połączenie:** host `postgres-ssh-tunnel`, port `5434` (tunel SSH), baza PostgreSQL: `zzz_tabu` (nazwa z `.env.dev`: `TABU_DB_NAME`).
- **Alias do migracji i skryptów:** w dev zawsze używaj **`zzz_tabu`**.

## Migracje

**W development (Docker):**

```bash
docker compose -f docker-compose/docker-compose.dev.yml exec web python manage.py migrate tabu --database=zzz_tabu
```

**Lokalnie (venv, z katalogu `src`):**

```bash
python manage.py migrate tabu --database=zzz_tabu --settings=core.settings.dev
```

Użycie `--database=tabu` w dev **nie** zastosuje migracji do właściwej bazy (router zezwala tylko na `zzz_tabu`).

## Tabele (po `0001_initial`)

W schemacie `public` bazy `zzz_tabu`:

- `django_migrations`
- `tabu_api_product`
- `tabu_api_variant`
- `tabu_apisynclog`
- `tabu_brand`
- `tabu_category`
- `tabu_product`
- `tabu_productimage`
- `tabu_productvariant`

## Sprawdzenie tabel w bazie

W kontenerze:

```bash
docker compose -f docker-compose/docker-compose.dev.yml exec web python manage.py shell -c "
from django.db import connections
c = connections['zzz_tabu']
with c.cursor() as cur:
    cur.execute(\"\"\"
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_catalog = current_database()
        ORDER BY table_name
    \"\"\")
    for row in cur.fetchall():
        print(row[0])
"
```

## Uwaga

Jeśli w `django_migrations` jest wpis `tabu.0001_initial`, a tabel `tabu_*` w bazie nie ma, usuń wpis i uruchom migrację ponownie (na `zzz_tabu`):

```python
# W Django shell z connections['zzz_tabu']
cur.execute("DELETE FROM django_migrations WHERE app = 'tabu' AND name = '0001_initial'")
# Potem: migrate tabu --database=zzz_tabu
```
