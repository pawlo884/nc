from datetime import datetime, timedelta
import logging
from django.core.management.base import CommandError
from .base_api_command import BaseAPICommand


logger = logging.getLogger(__name__)


class Command(BaseAPICommand):
    """
    Komenda do sekwencyjnego importu: najpierw ITEMS, potem INVENTORY
    """

    help = 'Sekwencyjny import: najpierw produkty z ITEMS, potem stany magazynowe z INVENTORY'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla sekwencyjnego importu"""
        self.add_common_arguments(parser)

        parser.add_argument(
            '--items-endpoint',
            type=str,
            help='Endpoint API dla produktów (domyślnie /B2BAPI/ITEMS/)',
            default='/B2BAPI/ITEMS/'
        )
        parser.add_argument(
            '--inventory-endpoint',
            type=str,
            help='Endpoint API dla inventory (domyślnie /B2BAPI/ITEMS/INVENTORY/)',
            default='/B2BAPI/ITEMS/INVENTORY/'
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
        parser.add_argument(
            '--skip-items',
            action='store_true',
            help='Pomiń import ITEMS (tylko INVENTORY)'
        )
        parser.add_argument(
            '--skip-inventory',
            action='store_true',
            help='Pomiń import INVENTORY (tylko ITEMS)'
        )

    def handle(self, *args, **options):
        """Główna logika sekwencyjnego importu"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        try:
            # Pobierz parametry
            items_endpoint = options.get('items_endpoint', '/B2BAPI/ITEMS/')
            inventory_endpoint = options.get(
                'inventory_endpoint', '/B2BAPI/ITEMS/INVENTORY/')
            start_id = options.get('start_id')
            end_id = options.get('end_id')
            batch_size = options.get('fetch_batch_size', 100)
            max_products = options.get('max_products', 10000)
            max_hours = options.get('max_hours', 8)
            resume = options.get('resume', False)
            plan_only = options.get('plan_only', False)
            skip_items = options.get('skip_items', False)
            skip_inventory = options.get('skip_inventory', False)

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
            self.show_import_plan(start_id, end_id, total_products,
                                  batch_size, time_estimate, skip_items, skip_inventory)

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
            self.create_sync_log('sequential_import')

            # KROK 1: Import podstawowych danych z ITEMS
            if not skip_items:
                self.stdout.write("\n" + "="*60)
                self.stdout.write(
                    "🚀 KROK 1: IMPORT PODSTAWOWYCH DANYCH Z ITEMS")
                self.stdout.write("="*60)

                items_start_time = datetime.now()
                self.stdout.write(
                    f"📥 Pobieranie produktów ID {start_id}-{end_id} z ITEMS...")

                products_data = self.fetch_products_by_id_range(
                    start_id, end_id, items_endpoint, batch_size
                )

                if not products_data:
                    self.stdout.write("❌ Brak danych produktów z ITEMS")
                    self.complete_sync_log('error', 'Brak danych z ITEMS')
                    return

                self.stdout.write(
                    f"📥 Pobrano {len(products_data)} produktów z ITEMS")

                # Przetwórz dane produktów
                items_result = self.process_batch(
                    products_data,
                    batch_size,
                    self.process_products_batch,
                    options.get('dry_run', False)
                )

                items_duration = datetime.now() - items_start_time
                self.stdout.write(
                    f"✅ Import ITEMS zakończony w {items_duration}")
                self.stdout.write(f"   Utworzono: {items_result['created']}")
                self.stdout.write(
                    f"   Zaktualizowano: {items_result['updated']}")
                self.stdout.write(f"   Błędów: {items_result['errors']}")

                # Sprawdź czy są produkty do aktualizacji inventory
                if items_result['created'] == 0 and items_result['updated'] == 0:
                    self.stdout.write(
                        "⚠️ Brak produktów do aktualizacji inventory")
                    self.complete_sync_log(
                        'success', 'Brak produktów do aktualizacji')
                    return
            else:
                self.stdout.write("\n⏭️ Pominięto import ITEMS (--skip-items)")
                items_result = {'created': 0, 'updated': 0, 'errors': 0}

            # KROK 2: Aktualizacja stanów magazynowych z INVENTORY
            if not skip_inventory:
                self.stdout.write("\n" + "="*60)
                self.stdout.write(
                    "🔄 KROK 2: AKTUALIZACJA STANÓW MAGAZYNOWYCH Z INVENTORY")
                self.stdout.write("="*60)

                inventory_start_time = datetime.now()
                self.stdout.write(
                    "📥 Pobieranie stanów magazynowych z INVENTORY (tylko zmienione)...")

                # Użyj komendy update_inventory zamiast pobierania po ID
                from django.core.management import call_command

                try:
                    call_command('update_inventory',
                                 '--api-url', options.get('api_url', ''),
                                 '--username', options.get('username', ''),
                                 '--password', options.get('password', ''),
                                 '--endpoint', inventory_endpoint,
                                 '--batch-size', str(batch_size),
                                 '--verbose' if options.get(
                                     'verbose') else '--no-verbose',
                                 '--dry-run' if options.get('dry_run') else '--no-dry-run')

                    inventory_duration = datetime.now() - inventory_start_time
                    self.stdout.write(
                        f"✅ Aktualizacja INVENTORY zakończona w {inventory_duration}")

                    # Pobierz wyniki z logów
                    from matterhorn1.models import ApiSyncLog
                    last_sync = ApiSyncLog.objects.using('matterhorn1').filter(
                        sync_type='inventory_update'
                    ).order_by('-started_at').first()

                    if last_sync:
                        inventory_result = {
                            'updated': last_sync.records_updated,
                            'errors': last_sync.records_errors
                        }
                    else:
                        inventory_result = {'updated': 0, 'errors': 0}

                except Exception as e:
                    self.stdout.write(f"❌ Błąd aktualizacji INVENTORY: {e}")
                    inventory_result = {'updated': 0, 'errors': 1}
            else:
                self.stdout.write(
                    "\n⏭️ Pominięto import INVENTORY (--skip-inventory)")
                inventory_result = {'updated': 0, 'errors': 0}

            # Zakończ log synchronizacji
            total_created = items_result.get('created', 0)
            total_updated = items_result.get(
                'updated', 0) + inventory_result.get('updated', 0)
            total_errors = items_result.get(
                'errors', 0) + inventory_result.get('errors', 0)

            self.complete_sync_log(
                'success' if total_errors == 0 else 'partial',
                f"Import ID {start_id}-{end_id}: {total_created} utworzono, {total_updated} zaktualizowano, {total_errors} błędów"
            )

            # Wyświetl podsumowanie
            self.show_import_summary(
                start_id, end_id, items_result, inventory_result, time_estimate)

            # Pokaż następny zakres do importu
            self.show_next_import_range(
                end_id, max_products, max_hours, batch_size)

        except Exception as e:
            logger.error(f"Błąd sekwencyjnego importu: {e}")
            self.complete_sync_log('error', str(e))
            raise CommandError(f"Błąd importu: {e}")

    def process_products_batch(self, products_data):
        """Przetwórz batch produktów z ITEMS"""
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

    def process_inventory_batch(self, inventory_data):
        """Przetwórz batch danych inventory"""
        from matterhorn1.models import Product, ProductVariant

        updated_count = 0
        error_count = 0
        error_details = []

        for item in inventory_data:
            try:
                product_id = item.get('id')
                if not product_id:
                    error_count += 1
                    error_details.append({
                        'product_id': 'unknown',
                        'error': 'Brak product_id w danych inventory'
                    })
                    continue

                # Znajdź produkt w bazie
                try:
                    product = Product.objects.using(
                        'matterhorn1').get(product_id=product_id)
                except Product.DoesNotExist:
                    error_count += 1
                    error_details.append({
                        'product_id': product_id,
                        'error': 'Produkt nie istnieje w bazie (musi być najpierw zaimportowany z ITEMS)'
                    })
                    continue

                # Aktualizuj ceny jeśli są dostępne
                if 'prices' in item and item['prices']:
                    product.prices = item['prices']
                    product.save()
                    self.stdout.write(
                        f"  ✅ Zaktualizowano ceny dla produktu {product_id}")

                # Aktualizuj stany magazynowe wariantów
                if 'inventory' in item and item['inventory']:
                    for variant_data in item['inventory']:
                        variant_uid = variant_data.get('variant_uid')
                        if not variant_uid:
                            continue

                        try:
                            variant = ProductVariant.objects.using(
                                'matterhorn1').get(variant_uid=variant_uid)

                            # Aktualizuj stan magazynowy
                            if 'stock' in variant_data:
                                variant.stock = int(
                                    variant_data['stock']) if variant_data['stock'].isdigit() else 0

                            # Aktualizuj EAN jeśli jest dostępny
                            if 'ean' in variant_data and variant_data['ean']:
                                variant.ean = variant_data['ean']

                            # Aktualizuj nazwę wariantu jeśli jest dostępna
                            if 'variant_name' in variant_data and variant_data['variant_name']:
                                variant.name = variant_data['variant_name']

                            variant.save()

                        except ProductVariant.DoesNotExist:
                            # Wariant nie istnieje - utwórz go
                            variant = ProductVariant.objects.using('matterhorn1').create(
                                variant_uid=variant_uid,
                                product=product,
                                name=variant_data.get(
                                    'variant_name', 'Unknown'),
                                stock=int(variant_data.get('stock', 0)) if variant_data.get(
                                    'stock', '0').isdigit() else 0,
                                ean=variant_data.get('ean', ''),
                                max_processing_time=0
                            )
                            self.stdout.write(
                                f"  ✅ Utworzono wariant {variant_uid} dla produktu {product_id}")

                updated_count += 1

            except Exception as e:
                error_count += 1
                error_details.append({
                    'product_id': item.get('id', 'unknown'),
                    'error': str(e)
                })
                logger.error(f"Błąd przetwarzania inventory: {e}")

        return {
            'created': 0,  # Inventory nie tworzy nowych produktów
            'updated': updated_count,
            'errors': error_count,
            'error_details': error_details
        }

    def show_import_plan(self, start_id, end_id, total_products, batch_size, time_estimate, skip_items, skip_inventory):
        """Wyświetla plan importu"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("📋 PLAN SEKWENCYJNEGO IMPORTU")
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
        self.stdout.write("")
        self.stdout.write("📋 SEKWENCJA IMPORTU:")
        if not skip_items:
            self.stdout.write(
                "  1️⃣ KROK 1: Import podstawowych danych z ITEMS")
        if not skip_inventory:
            self.stdout.write(
                "  2️⃣ KROK 2: Aktualizacja stanów magazynowych z INVENTORY")
        if skip_items and skip_inventory:
            self.stdout.write("  ⚠️ Wszystkie kroki pominięte!")
        self.stdout.write("="*60)

    def show_import_summary(self, start_id, end_id, items_result, inventory_result, time_estimate):
        """Wyświetla podsumowanie importu"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("✅ PODSUMOWANIE SEKWENCYJNEGO IMPORTU")
        self.stdout.write("="*60)
        self.stdout.write(f"🎯 Zakres ID: {start_id} - {end_id}")
        self.stdout.write("")
        self.stdout.write("📊 WYNIKI ITEMS:")
        self.stdout.write(f"   Utworzono: {items_result.get('created', 0):,}")
        self.stdout.write(
            f"   Zaktualizowano: {items_result.get('updated', 0):,}")
        self.stdout.write(f"   Błędów: {items_result.get('errors', 0):,}")
        self.stdout.write("")
        self.stdout.write("📊 WYNIKI INVENTORY:")
        self.stdout.write(
            f"   Zaktualizowano: {inventory_result.get('updated', 0):,}")
        self.stdout.write(f"   Błędów: {inventory_result.get('errors', 0):,}")
        self.stdout.write("")
        self.stdout.write("📊 PODSUMOWANIE:")
        total_created = items_result.get('created', 0)
        total_updated = items_result.get(
            'updated', 0) + inventory_result.get('updated', 0)
        total_errors = items_result.get(
            'errors', 0) + inventory_result.get('errors', 0)
        self.stdout.write(f"   Utworzono: {total_created:,}")
        self.stdout.write(f"   Zaktualizowano: {total_updated:,}")
        self.stdout.write(f"   Błędów: {total_errors:,}")
        self.stdout.write("="*60)

    def show_next_import_range(self, end_id, max_products, max_hours, batch_size):
        """Pokazuje następny zakres do importu"""
        next_start = end_id + 1
        next_end = next_start + max_products - 1

        # Oblicz czas dla następnego zakresu
        time_estimate = self.calculate_import_time(max_products, batch_size)

        self.stdout.write("\n🔄 NASTĘPNY ZAKRES DO IMPORTU:")
        self.stdout.write(f"   ID: {next_start} - {next_end}")
        self.stdout.write(
            f"   Czas: {time_estimate['hours']}h {time_estimate['minutes']}m {time_estimate['seconds']}s")
        self.stdout.write(
            f"   Komenda: python manage.py import_products_sequence --start-id {next_start} --end-id {next_end}")
