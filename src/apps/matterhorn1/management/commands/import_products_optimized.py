import time
from datetime import datetime, timedelta
from django.core.management.base import CommandError
from .base_api_command import BaseAPICommand


class Command(BaseAPICommand):
    """
    Zoptymalizowana komenda do importu produktów z obliczeniami czasu
    """

    help = 'Zoptymalizowany import produktów z obliczeniami czasu i rekomendacjami'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla zoptymalizowanego importu"""
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
            help='Maksymalna liczba produktów do importu (domyślnie 10000)',
            default=10000
        )
        parser.add_argument(
            '--max-hours',
            type=int,
            help='Maksymalny czas importu w godzinach (domyślnie 8)',
            default=8
        )
        parser.add_argument(
            '--resume',
            action='store_true',
            help='Kontynuuj import od ostatniego ID w bazie'
        )
        parser.add_argument(
            '--plan-only',
            action='store_true',
            help='Tylko pokaż plan importu bez wykonywania'
        )

    def handle(self, *args, **options):
        """Główna logika zoptymalizowanego importu"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        try:
            # Pobierz parametry
            endpoint = options.get('endpoint', '/B2BAPI/ITEMS/')
            start_id = options.get('start_id')
            end_id = options.get('end_id')
            batch_size = options.get('fetch_batch_size', 100)
            max_products = options.get('max_products', 10000)
            max_hours = options.get('max_hours', 8)
            resume = options.get('resume', False)
            plan_only = options.get('plan_only', False)

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

            # Oblicz szacowany czas importu
            time_estimate = self.calculate_import_time(
                total_products, batch_size)

            # Sprawdź czy nie przekraczamy maksymalnego czasu
            if time_estimate['hours'] > max_hours:
                # Oblicz maksymalną liczbę produktów dla danego czasu
                max_products_for_time = self.calculate_max_products_for_time(
                    max_hours, batch_size)
                end_id = start_id + max_products_for_time - 1
                total_products = max_products_for_time
                time_estimate = self.calculate_import_time(
                    total_products, batch_size)
                self.stdout.write(
                    f"⚠️ Ograniczono do {max_products_for_time} produktów (max {max_hours}h)")

            # Wyświetl plan importu
            self.show_import_plan(
                start_id, end_id, total_products, batch_size, time_estimate)

            if plan_only:
                self.stdout.write("📋 Tryb planowania - nie wykonuję importu")
                return

            # Potwierdź import
            if time_estimate['hours'] > 1:
                self.stdout.write(
                    f"\n⚠️ UWAGA: Import potrwa {time_estimate['hours']} godzin!")
                self.stdout.write("💡 Rozważ podzielenie na mniejsze partie")
                self.stdout.write(
                    "🛑 Naciśnij Ctrl+C aby anulować, Enter aby kontynuować...")
                try:
                    input()
                except KeyboardInterrupt:
                    self.stdout.write("❌ Import anulowany przez użytkownika")
                    return

            # Utwórz log synchronizacji
            self.create_sync_log('optimized_import')

            # Pobierz dane z API
            self.stdout.write("\n🚀 Rozpoczynam import...")
            start_time = datetime.now()

            products_data = self.fetch_products_by_id_range(
                start_id, end_id, endpoint, batch_size
            )

            if not products_data:
                self.stdout.write("❌ Brak danych do importu")
                self.complete_sync_log('success')
                return

            self.stdout.write(
                f"📥 Pobrano {len(products_data)} produktów z API")

            # Przetwórz dane w batchach
            result = self.process_batch(
                products_data,
                batch_size,
                self.process_products_batch,
                options.get('dry_run', False)
            )

            # Oblicz rzeczywisty czas
            end_time = datetime.now()
            actual_duration = end_time - start_time

            # Zakończ log synchronizacji
            self.complete_sync_log(
                'success' if result['errors'] == 0 else 'partial',
                f"Import ID {start_id}-{end_id}: {result['created']} utworzono, {result['updated']} zaktualizowano, {result['errors']} błędów"
            )

            # Wyświetl podsumowanie
            self.show_import_summary(
                start_id, end_id, result, actual_duration, time_estimate)

            # Pokaż następny zakres do importu
            self.show_next_import_range(
                end_id, max_products, max_hours, batch_size)

        except Exception as e:
            logger.error(f"Błąd zoptymalizowanego importu: {e}")
            self.complete_sync_log('error', str(e))
            raise CommandError(f"Błąd importu: {e}")

    def calculate_max_products_for_time(self, max_hours, batch_size):
        """Oblicza maksymalną liczbę produktów dla danego czasu"""
        max_seconds = max_hours * 3600
        time_per_request = 0.8
        time_per_batch = (batch_size * time_per_request) + 1
        max_batches = int(max_seconds / time_per_batch)
        return max_batches * batch_size

    def show_import_plan(self, start_id, end_id, total_products, batch_size, time_estimate):
        """Wyświetla plan importu"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("📋 PLAN IMPORTU")
        self.stdout.write("="*60)
        self.stdout.write(f"🎯 Zakres ID: {start_id} - {end_id}")
        self.stdout.write(f"📊 Liczba produktów: {total_products:,}")
        self.stdout.write(f"📦 Rozmiar batcha: {batch_size}")
        self.stdout.write(
            f"⏱️ Szacowany czas: {time_estimate['hours']}h {time_estimate['minutes']}m {time_estimate['seconds']}s")
        self.stdout.write(
            f"📈 Prędkość: {time_estimate['requests_per_second']:.1f} requestów/sekundę")
        self.stdout.write(
            f"🔄 Liczba batchów: {time_estimate['num_batches']:,}")
        self.stdout.write(
            f"📅 Szacowany koniec: {datetime.now() + timedelta(seconds=time_estimate['total_seconds'])}")
        self.stdout.write("="*60)

    def show_import_summary(self, start_id, end_id, result, actual_duration, time_estimate):
        """Wyświetla podsumowanie importu"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("✅ PODSUMOWANIE IMPORTU")
        self.stdout.write("="*60)
        self.stdout.write(f"🎯 Zakres ID: {start_id} - {end_id}")
        self.stdout.write(f"📊 Przetworzono: {result['processed']:,}")
        self.stdout.write(f"✅ Utworzono: {result['created']:,}")
        self.stdout.write(f"🔄 Zaktualizowano: {result['updated']:,}")
        self.stdout.write(f"❌ Błędów: {result['errors']:,}")
        self.stdout.write(f"⏱️ Rzeczywisty czas: {actual_duration}")
        self.stdout.write(
            f"⏱️ Szacowany czas: {time_estimate['hours']}h {time_estimate['minutes']}m {time_estimate['seconds']}s")

        # Oblicz różnicę
        estimated_seconds = time_estimate['total_seconds']
        actual_seconds = actual_duration.total_seconds()
        if actual_seconds > 0:
            ratio = actual_seconds / estimated_seconds
            if ratio > 1.1:
                self.stdout.write(
                    f"⚠️ Import trwał {ratio:.1f}x dłużej niż szacowano")
            elif ratio < 0.9:
                self.stdout.write(
                    f"✅ Import trwał {ratio:.1f}x krócej niż szacowano")
            else:
                self.stdout.write("✅ Czas importu zgodny z szacunkami")

        self.stdout.write("="*60)

    def show_next_import_range(self, end_id, max_products, max_hours, batch_size):
        """Pokazuje następny zakres do importu"""
        next_start = end_id + 1
        next_end = next_start + max_products - 1

        # Oblicz czas dla następnego zakresu
        time_estimate = self.calculate_import_time(max_products, batch_size)

        self.stdout.write(f"\n🔄 NASTĘPNY ZAKRES DO IMPORTU:")
        self.stdout.write(f"   ID: {next_start} - {next_end}")
        self.stdout.write(
            f"   Czas: {time_estimate['hours']}h {time_estimate['minutes']}m {time_estimate['seconds']}s")
        self.stdout.write(
            f"   Komenda: python manage.py import_products_optimized --start-id {next_start} --end-id {next_end}")

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
