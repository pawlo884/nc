import logging
from django.core.management.base import CommandError
from .base_api_command import BaseAPICommand


logger = logging.getLogger(__name__)


class Command(BaseAPICommand):
    """
    Komenda do masowego importu produktów po ID (dla 200,000+ produktów)
    """

    help = 'Masowy import produktów po ID - kontynuuje od ostatniego ID w bazie'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla masowego importu"""
        self.add_common_arguments(parser)

        parser.add_argument(
            '--endpoint',
            type=str,
            help='Endpoint API dla produktów (domyślnie /B2BAPI/ITEMS/)',
            default='/B2BAPI/ITEMS/'
        )
        parser.add_argument(
            '--start-id',
            type=int,
            help='ID produktu od którego rozpocząć import (domyślnie ostatni w bazie + 1)',
            default=None
        )
        parser.add_argument(
            '--end-id',
            type=int,
            help='ID produktu na którym zakończyć import (domyślnie start_id + 10000)',
            default=None
        )
        parser.add_argument(
            '--fetch-batch-size',
            type=int,
            help='Rozmiar batcha dla pobierania po ID (domyślnie 100)',
            default=100
        )
        parser.add_argument(
            '--max-products',
            type=int,
            help='Maksymalna liczba produktów do importu (domyślnie 200000)',
            default=200000
        )
        parser.add_argument(
            '--resume',
            action='store_true',
            help='Kontynuuj import od ostatniego ID w bazie'
        )

    def handle(self, *args, **options):
        """Główna logika masowego importu"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        # Utwórz log synchronizacji
        self.create_sync_log('bulk_import')

        try:
            # Pobierz parametry
            endpoint = options.get('endpoint', '/B2BAPI/ITEMS/')
            start_id = options.get('start_id')
            end_id = options.get('end_id')
            batch_size = options.get('fetch_batch_size', 100)
            max_products = options.get('max_products', 200000)
            resume = options.get('resume', False)

            # Określ start_id
            if start_id is None:
                if resume:
                    last_id = self.get_last_product_id()
                    start_id = last_id + 1
                    self.stdout.write(
                        f"🔄 Kontynuuję import od ID: {start_id} (ostatni w bazie: {last_id})")
                else:
                    start_id = 1
                    self.stdout.write(
                        f"🆕 Rozpoczynam import od ID: {start_id}")

            # Określ end_id
            if end_id is None:
                end_id = start_id + max_products - 1
                self.stdout.write(f"🎯 Planowany koniec importu: ID {end_id}")

            # Sprawdź czy nie przekraczamy limitu
            total_products = end_id - start_id + 1
            if total_products > max_products:
                end_id = start_id + max_products - 1
                total_products = max_products
                self.stdout.write(
                    f"⚠️ Ograniczono do {max_products} produktów (ID {start_id}-{end_id})")

            self.stdout.write(
                f"📊 Planowany import: {total_products} produktów (ID {start_id}-{end_id})")
            self.stdout.write(f"📦 Rozmiar batcha: {batch_size}")

            # Oblicz szacowany czas importu
            time_estimate = self.calculate_import_time(
                total_products, batch_size)
            self.stdout.write(
                f"⏱️ Szacowany czas importu: {time_estimate['hours']}h {time_estimate['minutes']}m {time_estimate['seconds']}s")
            self.stdout.write(
                f"📈 Prędkość: {time_estimate['requests_per_second']:.1f} requestów/sekundę")
            self.stdout.write(
                f"🔄 Liczba batchów: {time_estimate['num_batches']}")

            # Pokaż ostrzeżenie dla długich importów
            if time_estimate['hours'] > 0:
                self.stdout.write(
                    f"⚠️ UWAGA: Import potrwa {time_estimate['hours']} godzin!")
                self.stdout.write(
                    "💡 Rozważ podzielenie na mniejsze partie (--max-products 10000)")

            # Pobierz dane z API
            self.stdout.write("Pobieranie danych z API...")
            products_data = self.fetch_products_by_id_range(
                start_id, end_id, endpoint, batch_size
            )

            if not products_data:
                self.stdout.write("Brak danych do importu")
                self.complete_sync_log('success')
                return

            self.stdout.write(f"Pobrano {len(products_data)} produktów z API")

            # Przetwórz dane w batchach
            result = self.process_batch(
                products_data,
                batch_size,
                self.process_products_batch,
                options.get('dry_run', False)
            )

            # Zakończ log synchronizacji
            self.complete_sync_log(
                'success' if result['errors'] == 0 else 'partial',
                f"Import ID {start_id}-{end_id}: {result['created']} utworzono, {result['updated']} zaktualizowano, {result['errors']} błędów"
            )

            # Wyświetl podsumowanie
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Import zakończony!\n"
                f"   Zakres ID: {start_id}-{end_id}\n"
                f"   Przetworzono: {result['processed']}\n"
                f"   Utworzono: {result['created']}\n"
                f"   Zaktualizowano: {result['updated']}\n"
                f"   Błędów: {result['errors']}"
            ))

            # Pokaż następny zakres do importu
            next_start = end_id + 1
            next_end = min(next_start + max_products - 1, next_start + 10000)
            self.stdout.write(
                f"\n🔄 Następny zakres do importu: ID {next_start}-{next_end}")
            self.stdout.write(
                f"   Komenda: python manage.py import_products_bulk --start-id {next_start} --end-id {next_end}")

        except Exception as e:
            logger.error(f"Błąd masowego importu: {e}")
            self.complete_sync_log('error', str(e))
            raise CommandError(f"Błąd importu: {e}")

    def process_products_batch(self, products_data):
        """Przetwórz batch produktów"""
        from matterhorn1.serializers import ProductSerializer

        created_count = 0
        updated_count = 0
        error_count = 0
        error_details = []

        for product_data in products_data:
            try:
                # Sprawdź czy produkt już istnieje
                product_id = product_data.get('product_id')
                if not product_id:
                    error_count += 1
                    error_details.append({
                        'product_id': 'unknown',
                        'error': 'Brak product_id w danych'
                    })
                    continue

                # Użyj serializera do tworzenia/aktualizacji
                serializer = ProductSerializer(data=product_data)
                if serializer.is_valid():
                    product, created = serializer.save()
                    if created:
                        created_count += 1
                        self.stdout.write(
                            f"  ✅ Utworzono produkt ID {product_id}")
                    else:
                        updated_count += 1
                        self.stdout.write(
                            f"  🔄 Zaktualizowano produkt ID {product_id}")
                else:
                    error_count += 1
                    error_details.append({
                        'product_id': product_id,
                        'error': f"Błąd walidacji: {serializer.errors}"
                    })
                    self.stdout.write(
                        f"  ❌ Błąd walidacji produktu ID {product_id}: {serializer.errors}")

            except Exception as e:
                error_count += 1
                error_details.append({
                    'product_id': product_data.get('product_id', 'unknown'),
                    'error': str(e)
                })
                logger.error(f"Błąd przetwarzania produktu: {e}")

        return {
            'created': created_count,
            'updated': updated_count,
            'errors': error_count,
            'error_details': error_details
        }
