"""
Komenda do testowania połączenia z API Mada (get_xml.php, auth przez parametry l/p).

Użycie:
  python manage.py test_mada_connection --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand

from mada.api_client import MadaApiClient, MadaApiError


class Command(BaseCommand):
    help = 'Testuje połączenie z API Mada (pobiera manifest plików).'
    requires_system_checks = []

    def handle(self, *args, **options):
        try:
            client = MadaApiClient()
        except MadaApiError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(f'Test połączenia: GET {client.base_url}/get_xml.php')
        try:
            files = client.list_files()
        except MadaApiError as exc:
            self.stderr.write(self.style.ERROR(f'Błąd połączenia: {exc}'))
            return

        full_files = [f for f in files if f.is_full]
        partial_files = [f for f in files if f.type == 'partial']
        self.stdout.write(self.style.SUCCESS(
            f'OK - manifest zawiera {len(files)} plików '
            f'({len(full_files)} full, {len(partial_files)} partial)'
        ))
        latest_full = max(full_files, key=lambda f: f.date, default=None) if full_files else None
        if latest_full:
            self.stdout.write(f'Najnowszy pełny plik: {latest_full.name} ({latest_full.date})')
        if partial_files:
            newest_partial = max(partial_files, key=lambda f: f.name)
            self.stdout.write(f'Najnowszy plik partial: {newest_partial.name} ({newest_partial.date})')
