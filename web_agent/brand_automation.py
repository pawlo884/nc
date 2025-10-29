"""
Moduł do automatyzacji dla każdej marki (brand) osobno
"""
import os
from typing import Dict, Any, List
from dotenv import load_dotenv


def get_all_brands(using='matterhorn1') -> List[Dict[str, Any]]:
    """
    Pobiera wszystkie marki z bazy danych

    Args:
        using: Nazwa bazy danych (domyślnie: 'matterhorn1')

    Returns:
        Lista słowników z danymi mark: [{'id': 1, 'name': 'Axami'}, ...]
    """
    from matterhorn1.models import Brand

    brands = Brand.objects.using(using).all().values(
        'id', 'name').order_by('name')
    return list(brands)


def get_all_categories(using='matterhorn1') -> List[Dict[str, Any]]:
    """
    Pobiera wszystkie kategorie z bazy danych

    Args:
        using: Nazwa bazy danych (domyślnie: 'matterhorn1')

    Returns:
        Lista słowników z danymi kategorii: [{'id': 1, 'name': 'Biustonosze'}, ...]
    """
    from matterhorn1.models import Category

    categories = Category.objects.using(using).all().values(
        'id', 'name', 'path').order_by('name')
    return list(categories)


def build_filter_url(
    base_url: str,
    brand_id: int = None,
    category_id: int = None,
    active: bool = None
) -> str:
    """
    Buduje URL z filtrami dla Django Admin

    Args:
        base_url: Bazowy URL
        brand_id: ID marki (opcjonalne)
        category_id: ID kategorii (opcjonalne)
        active: Status aktywności (True/False, opcjonalne)

    Returns:
        URL z parametrami filtrowania
    """
    from urllib.parse import urlencode

    params = {}

    if brand_id is not None:
        params['brand__id__exact'] = brand_id

    if category_id is not None:
        params['category__id__exact'] = category_id

    if active is not None:
        # Django Admin używa 1/0 dla BooleanField
        params['active__exact'] = 1 if active else 0

    products_url = f'{base_url}/admin/matterhorn1/product/'
    if params:
        products_url += '?' + urlencode(params)

    return products_url


def get_brand_filter_config(
    brand_id: int,
    brand_name: str = None,
    category_id: int = None,
    category_name: str = None,
    active: bool = None,
    base_url: str = 'http://localhost:8000',
    username: str = None,
    password: str = None,
    env_file: str = '.env.dev'
) -> Dict[str, Any]:
    """
    Zwraca konfigurację zadania automatyzacji dla konkretnej marki z opcjonalnymi filtrami

    Args:
        brand_id: ID marki w bazie danych
        brand_name: Nazwa marki (do wyświetlenia, opcjonalne)
        category_id: ID kategorii (opcjonalne)
        category_name: Nazwa kategorii (do wyświetlenia, opcjonalne)
        active: Filtrowanie po statusie aktywności (True/False, opcjonalne)
        base_url: URL aplikacji Django
        username: Nazwa użytkownika (opcjonalne)
        password: Hasło (opcjonalne)
        env_file: Ścieżka do pliku .env

    Returns:
        Słownik z konfiguracją zadania automatyzacji
    """
    # Pobierz dane logowania jeśli nie podano
    if username is None or password is None:
        load_dotenv(env_file)
        username = username or os.getenv('DJANGO_ADMIN_USERNAME', '')
        password = password or os.getenv('DJANGO_ADMIN_PASSWORD', '')

    # URL do produktów z filtrami
    products_url = build_filter_url(
        base_url=base_url,
        brand_id=brand_id,
        category_id=category_id,
        active=active
    )

    config = {
        'headless': True,
        'actions': [
            {
                'type': 'navigate',
                'url': base_url,
                'wait_until': 'load',
                'timeout': 30000
            },
            {
                'type': 'wait_for',
                'selector': 'a[href="/admin/"]',
                'timeout': 10000
            },
            {
                'type': 'click',
                'selector': 'a[href="/admin/"]',
                'timeout': 10000
            },
            {
                'type': 'wait_for',
                'selector': 'input[name="username"]',
                'timeout': 10000
            },
            {
                'type': 'fill',
                'selector': 'input[name="username"]',
                'value': username,
                'timeout': 10000
            },
            {
                'type': 'fill',
                'selector': 'input[name="password"]',
                'value': password,
                'timeout': 10000
            },
            {
                'type': 'click',
                'selector': 'input[type="submit"], button[type="submit"]',
                'timeout': 10000
            },
            {
                'type': 'wait_for',
                'selector': '.user-tools, a[href*="/admin/matterhorn1"]',
                'timeout': 15000
            },
            # Przejdź bezpośrednio do produktów z filtrem po brand
            {
                'type': 'navigate',
                'url': products_url,
                'wait_until': 'load',
                'timeout': 30000
            },
            {
                'type': 'wait_for',
                'selector': 'table thead, .changelist-search',
                'timeout': 15000
            },
            # Sprawdź czy filtry są aktywne
            {
                'type': 'wait_for',
                'selector': 'table thead, .changelist-filters',
                'timeout': 10000
            },
            # Pobierz dane o produktach i filtrach
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const url = new URL(window.location.href);
                    return {
                        title: document.title,
                        url: window.location.href,
                        rowCount: document.querySelectorAll("table tbody tr").length,
                        filters: {
                            brandId: url.searchParams.get('brand__id__exact') || null,
                            categoryId: url.searchParams.get('category__id__exact') || null,
                            active: url.searchParams.get('active__exact') || null
                        },
                        brandFilterText: document.querySelector('select[name="brand__id__exact"]')?.options[document.querySelector('select[name="brand__id__exact"]')?.selectedIndex]?.text || '',
                        categoryFilterText: document.querySelector('select[name="category__id__exact"]')?.options[document.querySelector('select[name="category__id__exact"]')?.selectedIndex]?.text || '',
                        activeFilterText: document.querySelector('select[name="active__exact"]')?.options[document.querySelector('select[name="active__exact"]')?.selectedIndex]?.text || '',
                        currentPage: document.querySelector('.paginator .this-page')?.textContent || '1',
                        totalResults: document.querySelector('.paginator')?.textContent.match(/\\d+\\s+(?:produkt|product)/i)?.[0] || ''
                    };
                })()'''
            },
            # Screenshot
            {
                'type': 'screenshot',
                'full_page': True,
                'path': None
            },
            # Pobierz listę produktów (pierwsza strona)
            {
                'type': 'evaluate',
                'expression': '''(() => {
                    const rows = Array.from(document.querySelectorAll("table tbody tr"));
                    return rows.slice(0, 20).map(row => {
                        const cells = row.querySelectorAll("td");
                        return {
                            product_uid: cells[1]?.textContent.trim() || '',
                            name: cells[2]?.textContent.trim() || '',
                            brand: cells[3]?.textContent.trim() || ''
                        };
                    });
                })()'''
            }
        ]
    }

    return config


def create_brand_automation_task_config(
    brand_id: int,
    brand_name: str,
    category_id: int = None,
    category_name: str = None,
    active: bool = None,
    base_url: str = 'http://localhost:8000',
    username: str = None,
    password: str = None,
    env_file: str = '.env.dev'
) -> Dict[str, Any]:
    """
    Tworzy pełną konfigurację zadania automatyzacji dla marki z opcjonalnymi filtrami

    Args:
        brand_id: ID marki
        brand_name: Nazwa marki
        category_id: ID kategorii (opcjonalne)
        category_name: Nazwa kategorii (opcjonalne)
        active: Filtrowanie po statusie aktywności (True/False, opcjonalne)
        base_url: URL aplikacji
        username: Nazwa użytkownika (opcjonalne)
        password: Hasło (opcjonalne)
        env_file: Ścieżka do pliku .env

    Returns:
        Słownik z konfiguracją zadania dla WebAgentTask
    """
    config = get_brand_filter_config(
        brand_id=brand_id,
        brand_name=brand_name,
        category_id=category_id,
        category_name=category_name,
        active=active,
        base_url=base_url,
        username=username,
        password=password,
        env_file=env_file
    )

    # Utwórz nazwę zadania z informacją o filtrach
    name_parts = [f'Django Admin - Produkty marki: {brand_name}']
    if category_name:
        name_parts.append(f'Kategoria: {category_name}')
    if active is not None:
        name_parts.append(f'Aktywne: {"Tak" if active else "Nie"}')

    return {
        'name': ' | '.join(name_parts),
        'task_type': 'automation',
        'url': base_url,
        'config': config
    }


def create_automation_tasks_for_all_brands(
    base_url: str = 'http://localhost:8000',
    username: str = None,
    password: str = None,
    env_file: str = '.env.dev',
    using: str = 'matterhorn1'
) -> List[Dict[str, Any]]:
    """
    Tworzy konfiguracje zadań automatyzacji dla wszystkich marek

    Args:
        base_url: URL aplikacji Django
        username: Nazwa użytkownika (opcjonalne)
        password: Hasło (opcjonalne)
        env_file: Ścieżka do pliku .env
        using: Nazwa bazy danych

    Returns:
        Lista słowników z konfiguracjami zadań
    """
    brands = get_all_brands(using=using)
    tasks = []

    for brand in brands:
        task_config = create_brand_automation_task_config(
            brand_id=brand['id'],
            brand_name=brand['name'],
            base_url=base_url,
            username=username,
            password=password,
            env_file=env_file
        )
        tasks.append(task_config)

    return tasks
