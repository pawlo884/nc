from datetime import datetime, timedelta
from django.core.management.base import CommandError
from .base_api_command import BaseAPICommand
import logging

logger = logging.getLogger(__name__)


class Command(BaseAPICommand):
    """
    Komenda do aktualizacji stanów magazynowych z API INVENTORY (tylko zmienione od last_update)
    """

    help = 'Aktualizuje stany magazynowe z API INVENTORY - tylko dane zmienione od last_update'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla aktualizacji inventory"""
        self.add_common_arguments(parser)

        parser.add_argument(
            '--endpoint',
            type=str,
            help='Endpoint API dla inventory (domyślnie /B2BAPI/ITEMS/INVENTORY/)',
            default='/B2BAPI/ITEMS/INVENTORY/'
        )
        parser.add_argument(
            '--inventory-last-update',
            type=str,
            help='Data ostatniej aktualizacji inventory w formacie YYYY-MM-DD HH:MM:SS (domyślnie z bazy)',
            default=None
        )
        parser.add_argument(
            '--inventory-limit',
            type=int,
            help='Limit elementów na stronę (domyślnie 500)',
            default=500
        )
        parser.add_argument(
            '--update-prices',
            action='store_true',
            help='Aktualizuj ceny produktów'
        )
        parser.add_argument(
            '--update-stock',
            action='store_true',
            help='Aktualizuj stany magazynowe wariantów'
        )
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Wymuś aktualizację wszystkich produktów (ignoruj last_update)'
        )

    def handle(self, *args, **options):
        """Główna logika aktualizacji inventory"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        # Utwórz log synchronizacji
        self.create_sync_log('inventory_update')

        try:
            # Pobierz parametry
            endpoint = options.get('endpoint', '/B2BAPI/ITEMS/INVENTORY/')
            last_update = options.get('inventory_last_update')
            limit = options.get('inventory_limit', 500)
            force_update = options.get('force_update', False)

            # Określ last_update
            if not last_update and not force_update:
                last_update = self.get_last_update_time()
                self.stdout.write(
                    f"📅 Używam ostatniej aktualizacji: {last_update}")
            elif force_update:
                last_update = None
                self.stdout.write(
                    "🔄 Wymuszam aktualizację wszystkich produktów")
            else:
                self.stdout.write(f"📅 Używam podanej daty: {last_update}")

            # Oblicz szacowany czas aktualizacji
            if last_update:
                self.stdout.write(
                    f"⏱️ Aktualizacja danych zmienionych od: {last_update}")
            else:
                self.stdout.write("⏱️ Aktualizacja wszystkich danych")

            # Pobierz dane z API
            self.stdout.write("Pobieranie danych inventory z API...")
            inventory_data = self.fetch_inventory_data(
                endpoint, limit, last_update)

            if not inventory_data:
                self.stdout.write("✅ Brak nowych danych do aktualizacji")
                self.complete_sync_log('success')
                return

            self.stdout.write(
                f"📥 Pobrano {len(inventory_data)} rekordów inventory")

            # Przetwórz dane w batchach
            batch_size = options.get('batch_size', 100)
            result = self.process_batch(
                inventory_data,
                batch_size,
                self.process_inventory_batch,
                options.get('dry_run', False)
            )

            # Zakończ log synchronizacji
            self.complete_sync_log(
                'success' if result['errors'] == 0 else 'partial',
                f"Inventory update: {result['updated']} zaktualizowano, {result['errors']} błędów"
            )

            # Wyświetl podsumowanie
            self.show_update_summary(result, last_update)

        except Exception as e:
            logger.error(f"Błąd aktualizacji inventory: {e}")
            self.complete_sync_log('error', str(e))
            raise CommandError(f"Błąd aktualizacji: {e}")

    def fetch_inventory_data(self, endpoint, limit, last_update):
        """Pobierz dane inventory z API"""
        if last_update:
            # Pobierz tylko dane zmienione od last_update
            params = {'last_update': last_update}
            inventory_data = self.fetch_paginated_data(
                endpoint,
                limit=limit,
                last_update=last_update,
                params=params
            )
        else:
            # Pobierz wszystkie dane (force_update)
            params = {}
            inventory_data = self.fetch_paginated_data(
                endpoint,
                limit=limit,
                last_update=None,
                params=params
            )

        return inventory_data

    def get_last_update_time(self):
        """Pobiera ostatni czas aktualizacji z bazy danych"""
        try:
            from matterhorn1.models import ApiSyncLog
            import pytz

            last_sync = ApiSyncLog.objects.using('matterhorn1').filter(
                sync_type__in=['inventory_update', 'inventory_sync'],
                status__in=['success', 'partial']
            ).order_by('-started_at').first()

            if last_sync and last_sync.completed_at:
                # Konwertuj na strefę czasową Polski (UTC+1/UTC+2)
                poland_tz = pytz.timezone('Europe/Warsaw')
                if last_sync.completed_at.tzinfo is None:
                    # Jeśli data jest naive, załóż że to UTC
                    utc_dt = pytz.utc.localize(last_sync.completed_at)
                else:
                    utc_dt = last_sync.completed_at.astimezone(pytz.utc)

                # Konwertuj na strefę czasową Polski
                poland_dt = utc_dt.astimezone(poland_tz)
                return poland_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                # Domyślny czas - 1 dzień temu w strefie czasowej Polski
                poland_tz = pytz.timezone('Europe/Warsaw')
                default_time = datetime.now(poland_tz) - timedelta(days=1)
                return default_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(
                f"Błąd podczas pobierania ostatniego czasu aktualizacji: {e}")
            # Domyślny czas - 1 dzień temu w strefie czasowej Polski
            poland_tz = pytz.timezone('Europe/Warsaw')
            default_time = datetime.now(poland_tz) - timedelta(days=1)
            return default_time.strftime("%Y-%m-%d %H:%M:%S")

    def process_inventory_batch(self, inventory_data):
        """Przetwórz batch inventory"""
        from matterhorn1.models import Product, ProductVariant

        updated_count = 0
        error_count = 0
        error_details = []

        # Debug: sprawdź strukturę pierwszych kilku elementów
        if inventory_data:
            logger.info(
                f"🔍 Sprawdzam strukturę {min(5, len(inventory_data))} pierwszych elementów inventory:")
            for i, item in enumerate(inventory_data[:5]):
                logger.info(f"  Element {i+1}: {list(item.keys())}")
                if 'active' in item:
                    logger.info(
                        f"    ✅ Pole 'active': {item['active']} (typ: {type(item['active'])})")
                else:
                    logger.info("    ❌ Brak pola 'active'")

            # Sprawdź czy jakikolwiek element ma pole active
            has_active = any('active' in item for item in inventory_data)
            if has_active:
                logger.info(
                    "🔍 ✅ Znaleziono produkty z polem 'active' w inventory")
            else:
                logger.info(
                    "🔍 ❌ Żaden produkt nie ma pola 'active' w inventory")

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
                        'matterhorn1').get(product_id=int(product_id))
                except Product.DoesNotExist:
                    error_count += 1
                    error_details.append({
                        'product_id': product_id,
                        'error': 'Produkt nie istnieje w bazie'
                    })
                    continue

                # Aktualizuj ceny jeśli są dostępne
                if 'prices' in item and item['prices']:
                    product.prices = item['prices']
                    product.save()
                    self.stdout.write(
                        f"  ✅ Zaktualizowano ceny dla produktu {product_id}")

                # Aktualizuj active jeśli jest dostępne
                if 'active' in item:
                    active_value = item['active']
                    # Konwersja string na boolean (jak w starym kodzie)
                    if isinstance(active_value, str):
                        active_value = active_value.lower() in ('true', '1', 'yes', 'y')
                    product.active = active_value
                    product.save()
                    self.stdout.write(
                        f"  ✅ Zaktualizowano active dla produktu {product_id}: {active_value}")

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

    def show_update_summary(self, result, last_update):
        """Wyświetla podsumowanie aktualizacji"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("✅ PODSUMOWANIE AKTUALIZACJI INVENTORY")
        self.stdout.write("="*60)
        if last_update:
            self.stdout.write(f"📅 Aktualizacja od: {last_update}")
        else:
            self.stdout.write("📅 Aktualizacja wszystkich danych")
        self.stdout.write(f"🔄 Zaktualizowano: {result['updated']:,}")
        self.stdout.write(f"❌ Błędów: {result['errors']:,}")
        self.stdout.write("="*60)
