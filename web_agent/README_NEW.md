# Nowy Agent Web - Dokumentacja

## Architektura

Nowy agent został zaprojektowany z czystą architekturą i separacją odpowiedzialności:

```
web_agent/
├── core/                    # Podstawowe klasy i interfejsy
│   ├── browser.py          # Klasa Browser - zarządzanie Playwright
│   ├── action.py           # Klasa Action - reprezentacja akcji
│   └── workflow.py         # Klasa Workflow - orkiestracja akcji
├── workflows/              # Konkretne implementacje workflow
│   ├── django_admin.py     # Workflow dla Django Admin
│   └── product_mapping.py  # Workflow dla mapowania produktów
├── agent.py                # Główna klasa Agent
├── tasks.py                # Integracja z Celery
└── deprecated/             # Stara wersja (referencja)
```

## Użycie

### Podstawowe użycie

```python
from web_agent.agent import Agent

# Utwórz agenta
agent = Agent(headless=False)

# Wykonaj mapowanie produktów
result = await agent.execute_django_admin_product_mapping(
    base_url='http://localhost:8000',
    products_url='http://localhost:8000/admin/matterhorn1/product/?brand__id__exact=28&category__id__exact=15',
    max_products=10
)

# Zatrzymaj agenta
await agent.stop()
```

### Użycie z Celery

```python
from web_agent.agent import run_agent_sync

# Synchroniczna funkcja dla Celery
result = run_agent_sync(
    base_url='http://localhost:8000',
    products_url='http://localhost:8000/admin/matterhorn1/product/?brand__id__exact=28',
    headless=False,
    max_products=10
)
```

## Workflow

### Django Admin Login

```python
from web_agent.workflows import DjangoAdminWorkflow

workflow = DjangoAdminWorkflow.create_login_workflow(
    base_url='http://localhost:8000',
    username='admin',
    password='password'
)
```

### Product Mapping

```python
from web_agent.workflows import ProductMappingWorkflow

workflow = ProductMappingWorkflow.create_product_loop_workflow(
    max_products=10,
    changelist_url='http://localhost:8000/admin/matterhorn1/product/'
)
```

## Zalety nowej architektury

1. **Czysta separacja odpowiedzialności** - każda klasa ma jedną odpowiedzialność
2. **Łatwe testowanie** - każdy komponent można testować osobno
3. **Rozszerzalność** - łatwo dodać nowe workflow
4. **Czytelność** - kod jest prostszy i bardziej zrozumiały
5. **Type safety** - używa typów i dataclass
6. **Logowanie** - szczegółowe logi na każdym poziomie

## Migracja ze starego agenta

Stary agent jest w folderze `deprecated/` i może być używany jako referencja.
Nowy agent jest kompatybilny z istniejącymi zadaniami w bazie danych.

