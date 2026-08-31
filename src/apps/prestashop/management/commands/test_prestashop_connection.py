"""
Komenda do testowania połączenia z PrestaShop WebAPI (GET /api/, autoryzacja
Basic Auth kluczem webservice).

Użycie:
  python manage.py test_prestashop_connection --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand

from prestashop.api_client import PrestaShopApiClient, PrestaShopApiError


class Command(BaseCommand):
    help = 'Testuje połączenie z PrestaShop WebAPI (pobiera listę dostępnych zasobów).'
    requires_system_checks = []

    def handle(self, *args, **options):
        try:
            client = PrestaShopApiClient()
        except PrestaShopApiError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(f'Test połączenia: GET {client.base_url}/api/')
        try:
            resources = client.list_resources()
        except PrestaShopApiError as exc:
            self.stderr.write(self.style.ERROR(f'Błąd połączenia: {exc}'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'OK - autoryzacja poprawna, sklep udostępnia {len(resources)} zasobów.'
        ))
        interesting = ['products', 'combinations', 'stock_availables',
                        'product_option_values', 'images', 'categories']
        for name in interesting:
            marker = '✅' if name in resources else '❌'
            self.stdout.write(f'  {marker} {name}')

        others = sorted(set(resources) - set(interesting))
        if others:
            self.stdout.write(
                f'\nPozostałe dostępne zasoby: {", ".join(others)}')
