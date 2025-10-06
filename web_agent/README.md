# Web Agent - Aplikacja Django

Aplikacja Web Agent umożliwia zarządzanie zadaniami automatyzacji web, monitorowania i zbierania danych.

## Funkcjonalności

### Modele

- **WebAgentTask** - zadania agenta web (scraping, monitorowanie, zbieranie danych, automatyzacja)
- **WebAgentLog** - logi zadań agenta web
- **WebAgentConfig** - konfiguracje agenta web

### Typy zadań

1. **scrape** - Scraping stron internetowych
2. **monitor** - Monitorowanie dostępności stron
3. **data_collection** - Zbieranie danych z wielu źródeł
4. **automation** - Automatyzacja działań web

### API Endpoints

#### Zadania (Tasks)
- `GET /api/tasks/` - Lista zadań
- `POST /api/tasks/` - Utwórz nowe zadanie
- `GET /api/tasks/{id}/` - Szczegóły zadania
- `PUT /api/tasks/{id}/` - Aktualizuj zadanie
- `DELETE /api/tasks/{id}/` - Usuń zadanie
- `POST /api/tasks/{id}/start/` - Uruchom zadanie
- `POST /api/tasks/{id}/stop/` - Zatrzymaj zadanie
- `POST /api/tasks/{id}/update_status/` - Aktualizuj status zadania
- `GET /api/tasks/stats/` - Statystyki zadań

#### Logi (Logs)
- `GET /api/logs/` - Lista logów
- `GET /api/logs/{id}/` - Szczegóły logu

#### Konfiguracje (Configs)
- `GET /api/configs/` - Lista konfiguracji
- `POST /api/configs/` - Utwórz nową konfigurację
- `GET /api/configs/{id}/` - Szczegóły konfiguracji
- `PUT /api/configs/{id}/` - Aktualizuj konfigurację
- `DELETE /api/configs/{id}/` - Usuń konfigurację

### Taski Celery

- **start_web_agent_task** - Uruchamia zadanie agenta web
- **stop_web_agent_task** - Zatrzymuje zadanie agenta web

### Przykłady użycia

#### Utworzenie zadania scrapingu
```json
{
    "name": "Scraping przykładu",
    "task_type": "scrape",
    "url": "https://example.com",
    "config": {
        "timeout": 30,
        "headers": {
            "User-Agent": "WebAgent/1.0"
        }
    }
}
```

#### Utworzenie zadania monitorowania
```json
{
    "name": "Monitorowanie strony",
    "task_type": "monitor",
    "url": "https://example.com",
    "config": {
        "timeout": 10
    }
}
```

#### Utworzenie zadania zbierania danych
```json
{
    "name": "Zbieranie danych",
    "task_type": "data_collection",
    "config": {
        "urls": [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com"
        ]
    }
}
```

#### Utworzenie zadania automatyzacji
```json
{
    "name": "Automatyzacja działań",
    "task_type": "automation",
    "config": {
        "actions": [
            {
                "type": "http_request",
                "method": "GET",
                "url": "https://api.example.com/data"
            },
            {
                "type": "data_processing",
                "operation": "filter",
                "filter_key": "status",
                "filter_value": "active"
            }
        ]
    }
}
```

## Instalacja

1. Dodaj aplikację do `INSTALLED_APPS` w settings.py:
```python
INSTALLED_APPS = [
    # ...
    'web_agent',
    # ...
]
```

2. Dodaj URL patterns do głównego urls.py:
```python
urlpatterns = [
    # ...
    path('web_agent/', include('web_agent.urls')),
    # ...
]
```

3. Uruchom migracje:
```bash
python manage.py makemigrations web_agent
python manage.py migrate --database=zzz_web_agent --settings=nc.settings.dev
```

## Testy

Uruchom testy:
```bash
python manage.py test web_agent --settings=nc.settings.dev
```

## Dokumentacja API

Dokumentacja API jest dostępna przez drf-spectacular:
- Swagger UI: `/api/schema/swagger-ui/`
- ReDoc: `/api/schema/redoc/`
