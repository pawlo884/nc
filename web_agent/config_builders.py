"""
Funkcje pomocnicze do budowania konfiguracji zadań dla nowego agenta
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from matterhorn1.models import Brand, Category


def build_products_url(
    base_url: str,
    brand_id: Optional[int] = None,
    category_id: Optional[int] = None,
    active: Optional[bool] = None,
    is_mapped: Optional[bool] = None
) -> str:
    """
    Buduje URL do listy produktów z filtrami
    
    Args:
        base_url: Bazowy URL aplikacji
        brand_id: ID marki (opcjonalne)
        category_id: ID kategorii (opcjonalne)
        active: Filtrowanie po aktywności (opcjonalne)
        is_mapped: Filtrowanie po mapowaniu (opcjonalne)
        
    Returns:
        URL z parametrami filtrowania
    """
    url = f'{base_url}/admin/matterhorn1/product/'
    params = []
    
    if brand_id:
        params.append(f'brand__id__exact={brand_id}')
    if category_id:
        params.append(f'category__id__exact={category_id}')
    if active is not None:
        params.append(f'active__exact={1 if active else 0}')
    if is_mapped is not None:
        params.append(f'is_mapped__exact={1 if is_mapped else 0}')
    
    if params:
        url += '?' + '&'.join(params)
    
    return url


def get_all_brands(using: str = 'matterhorn1') -> list:
    """
    Pobiera wszystkie marki z bazy danych
    
    Args:
        using: Nazwa bazy danych
        
    Returns:
        Lista słowników z id i name marki
    """
    brands = Brand.objects.using(using).all().values('id', 'name')
    return [{'id': b['id'], 'name': b['name']} for b in brands]


def get_all_categories(using: str = 'matterhorn1') -> list:
    """
    Pobiera wszystkie kategorie z bazy danych
    
    Args:
        using: Nazwa bazy danych
        
    Returns:
        Lista słowników z id i name kategorii
    """
    categories = Category.objects.using(using).all().values('id', 'name')
    return [{'id': c['id'], 'name': c['name']} for c in categories]


def create_django_admin_task_config(
    base_url: str = 'http://localhost:8000',
    username: Optional[str] = None,
    password: Optional[str] = None,
    env_file: str = '.env.dev',
    config_type: str = 'products'
) -> Dict[str, Any]:
    """
    Tworzy konfigurację zadania dla Django Admin (logowanie)
    
    Args:
        base_url: URL aplikacji Django
        username: Nazwa użytkownika (jeśli None, pobiera z .env)
        password: Hasło (jeśli None, pobiera z .env)
        env_file: Ścieżka do pliku .env
        config_type: Typ konfiguracji ('login' lub 'products')
        
    Returns:
        Słownik z konfiguracją zadania
    """
    # Pobierz dane logowania
    if username is None or password is None:
        load_dotenv(env_file)
        username = username or os.getenv('DJANGO_ADMIN_USERNAME', '')
        password = password or os.getenv('DJANGO_ADMIN_PASSWORD', '')
    
    name = 'Django Admin - Login' if config_type == 'login' else 'Django Admin - Products'
    
    return {
        'name': name,
        'task_type': 'automation',
        'url': base_url,
        'config': {
            'headless': False,
            'base_url': base_url,
            'username': username,
            'password': password,
            'config_type': config_type
        }
    }


def create_brand_task_config(
    brand_id: int,
    brand_name: str,
    base_url: str = 'http://localhost:8000',
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    active: Optional[bool] = True,
    is_mapped: Optional[bool] = False,
    username: Optional[str] = None,
    password: Optional[str] = None,
    env_file: str = '.env.dev',
    max_products: int = 10
) -> Dict[str, Any]:
    """
    Tworzy konfigurację zadania dla marki z mapowaniem produktów
    
    Args:
        brand_id: ID marki
        brand_name: Nazwa marki
        base_url: URL aplikacji Django
        category_id: ID kategorii (opcjonalne)
        category_name: Nazwa kategorii (opcjonalne)
        active: Filtrowanie po aktywności
        is_mapped: Filtrowanie po mapowaniu
        username: Nazwa użytkownika (jeśli None, pobiera z .env)
        password: Hasło (jeśli None, pobiera z .env)
        env_file: Ścieżka do pliku .env
        max_products: Maksymalna liczba produktów do przetworzenia
        
    Returns:
        Słownik z konfiguracją zadania
    """
    # Pobierz dane logowania
    if username is None or password is None:
        load_dotenv(env_file)
        username = username or os.getenv('DJANGO_ADMIN_USERNAME', '')
        password = password or os.getenv('DJANGO_ADMIN_PASSWORD', '')
    
    # Zbuduj URL produktów
    products_url = build_products_url(
        base_url=base_url,
        brand_id=brand_id,
        category_id=category_id,
        active=active,
        is_mapped=is_mapped
    )
    
    # Utwórz nazwę zadania
    name_parts = [f'Django Admin - Produkty marki: {brand_name}']
    if category_name:
        name_parts.append(f'Kategoria: {category_name}')
    if active is not None:
        name_parts.append(f'Aktywne: {"Tak" if active else "Nie"}')
    if is_mapped is not None:
        name_parts.append(f'Zmapowane: {"Tak" if is_mapped else "Nie"}')
    
    return {
        'name': ' | '.join(name_parts),
        'task_type': 'automation',
        'url': base_url,
        'config': {
            'headless': False,
            'base_url': base_url,
            'products_url': products_url,
            'username': username,
            'password': password,
            'brand_id': brand_id,
            'brand_name': brand_name,
            'category_id': category_id,
            'category_name': category_name,
            'active': active,
            'is_mapped': is_mapped,
            'max_products': max_products
        },
        'brand_id': brand_id,
        'brand_name': brand_name
    }

