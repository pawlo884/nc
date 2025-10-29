# Web Agent - Aplikacja Django

Aplikacja Web Agent umożliwia zarządzanie zadaniami automatyzacji web, monitorowania i zbierania danych.

## Funkcjonalności

### Modele

- **WebAgentTask** - zadania agenta web (scraping, monitorowanie, zbieranie danych, automatyzacja)
- **WebAgentLog** - logi zadań agenta web
- **WebAgentConfig** - konfiguracje agenta web

### Typy zadań

1. **scrape** - Scraping stron internetowych (obsługuje HTTP i Playwright dla dynamicznych stron)
2. **monitor** - Monitorowanie dostępności stron
3. **data_collection** - Zbieranie danych z wielu źródeł
4. **automation** - Automatyzacja działań web (obsługuje HTTP i akcje przeglądarki)

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

#### Utworzenie zadania scrapingu (HTTP - dla prostych stron)
```json
{
    "name": "Scraping przykładu",
    "task_type": "scrape",
    "url": "https://example.com",
    "config": {
        "timeout": 30,
        "headers": {
            "User-Agent": "WebAgent/1.0"
        },
        "use_browser": false
    }
}
```

#### Utworzenie zadania scrapingu z przeglądarką (dla stron z JavaScript/SPA)
```json
{
    "name": "Scraping strony z JavaScript",
    "task_type": "scrape",
    "url": "https://example.com",
    "config": {
        "use_browser": true,
        "headless": true,
        "wait_for_selector": ".content-loaded"
    }
}
```

**Opcje konfiguracji dla scrapingu z przeglądarką:**
- `use_browser` (boolean): Użyj Playwright zamiast HTTP (domyślnie: false)
- `headless` (boolean): Tryb headless przeglądarki (domyślnie: true)
- `wait_for_selector` (string): CSS selektor - czekaj aż element się pojawi przed scrapowaniem

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

#### Utworzenie zadania automatyzacji (HTTP)
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

#### Utworzenie zadania automatyzacji z przeglądarką
```json
{
    "name": "Automatyzacja z przeglądarką",
    "task_type": "automation",
    "config": {
        "headless": true,
        "actions": [
            {
                "type": "navigate",
                "url": "https://example.com",
                "wait_until": "load",
                "timeout": 30000
            },
            {
                "type": "wait_for",
                "selector": ".main-content",
                "timeout": 10000
            },
            {
                "type": "click",
                "selector": "button#submit",
                "timeout": 10000
            },
            {
                "type": "fill",
                "selector": "input#email",
                "value": "user@example.com",
                "timeout": 10000
            },
            {
                "type": "fill_form",
                "fields": [
                    {
                        "selector": "input#name",
                        "value": "Jan Kowalski"
                    },
                    {
                        "selector": "input#phone",
                        "value": "123456789"
                    }
                ],
                "timeout": 10000
            },
            {
                "type": "screenshot",
                "full_page": true,
                "path": "/tmp/screenshot.png"
            },
            {
                "type": "get_text",
                "selector": ".result-message"
            },
            {
                "type": "evaluate",
                "expression": "document.title"
            }
        ]
    }
}
```

**Dostępne akcje przeglądarki:**
- `navigate` - Nawigacja do URL
  - `url` (string, wymagane): URL do otwarcia
  - `wait_until` (string): 'load', 'domcontentloaded', 'networkidle' (domyślnie: 'load')
  - `timeout` (number): Timeout w ms (domyślnie: 30000)
- `click` - Kliknięcie w element
  - `selector` (string, wymagane): CSS selektor elementu
  - `timeout` (number): Timeout w ms (domyślnie: 10000)
- `fill` - Wypełnienie pola formularza
  - `selector` (string, wymagane): CSS selektor pola
  - `value` (string, wymagane): Wartość do wpisania
  - `timeout` (number): Timeout w ms (domyślnie: 10000)
- `fill_form` - Wypełnienie formularza z wieloma polami
  - `fields` (array, wymagane): Lista pól `[{selector: "...", value: "..."}]`
  - `timeout` (number): Timeout w ms (domyślnie: 10000)
- `wait_for` - Oczekiwanie na element lub tekst
  - `selector` (string, opcjonalne): CSS selektor
  - `text` (string, opcjonalne): Tekst do oczekiwania
  - `timeout` (number): Timeout w ms (domyślnie: 10000)
- `screenshot` - Zrzut ekranu
  - `full_page` (boolean): Czy zrzut całej strony (domyślnie: false)
  - `path` (string, opcjonalne): Ścieżka do zapisania (jeśli brak, zwraca base64)
- `evaluate` - Wykonanie JavaScript
  - `expression` (string, wymagane): Kod JavaScript do wykonania
- `get_text` - Pobranie tekstu z elementu
  - `selector` (string, wymagane): CSS selektor elementu

## Instalacja

1. Zainstaluj zależności (Playwright jest już w requirements.txt):
```bash
pip install -r requirements.txt
# Zainstaluj przeglądarki Playwright (jednorazowo)
playwright install chromium
```

2. Dodaj aplikację do `INSTALLED_APPS` w settings.py:
```python
INSTALLED_APPS = [
    # ...
    'web_agent',
    # ...
]
```

3. Dodaj URL patterns do głównego urls.py:
```python
urlpatterns = [
    # ...
    path('web_agent/', include('web_agent.urls')),
    # ...
]
```

4. Uruchom migracje:
```bash
python manage.py makemigrations web_agent
python manage.py migrate --database=zzz_web_agent --settings=nc.settings.dev
```

## Testy

Uruchom testy:
```bash
python manage.py test web_agent --settings=nc.settings.dev
```

## Automatyzacja Django Admin

Web Agent zawiera gotowe konfiguracje dla automatyzacji Django Admin.

### Gotowe konfiguracje

#### Utworzenie zadania przez komendę Django

Najłatwiejszy sposób - użyj komendy Django:

```bash
# Utworzenie zadania dla logowania i przejścia do Produktów
python manage.py create_django_admin_task --type products --base-url http://localhost:8000 --settings=nc.settings.dev

# Tylko logowanie (bez przechodzenia do Produktów)
python manage.py create_django_admin_task --type login --base-url http://localhost:8000 --settings=nc.settings.dev
```

**Dane logowania** są automatycznie pobierane z `.env.dev`:
- `DJANGO_ADMIN_USERNAME`
- `DJANGO_ADMIN_PASSWORD`

#### Utworzenie zadania programatycznie

```python
from web_agent.models import WebAgentTask
from web_agent.django_admin_automation import create_automation_task_config
from web_agent.tasks import start_web_agent_task

# Utwórz konfigurację
task_config = create_automation_task_config(
    config_type='products',  # 'login' lub 'products'
    base_url='http://localhost:8000',
    username='Web_Agent',  # opcjonalne, jeśli None pobiera z .env.dev
    password='haslo'  # opcjonalne, jeśli None pobiera z .env.dev
)

# Utwórz zadanie
task = WebAgentTask.objects.create(
    name=task_config['name'],
    task_type=task_config['task_type'],
    url=task_config['url'],
    config=task_config['config'],
    status='pending'
)

# Uruchom zadanie
start_web_agent_task.delay(task.id)
```

#### Utworzenie zadania przez API

```bash
POST /api/web_agent/api/tasks/
Content-Type: application/json

{
  "name": "Django Admin - Products",
  "task_type": "automation",
  "url": "http://localhost:8000",
  "config": {
    "headless": true,
    "actions": [
      {
        "type": "navigate",
        "url": "http://localhost:8000",
        "wait_until": "load",
        "timeout": 30000
      },
      {
        "type": "click",
        "selector": "a[href=\"/admin/\"]",
        "timeout": 10000
      },
      {
        "type": "fill",
        "selector": "input[name=\"username\"]",
        "value": "Web_Agent",
        "timeout": 10000
      },
      {
        "type": "fill",
        "selector": "input[name=\"password\"]",
        "value": "Staropolanka2000",
        "timeout": 10000
      },
      {
        "type": "click",
        "selector": "input[type=\"submit\"]",
        "timeout": 10000
      },
      {
        "type": "click",
        "selector": "a[href*=\"/admin/matterhorn1/product/\"]",
        "timeout": 10000
      }
    ]
  }
}
```

### Funkcje pomocnicze

```python
from web_agent.django_admin_automation import (
    get_django_admin_login_config,
    get_django_admin_products_config,
    create_automation_task_config
)

# Konfiguracja tylko logowania
login_config = get_django_admin_login_config(
    base_url='http://localhost:8000',
    username='Web_Agent',  # opcjonalne
    password='haslo'  # opcjonalne
)

# Konfiguracja logowania + produkty
products_config = get_django_admin_products_config(
    base_url='http://localhost:8000'
)
```

## Automatyzacja dla każdej marki (Brand)

Web Agent może tworzyć osobne zadania automatyzacji dla każdej marki, filtrując produkty po brand.

### Utworzenie zadań dla wszystkich marek

Najłatwiejszy sposób - użyj komendy Django:

```bash
# Utworzenie zadań dla WSZYSTKICH marek
python manage.py create_brand_tasks --base-url http://localhost:8000 --settings=nc.settings.dev

# Tryb testowy (dry-run) - tylko pokazuje co zostanie utworzone
python manage.py create_brand_tasks --dry-run --settings=nc.settings.dev
```

### Utworzenie zadania dla konkretnej marki

```bash
# Przez ID marki
python manage.py create_brand_tasks --brand-id 4 --base-url http://localhost:8000 --settings=nc.settings.dev

# Przez nazwę marki
python manage.py create_brand_tasks --brand-name "Axami" --base-url http://localhost:8000 --settings=nc.settings.dev

# Z filtrem kategorii
python manage.py create_brand_tasks --brand-name "Axami" --category-name "Biustonosze" --settings=nc.settings.dev

# Z filtrem aktywności (tylko aktywne produkty)
python manage.py create_brand_tasks --brand-name "Axami" --active true --settings=nc.settings.dev

# Z wszystkimi filtrami
python manage.py create_brand_tasks --brand-name "Axami" --category-id 5 --active true --settings=nc.settings.dev
```

### Utworzenie programatycznie

```python
from web_agent.models import WebAgentTask
from web_agent.brand_automation import (
    get_all_brands,
    create_brand_automation_task_config
)

# Pobierz wszystkie marki
brands = get_all_brands(using='matterhorn1')

# Utwórz zadania dla każdej marki z filtrem aktywnych produktów
for brand in brands:
    task_config = create_brand_automation_task_config(
        brand_id=brand['id'],
        brand_name=brand['name'],
        category_id=5,  # opcjonalne - ID kategorii
        active=True,  # opcjonalne - tylko aktywne produkty
        base_url='http://localhost:8000'
    )
    
    task = WebAgentTask.objects.create(
        name=task_config['name'],
        task_type=task_config['task_type'],
        url=task_config['url'],
        config=task_config['config'],
        status='pending'
    )
    
    print(f"Utworzono zadanie dla marki: {brand['name']}")
```

### Co robi zadanie dla marki?

Każde zadanie automatycznie:

1. **Loguje się** do Django Admin (dane z `.env.dev`)
2. **Przechodzi** do sekcji Produkty
3. **Filtruje** produkty według:
   - **Brand** (marka) - wymagane
   - **Category** (kategoria) - opcjonalne
   - **Active** (status aktywności: True/False) - opcjonalne
4. **Pobiera dane** o produktach (pierwsza strona, max 20 produktów)
5. **Robie screenshot** przefiltrowanej listy
6. **Zwraca statystyki**: liczba produktów, informacje o wszystkich filtrach

### Dostępne filtry

- **`--brand-id` / `--brand-name`** (wymagane): Filtrowanie po marce
- **`--category-id` / `--category-name`** (opcjonalne): Filtrowanie po kategorii
- **`--active`** (opcjonalne): 
  - `true` / `1` / `yes` - tylko aktywne produkty
  - `false` / `0` / `no` - tylko nieaktywne produkty
  - jeśli nie podano - wszystkie produkty (aktywne i nieaktywne)

### Przykładowy wynik zadania

```json
{
  "total_actions": 12,
  "browser_actions": 12,
  "results": [
    {
      "action": "navigate",
      "result": {"url": "http://localhost:8000", "success": true},
      "success": true
    },
    {
      "action": "click",
      "result": {"selector": "a[href=\"/admin/\"]", "success": true},
      "success": true
    },
    {
      "action": "fill",
      "result": {"selector": "input[name=\"username\"]", "success": true},
      "success": true
    },
    {
      "action": "evaluate",
                    "result": {
                        "rowCount": 15,
                        "filters": {
                            "brandId": "4",
                            "categoryId": "5",
                            "active": "1"
                        },
                        "url": "http://localhost:8000/admin/matterhorn1/product/?brand__id__exact=4&category__id__exact=5&active__exact=1"
                    },
      "success": true
    },
    {
      "action": "evaluate",
      "result": [
        {"product_uid": "11031", "name": "Biustonosz...", "brand": "Axami"},
        ...
      ],
      "success": true
    }
  ]
}
```

### Przykłady użycia przez API

```bash
# Utworzenie zadania dla marki "Axami"
POST /api/web_agent/api/tasks/
Content-Type: application/json

{
  "name": "Django Admin - Produkty marki: Axami",
  "task_type": "automation",
  "url": "http://localhost:8000",
  "config": {
    "headless": true,
    "actions": [
      {
        "type": "navigate",
        "url": "http://localhost:8000/admin/matterhorn1/product/?brand__id__exact=4",
        "wait_until": "load",
        "timeout": 30000
      },
      ...
    ]
  }
}
```

## Dokumentacja API

Dokumentacja API jest dostępna przez drf-spectacular:
- Swagger UI: `/api/schema/swagger-ui/`
- ReDoc: `/api/schema/redoc/`
