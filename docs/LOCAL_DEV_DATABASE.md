# Połączenie z bazami danych – rozwój lokalny

## Jak to działa

- **Docker** (web, celery): łączy się przez `postgres-ssh-tunnel` (override w docker-compose).
- **Lokalnie** (manage.py na hoście): łączy się przez `localhost:5434` (port mapowany z kontenera).

Jedna konfiguracja `.env.dev` – bez ręcznej zmiany plików przy przełączaniu środowiska.

---

## Konfiguracja `.env.dev` (dla lokalnego uruchomienia)

Ustaw hosty baz na `localhost`:

```env
DEFAULT_DB_HOST=localhost
DEFAULT_DB_PORT=5434

MPD_DB_HOST=localhost
MPD_DB_PORT=5434

MATTERHORN1_DB_HOST=localhost
MATTERHORN1_DB_PORT=5434

WEB_AGENT_DB_HOST=localhost
WEB_AGENT_DB_PORT=5434

TABU_DB_HOST=localhost
TABU_DB_PORT=5434
```

**Kontenery Dockera** nadal używają `postgres-ssh-tunnel` dzięki nadpisaniu w `docker-compose.dev.yml`.

---

## Kroki do działania

1. Uruchom tunel SSH:
   ```powershell
   docker-compose -f docker-compose/docker-compose.dev.yml up -d postgres-ssh-tunnel
   ```

2. Sprawdź połączenie:
   ```powershell
   cd src
   python manage.py check_tabu_mpd_db --settings=core.settings.dev
   ```

3. Przy błędzie połączenia:
   - tunel działa: `docker ps | findstr postgres-ssh-tunnel`
   - port 5434 mapowany: w `docker-compose.dev.yml` sekcja `ports: - "127.0.0.1:5434:5434"`

---

## Alternatywa: wpis w hosts

Jeśli chcesz zostawić `postgres-ssh-tunnel` w `.env.dev`:

1. Edycja `C:\Windows\System32\drivers\etc\hosts` (jako Administrator):
   ```
   127.0.0.1 postgres-ssh-tunnel
   ```

2. Port 5434 musi być mapowany w docker-compose (domyślnie jest).

Rekomendacja: **localhost w .env.dev** – mniej konfiguracji, działa na każdej maszynie.
