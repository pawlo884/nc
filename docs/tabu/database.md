# Tabu – baza danych i migracje

## Alias bazy w dev

W środowisku **development** (`core.settings.dev`) router `TabuRouter` kieruje aplikację `tabu` wyłącznie na bazę o **aliasie `zzz_tabu`** (nie `tabu`).

- **Połączenie:** host `postgres-ssh-tunnel` (Docker) lub `localhost` (lokalnie), port `5434`.
- **Konfiguracja:** Szczegóły w [docs/LOCAL_DEV_DATABASE.md](../LOCAL_DEV_DATABASE.md) – rekomendowane: `TABU_DB_HOST=localhost` w `.env.dev` dla lokalnego uruchomienia.
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

## Produkcja

Router `TabuRouter` w prod kieruje aplikację `tabu` na alias **`tabu`** (gdy w `DATABASES` **nie** ma wpisu `zzz_tabu`).

### 1. Baza na Postgresie

Na tym samym serwerze co inne bazy NC utwórz pustą bazę o nazwie zgodnej z `TABU_DB_NAME` (np. `tabu`) i nadaj uprawnienia użytkownikowi z `TABU_DB_USER` — przykład jako superuser:

```sql
CREATE DATABASE tabu OWNER pawel;
-- ewentualnie: GRANT ALL PRIVILEGES ON DATABASE tabu TO pawel;
```

W `.env.prod` muszą być ustawione: `TABU_DB_HOST`, `TABU_DB_PORT`, `TABU_DB_NAME`, `TABU_DB_USER`, `TABU_DB_PASSWORD` oraz **`TABU_API_KEY`**, **`TABU_API_BASE_URL`**.

**Składnia pliku dla Dockera (`env_file`):** linie muszą mieć postać `NAZWA=wartość` **bez spacji wokół `=`**. Błędna linia (np. `KEY = "x"`) może spowodować **odrzucenie całego pliku** albo brak zmiennych **od tej linii w dół** — wtedy w kontenerze nie ma `TABU_API_KEY`, mimo że „jest w pliku” niżej. To samo dotyczy innych kluczy w tym samym `.env.prod` (np. `MATTERHORN_API_KEY`).

W `docker-compose/docker-compose.blue-green.yml` dla **web-blue**, **web-green** i **celery-default** są domyślne wartości interpolacji (`TABU_DB_HOST` itd.) — po `docker compose ... up -d` kontener dostanie poprawny host TCP nawet gdy wcześniej `HOST` był pusty. **Hasło** nadal musi pochodzić z `env_file` (`.env.prod`).

**`TABU_API_KEY`:** ten sam plik `.env.prod` jest montowany do **`/app/.env.prod`** w kontenerach web/celery/flower. Komendy Tabu przy starcie wywołują `load_dotenv` na tym pliku (python-dotenv), żeby wczytać klucz nawet wtedy, gdy Docker `env_file` pominął część zmiennych z powodu wcześniejszej błędnej linii w pliku.

### 2. Migracje

W kontenerze web (np. `nc-web-green`), katalog z `manage.py` to `/app`:

```bash
docker exec nc-web-green bash -lc 'cd /app && python manage.py migrate tabu --database=tabu --settings=core.settings.prod'
```

Jeśli `DJANGO_SETTINGS_MODULE` w kontenerze jest już `core.settings.prod`, można pominąć `--settings`:

```bash
docker exec nc-web-green bash -lc 'cd /app && python manage.py migrate tabu --database=tabu'
```

### 3. Weryfikacja

```bash
docker exec nc-web-green bash -lc 'cd /app && python manage.py showmigrations tabu --database=tabu --settings=core.settings.prod'
```

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
