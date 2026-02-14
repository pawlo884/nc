"""
Komenda do testowania połączenia z API Tabu.
API Tabu używa nagłówka X-API-KEY (dokumentacja: https://b2b.tabu.com.pl/api/v1).

Użycie:
  python manage.py test_tabu_connection --settings=core.settings.dev
  python manage.py test_tabu_connection --api-key=YOUR_KEY --settings=core.settings.dev
  python manage.py test_tabu_connection --path=products --settings=core.settings.dev
"""
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Testuje połączenie z API Tabu (X-API-KEY, domyślny URL: b2b.tabu.com.pl/api/v1).'
    # Tylko test połączenia HTTP – nie wymaga poprawnych modeli ani bazy.
    # W Django 5 requires_system_checks musi być listą/krotką tagów lub pustą listą,
    # a nie bool. Pusta lista oznacza brak uruchamiania system checks.
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-url',
            type=str,
            default=None,
            help='URL bazowy API (domyślnie: https://b2b.tabu.com.pl/api/v1)',
        )
        parser.add_argument(
            '--api-key',
            type=str,
            default=None,
            help='Klucz API (domyślnie: TABU_API_KEY z .env)',
        )
        parser.add_argument(
            '--path',
            type=str,
            default='products',
            help='Zasób do wywołania (np. products, products/categories, users/me). Domyślnie: products.',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=15,
            help='Timeout żądania w sekundach (domyślnie 15).',
        )

    def handle(self, *args, **options):
        base_url = (options.get('base_url') or getattr(settings, 'TABU_API_BASE_URL', '') or '').strip().rstrip('/')
        api_key = options.get('api_key') or getattr(settings, 'TABU_API_KEY', '') or ''
        path = (options.get('path') or '').strip().strip('/')
        timeout = options.get('timeout', 15)

        if not base_url:
            self.stderr.write(self.style.ERROR(
                'Brak URL API. Ustaw TABU_API_BASE_URL w .env.dev lub podaj --base-url.'
            ))
            return
        if not api_key:
            self.stderr.write(self.style.ERROR(
                'Brak klucza API. Ustaw TABU_API_KEY w .env.dev lub podaj --api-key.'
            ))
            return

        url = f"{base_url}/{path}" if path else base_url
        # Tabu API: uwierzytelnienie przez nagłówek X-API-KEY (dokumentacja API)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-API-KEY': api_key,
        }

        self.stdout.write(f'Test połączenia: GET {url}')
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            self.stdout.write(self.style.SUCCESS(f'OK (HTTP {resp.status_code})'))
            try:
                data = resp.json()
                self.stdout.write('Odpowiedź (skrót): ' + str(data)[:500] + ('...' if len(str(data)) > 500 else ''))
            except Exception:
                self.stdout.write('Odpowiedź (tekst): ' + (resp.text[:500] or '(pusta)') + ('...' if len(resp.text) > 500 else ''))
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Błąd połączenia: {e}'))
            if hasattr(e, 'response') and e.response is not None:
                self.stderr.write(f'Status: {e.response.status_code}, body: {e.response.text[:300]}')
