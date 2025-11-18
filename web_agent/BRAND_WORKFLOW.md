# Organizacja pracy per marka - Web Agent

## Przegląd

System został zorganizowany do pracy per marka, zaczynając od marki "Marko", a następnie kolejnych marek.

## Struktura

### Model WebAgentTask
- **brand_id** - ID marki w bazie danych
- **brand_name** - Nazwa marki (np. "Marko")
- **priority** - Priorytet zadania (wyższa wartość = wyższy priorytet)
- Zadania są sortowane według: `-priority`, `-created_at`

### Filtry domyślne
- **active=True** - Tylko aktywne produkty
- **is_mapped=False** - Tylko niezmapowane produkty (wymagające mapowania)

## Workflow pracy per marka

### 1. Tworzenie zadania dla marki "Marko"

```bash
python manage.py create_brand_task --brand-name "Marko" --settings=nc.settings.dev
```

Opcje:
- `--brand-name "Marko"` - Nazwa marki
- `--brand-id 123` - Alternatywnie: ID marki
- `--priority 10` - Priorytet (domyślnie: 0)
- `--active true` - Filtrowanie aktywnych (domyślnie: true)
- `--is-mapped false` - Tylko niezmapowane (domyślnie: false)

### 2. Sprawdzanie zadań dla marki

W Django Admin:
- Filtruj po `brand_name = "Marko"`
- Sortuj według `priority` (najwyższy priorytet na górze)

Przez API:
```
GET /api/web_agent/api/tasks/?brand_name=Marko
```

### 3. Uruchamianie zadania

**Przez API:**
```bash
POST /api/web_agent/api/tasks/{task_id}/start/
```

**Przez Django shell:**
```python
python manage.py shell --settings=nc.settings.dev
>>> from web_agent.tasks import start_web_agent_task
>>> start_web_agent_task.delay(task_id)
```

**Przez skrypt testowy (widoczna przeglądarka):**
```bash
python test_browser_visible.py --brand-id {brand_id} --wait 60
```

### 4. Monitorowanie postępu

**W Django Admin:**
- Lista zadań: `/admin/web_agent/webagenttask/`
- Filtruj po `brand_name` i `status`
- Sprawdzaj logi: `/admin/web_agent/webagentlog/`

**Przez API:**
```
GET /api/web_agent/api/tasks/{task_id}/
GET /api/web_agent/api/tasks/{task_id}/logs/
```

## Przykładowy workflow dla marki "Marko"

### Krok 1: Utwórz zadanie z wysokim priorytetem
```bash
python manage.py create_brand_task \
  --brand-name "Marko" \
  --priority 10 \
  --settings=nc.settings.dev
```

### Krok 2: Sprawdź utworzone zadanie
```bash
# W Django Admin lub przez API
GET /api/web_agent/api/tasks/?brand_name=Marko&status=pending
```

### Krok 3: Uruchom zadanie
```bash
# Przez API
POST /api/web_agent/api/tasks/{task_id}/start/

# Lub przez skrypt testowy (widoczna przeglądarka)
python test_browser_visible.py --brand-id {marko_brand_id} --wait 60
```

### Krok 4: Monitoruj postęp
- Sprawdzaj status w Django Admin
- Przeglądaj logi w `/admin/web_agent/webagentlog/`
- Sprawdzaj wyniki w `result` field zadania

### Krok 5: Po zakończeniu marki "Marko"
- Oznacz zadanie jako zakończone
- Przejdź do następnej marki z niższym priorytetem

## Kolejność pracy

1. **Marko** (priority: 10) - Najwyższy priorytet
2. **Następna marka** (priority: 9)
3. **Kolejna marka** (priority: 8)
4. ... itd.

## Przydatne komendy

### Lista wszystkich marek
```python
python manage.py shell --settings=nc.settings.dev
>>> from web_agent.brand_automation import get_all_brands
>>> brands = get_all_brands(using='matterhorn1')
>>> for brand in brands:
...     print(f"{brand['id']}: {brand['name']}")
```

### Sprawdź zadania dla konkretnej marki
```python
>>> from web_agent.models import WebAgentTask
>>> tasks = WebAgentTask.objects.filter(brand_name="Marko")
>>> for task in tasks:
...     print(f"{task.id}: {task.name} - {task.get_status_display()}")
```

### Utwórz zadanie dla następnej marki
```bash
python manage.py create_brand_task \
  --brand-name "NastępnaMarka" \
  --priority 9 \
  --settings=nc.settings.dev
```

## Uwagi

- Zadania są wykonywane sekwencyjnie (jeden po drugim)
- Priorytet określa kolejność wykonania
- Każde zadanie filtruje produkty: `active=True` i `is_mapped=False`
- Wyniki są zapisywane w `result` field zadania
- Logi są dostępne w `WebAgentLog` model

