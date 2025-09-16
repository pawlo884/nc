import requests
import json
import logging
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import datetime

from matterhorn1.models import ApiSyncLog

logger = logging.getLogger(__name__)


class BaseAPICommand(BaseCommand):
    """
    Bazowa klasa dla komend synchronizacji z API Matterhorn
    """

    help = 'Base command for API synchronization'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base_url = None
        self.api_username = None
        self.api_password = None
        self.sync_log = None

    def add_common_arguments(self, parser):
        """Dodaj wspólne argumenty dla wszystkich komend"""
        parser.add_argument(
            '--api-url',
            type=str,
            help='URL API Matterhorn (domyślnie z ustawień)',
            default=None
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Nazwa użytkownika API (domyślnie z ustawień)',
            default=None
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Hasło API (domyślnie z ustawień)',
            default=None
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            help='Rozmiar batch dla bulk operations (domyślnie 100)',
            default=100
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit elementów na stronę (domyślnie 500)',
            default=500
        )
        parser.add_argument(
            '--last-update',
            type=str,
            help='Data ostatniej aktualizacji w formacie YYYY-MM-DD HH:MM:SS',
            default=None
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Tryb testowy - nie zapisuje danych do bazy'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Szczegółowe logowanie'
        )

    def setup_logging(self, verbose=False):
        """Konfiguruj logowanie"""
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def get_api_credentials(self, options):
        """Pobierz dane dostępowe do API"""
        from django.conf import settings

        self.api_base_url = options.get('api_url') or getattr(
            settings, 'MATTERHORN_API_URL', None)
        self.api_username = options.get('username') or getattr(
            settings, 'MATTERHORN_API_USERNAME', None)
        self.api_password = options.get('password') or getattr(
            settings, 'MATTERHORN_API_PASSWORD', None)

        if not all([self.api_base_url, self.api_username, self.api_password]):
            raise CommandError(
                "Brak konfiguracji API. Ustaw MATTERHORN_API_URL, "
                "MATTERHORN_API_USERNAME, MATTERHORN_API_PASSWORD w settings "
                "lub użyj argumentów --api-url, --username, --password"
            )

    def create_sync_log(self, sync_type, status='started'):
        """Utwórz log synchronizacji"""
        self.sync_log = ApiSyncLog.objects.create(
            sync_type=sync_type,
            status=status,
            started_at=timezone.now()
        )
        return self.sync_log

    def update_sync_log(self, **kwargs):
        """Aktualizuj log synchronizacji"""
        if self.sync_log:
            for key, value in kwargs.items():
                setattr(self.sync_log, key, value)
            self.sync_log.save()

    def complete_sync_log(self, status='success', error_details=None):
        """Zakończ log synchronizacji"""
        if self.sync_log:
            self.sync_log.status = status
            self.sync_log.completed_at = timezone.now()
            if self.sync_log.started_at:
                duration = (self.sync_log.completed_at -
                            self.sync_log.started_at).total_seconds()
                self.sync_log.duration_seconds = duration
            if error_details:
                self.sync_log.error_details = error_details
            self.sync_log.save()

    def make_api_request(self, endpoint, method='GET', data=None, params=None):
        """Wykonaj żądanie do API"""
        url = f"{self.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        auth = (self.api_username, self.api_password)
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            if method.upper() == 'GET':
                response = requests.get(
                    url, auth=auth, headers=headers, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(
                    url, auth=auth, headers=headers, json=data, timeout=30)
            else:
                raise CommandError(f"Nieobsługiwana metoda HTTP: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Błąd żądania API: {e}")
            raise CommandError(f"Błąd połączenia z API: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Błąd parsowania JSON: {e}")
            raise CommandError(f"Błąd parsowania odpowiedzi API: {e}")

    def process_batch(self, data, batch_size, process_func, dry_run=False):
        """Przetwórz dane w batchach"""
        total_processed = 0
        total_created = 0
        total_updated = 0
        total_errors = 0
        errors = []

        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(data) + batch_size - 1) // batch_size

            self.stdout.write(
                f"Przetwarzanie batch {batch_num}/{total_batches} "
                f"({len(batch)} elementów)..."
            )

            try:
                if not dry_run:
                    with transaction.atomic():
                        batch_result = process_func(batch)
                else:
                    self.stdout.write("  [DRY RUN] Pomijanie zapisu do bazy")
                    batch_result = {
                        'created': len(batch),
                        'updated': 0,
                        'errors': 0,
                        'error_details': []
                    }

                total_processed += len(batch)
                total_created += batch_result.get('created', 0)
                total_updated += batch_result.get('updated', 0)
                total_errors += batch_result.get('errors', 0)

                if batch_result.get('error_details'):
                    errors.extend(batch_result['error_details'])

                self.stdout.write(
                    f"  ✅ Batch {batch_num} zakończony: "
                    f"utworzono {batch_result.get('created', 0)}, "
                    f"zaktualizowano {batch_result.get('updated', 0)}, "
                    f"błędów {batch_result.get('errors', 0)}"
                )

            except Exception as e:
                logger.error(f"Błąd w batch {batch_num}: {e}")
                total_errors += len(batch)
                errors.append({
                    'batch': batch_num,
                    'error': str(e)
                })
                self.stdout.write(f"  ❌ Błąd w batch {batch_num}: {e}")

        return {
            'processed': total_processed,
            'created': total_created,
            'updated': total_updated,
            'errors': total_errors,
            'error_details': errors
        }

    def fetch_paginated_data(self, endpoint, limit=500, last_update=None, params=None):
        """Pobierz wszystkie dane z API z obsługą paginacji"""
        all_data = []
        page = 1

        # Przygotuj parametry
        if params is None:
            params = {}

        params['limit'] = limit
        if last_update:
            params['last_update'] = last_update

        self.stdout.write(f"Pobieranie danych z {endpoint} (limit={limit})...")

        while True:
            # Dodaj numer strony do parametrów
            current_params = params.copy()
            current_params['page'] = page

            try:
                self.stdout.write(f"  Strona {page}...")
                response_data = self.make_api_request(
                    endpoint, params=current_params)

                # Sprawdź czy odpowiedź zawiera dane
                if isinstance(response_data, list):
                    data_list = response_data
                elif isinstance(response_data, dict) and 'data' in response_data:
                    data_list = response_data['data']
                elif isinstance(response_data, dict) and 'items' in response_data:
                    data_list = response_data['items']
                else:
                    # Jeśli to pojedynczy obiekt, dodaj do listy
                    data_list = [response_data] if response_data else []

                if not data_list:
                    self.stdout.write(
                        f"  Brak danych na stronie {page}, kończenie...")
                    break

                all_data.extend(data_list)
                self.stdout.write(
                    f"  Pobrano {len(data_list)} elementów ze strony {page}")

                # Jeśli pobrano mniej niż limit, to była ostatnia strona
                if len(data_list) < limit:
                    self.stdout.write(
                        f"  Ostatnia strona osiągnięta (pobrano {len(data_list)} < {limit})")
                    break

                page += 1

                # Zabezpieczenie przed nieskończoną pętlą
                if page > 1000:  # Maksymalnie 1000 stron
                    self.stdout.write(
                        "  ⚠️ Osiągnięto limit 1000 stron, przerywanie...")
                    break

            except CommandError as e:
                logger.error(f"Błąd pobierania strony {page}: {e}")
                self.stdout.write(f"  ❌ Błąd pobierania strony {page}: {e}")
                break

        self.stdout.write(
            f"Pobrano łącznie {len(all_data)} elementów z {page-1} stron")
        return all_data

    def get_last_product_id(self):
        """
        Pobiera ostatni ID produktu z bazy danych
        """
        try:
            from matterhorn1.models import Product
            last_product = Product.objects.using('matterhorn1').filter(
                name__isnull=False
            ).exclude(
                name__in=['Placeholder Name', '0 Nowy artykul - 0']
            ).order_by('-product_id').first()

            if last_product:
                return int(last_product.product_id)
            else:
                return 0
        except Exception as e:
            logger.error(
                f"Błąd podczas pobierania ostatniego ID produktu: {e}")
            return 0

    def fetch_products_by_id_range(self, start_id, end_id, endpoint, batch_size=100):
        """
        Pobiera produkty po ID w zakresie (dla dużych importów)
        """
        all_data = []
        current_id = start_id

        while current_id <= end_id:
            batch_end = min(current_id + batch_size - 1, end_id)
            self.stdout.write(f"  📦 Pobieranie ID {current_id}-{batch_end}...")

            batch_data = []
            for product_id in range(current_id, batch_end + 1):
                try:
                    url = f"{endpoint}{product_id}"
                    data = self.make_api_request(url)

                    if data and data.get('id'):
                        batch_data.append(data)
                        self.stdout.write(
                            f"    ✅ ID {product_id}: {data.get('name', 'Unknown')}")
                    else:
                        self.stdout.write(
                            f"    ⚠️ ID {product_id}: Brak danych")

                    # Opóźnienie między requestami (zgodnie z ograniczeniami API: 0.6s)
                    time.sleep(0.6)

                except Exception as e:
                    self.stdout.write(f"    ❌ ID {product_id}: {e}")
                    continue

            all_data.extend(batch_data)
            self.stdout.write(
                f"  📊 Batch {current_id}-{batch_end}: {len(batch_data)} produktów")

            current_id = batch_end + 1

            # Opóźnienie między batchami (dodatkowe 1s po batchu)
            time.sleep(1)

        return all_data

    def calculate_import_time(self, total_products, batch_size=100):
        """
        Oblicza szacowany czas importu na podstawie ograniczeń API
        """
        # Czas na pojedynczy request: 0.6s + czas odpowiedzi (~0.2s) = ~0.8s
        time_per_request = 0.8

        # Czas na batch: (batch_size * time_per_request) + 1s opóźnienie
        time_per_batch = (batch_size * time_per_request) + 1

        # Liczba batchów
        num_batches = (total_products + batch_size - 1) // batch_size

        # Całkowity czas
        total_seconds = num_batches * time_per_batch

        # Konwersja na godziny, minuty, sekundy
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        return {
            'total_seconds': total_seconds,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'requests_per_second': 1 / time_per_request,
            'num_batches': num_batches
        }

    def handle(self, *args, **options):
        """Główna metoda - do zaimplementowania w klasach potomnych"""
        raise NotImplementedError("Subclasses must implement handle method")
