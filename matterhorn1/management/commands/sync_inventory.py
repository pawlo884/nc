import json
import logging
from django.core.management.base import CommandError
from django.db import transaction

from .base_api_command import BaseAPICommand
from matterhorn1.models import Product, ProductVariant

logger = logging.getLogger(__name__)


class Command(BaseAPICommand):
    """
    Komenda do synchronizacji stanów magazynowych i cen z API Matterhorn
    """

    help = 'Synchronizuje stany magazynowe i ceny z API Matterhorn'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla synchronizacji inventory"""
        self.add_common_arguments(parser)

        parser.add_argument(
            '--endpoint',
            type=str,
            help='Endpoint API dla inventory (domyślnie /B2BAPI/ITEMS/INVENTORY/)',
            default='/B2BAPI/ITEMS/INVENTORY/'
        )
        parser.add_argument(
            '--product-ids',
            type=str,
            help='Lista ID produktów do synchronizacji (oddzielone przecinkami)',
            default=None
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

    def handle(self, *args, **options):
        """Główna logika synchronizacji inventory"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        # Utwórz log synchronizacji
        self.create_sync_log('inventory_sync')

        try:
            # Pobierz dane z API
            self.stdout.write("Pobieranie danych inventory z API...")
            inventory_data = self.fetch_inventory_data(options)

            if not inventory_data:
                self.stdout.write("Brak danych inventory do synchronizacji")
                self.complete_sync_log('success')
                return

            self.stdout.write(
                f"Pobrano {len(inventory_data)} produktów z inventory")

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
                json.dumps(result['error_details']
                           ) if result['error_details'] else None
            )

            # Wyświetl podsumowanie
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Synchronizacja inventory zakończona!\n"
                f"   Przetworzono: {result['processed']}\n"
                f"   Zaktualizowano: {result['updated']}\n"
                f"   Błędów: {result['errors']}"
            ))

        except Exception as e:
            logger.error(f"Błąd synchronizacji inventory: {e}")
            self.complete_sync_log('error', str(e))
            raise CommandError(f"Błąd synchronizacji: {e}")

    def fetch_inventory_data(self, options):
        """Pobierz dane inventory z API"""
        endpoint = options.get('endpoint', '/B2BAPI/ITEMS/INVENTORY/')
        product_ids = options.get('product_ids')
        limit = options.get('limit', 500)
        last_update = options.get('last_update')

        if product_ids:
            # Synchronizuj konkretne produkty
            ids_list = [id.strip() for id in product_ids.split(',')]
            inventory_data = []

            for product_id in ids_list:
                try:
                    data = self.make_api_request(f"{endpoint}{product_id}")
                    if data:
                        inventory_data.append(data)
                except CommandError:
                    self.stdout.write(
                        f"  ⚠️ Nie można pobrać inventory dla produktu {product_id}")
                    continue
        else:
            # Pobierz dane inventory z paginacją (tylko zmienione od last_update)
            if not last_update:
                # Jeśli nie podano last_update, pobierz z bazy
                last_update = self.get_last_update_time()
                self.stdout.write(
                    f"📅 Używam ostatniej aktualizacji: {last_update}")

            params = {}
            inventory_data = self.fetch_paginated_data(
                endpoint,
                limit=limit,
                last_update=last_update,
                params=params
            )

        return inventory_data

    def get_last_update_time(self):
        """Pobiera ostatni czas aktualizacji z bazy danych"""
        try:
            from matterhorn1.models import ApiSyncLog
            last_sync = ApiSyncLog.objects.using('matterhorn1').filter(
                sync_type='inventory_sync',
                status__in=['success', 'partial']
            ).order_by('-started_at').first()

            if last_sync and last_sync.completed_at:
                return last_sync.completed_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                # Domyślny czas - 1 dzień temu
                from datetime import datetime, timedelta
                default_time = datetime.now() - timedelta(days=1)
                return default_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(
                f"Błąd podczas pobierania ostatniego czasu aktualizacji: {e}")
            # Domyślny czas - 1 dzień temu
            from datetime import datetime, timedelta
            default_time = datetime.now() - timedelta(days=1)
            return default_time.strftime("%Y-%m-%d %H:%M:%S")

    def process_inventory_batch(self, inventory_data):
        """Przetwórz batch inventory"""
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
                    product = Product.objects.get(product_id=product_id)
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

                # Aktualizuj stany magazynowe wariantów
                if 'inventory' in item and item['inventory']:
                    for variant_data in item['inventory']:
                        variant_uid = variant_data.get('variant_uid')
                        if not variant_uid:
                            continue

                        try:
                            variant = ProductVariant.objects.get(
                                variant_uid=variant_uid)

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
                            variant = ProductVariant.objects.create(
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
