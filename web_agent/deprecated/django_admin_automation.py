"""
Moduł z gotowymi konfiguracjami automatyzacji dla Django Admin
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv


def load_env_vars(env_file: str = '.env.dev') -> Dict[str, str]:
    """Ładuje zmienne środowiskowe z pliku .env.dev"""
    load_dotenv(env_file)
    return {
        'username': os.getenv('DJANGO_ADMIN_USERNAME', ''),
        'password': os.getenv('DJANGO_ADMIN_PASSWORD', ''),
    }


def get_django_admin_login_config(
    base_url: str = 'http://localhost:8080',
    username: str = None,
    password: str = None,
    env_file: str = '.env.dev'
) -> Dict[str, Any]:
    """
    Zwraca konfigurację zadania automatyzacji dla logowania do Django Admin

    Args:
        base_url: URL aplikacji Django (domyślnie: http://localhost:8000)
        username: Nazwa użytkownika (jeśli None, pobiera z .env.dev)
        password: Hasło (jeśli None, pobiera z .env.dev)
        env_file: Ścieżka do pliku .env (domyślnie: .env.dev)

    Returns:
        Słownik z konfiguracją zadania automatyzacji
    """
    # Jeśli nie podano danych, pobierz z .env.dev
    if username is None or password is None:
        env_vars = load_env_vars(env_file)
        username = username or env_vars['username']
        password = password or env_vars['password']

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
            {
                'type': 'screenshot',
                'full_page': False,
                'path': None
            }
        ]
    }

    return config


def get_django_admin_products_config(
    base_url: str = 'http://localhost:8080',
    username: str = None,
    password: str = None,
    env_file: str = '.env.dev'
) -> Dict[str, Any]:
    """
    Zwraca konfigurację zadania automatyzacji dla logowania i przejścia do Produktów

    Args:
        base_url: URL aplikacji Django (domyślnie: http://localhost:8000)
        username: Nazwa użytkownika (jeśli None, pobiera z .env.dev)
        password: Hasło (jeśli None, pobiera z .env.dev)
        env_file: Ścieżka do pliku .env (domyślnie: .env.dev)

    Returns:
        Słownik z konfiguracją zadania automatyzacji
    """
    config = get_django_admin_login_config(
        base_url, username, password, env_file)

    # Dodaj akcje do przejścia do Produktów
    config['actions'].extend([
        {
            'type': 'wait_for',
            'selector': 'a[href*="/admin/matterhorn1/product"]',
            'timeout': 10000
        },
        {
            'type': 'click',
            'selector': 'a[href*="/admin/matterhorn1/product/"]',
            'timeout': 10000
        },
        {
            'type': 'wait_for',
            'selector': 'table thead, .changelist-search',
            'timeout': 15000
        },
        {
            'type': 'screenshot',
            'full_page': True,
            'path': None
        },
        {
            'type': 'evaluate',
            'expression': '({ title: document.title, url: window.location.href, rowCount: document.querySelectorAll("table tbody tr").length })'
        }
    ])

    return config


def create_automation_task_config(config_type: str = 'products', **kwargs) -> Dict[str, Any]:
    """
    Tworzy konfigurację zadania automatyzacji na podstawie typu

    Args:
        config_type: Typ konfiguracji ('login' lub 'products')
        **kwargs: Dodatkowe argumenty przekazywane do funkcji konfiguracyjnej

    Returns:
        Słownik z konfiguracją zadania dla WebAgentTask
    """
    if config_type == 'login':
        config = get_django_admin_login_config(**kwargs)
    elif config_type == 'products':
        config = get_django_admin_products_config(**kwargs)
    else:
        raise ValueError(
            f'Nieznany typ konfiguracji: {config_type}. Dostępne: login, products')

    return {
        'name': f'Django Admin - {config_type.capitalize()}',
        'task_type': 'automation',
        'url': kwargs.get('base_url', 'http://localhost:8080'),
        'config': config
    }
