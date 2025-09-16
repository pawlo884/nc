import json
import logging
from django.core.management.base import CommandError
from django.db import transaction

from .base_api_command import BaseAPICommand
from matterhorn1.models import Product, Brand, Category
from matterhorn1.serializers import ProductSerializer

logger = logging.getLogger(__name__)


class Command(BaseAPICommand):
    """
    Komenda do synchronizacji produktów z API Matterhorn
    """

    help = 'Synchronizuje produkty z API Matterhorn'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla synchronizacji produktów"""
        self.add_common_arguments(parser)

        parser.add_argument(
            '--create-endpoint',
            type=str,
            help='Endpoint API dla dodawania produktów (domyślnie /B2BAPI/ITEMS/)',
            default='/B2BAPI/ITEMS/'
        )
        parser.add_argument(
            '--update-endpoint',
            type=str,
            help='Endpoint API dla aktualizacji produktów (domyślnie /B2BAPI/ITEMS/INVENTORY/)',
            default='/B2BAPI/ITEMS/INVENTORY/'
        )
        parser.add_argument(
            '--update-only',
            action='store_true',
            help='Tylko aktualizuj istniejące produkty (nie tworz nowych)'
        )
        parser.add_argument(
            '--create-only',
            action='store_true',
            help='Tylko twórz nowe produkty (nie aktualizuj istniejących)'
        )
        parser.add_argument(
            '--product-ids',
            type=str,
            help='Lista ID produktów do synchronizacji (oddzielone przecinkami)',
            default=None
        )
        parser.add_argument(
            '--start-id',
            type=int,
            help='ID produktu od którego rozpocząć synchronizację (domyślnie ostatni w bazie + 1)',
            default=None
        )
        parser.add_argument(
            '--end-id',
            type=int,
            help='ID produktu na którym zakończyć synchronizację (domyślnie start_id + 1000)',
            default=None
        )
        parser.add_argument(
            '--id-range-mode',
            action='store_true',
            help='Tryb pobierania po ID (zamiast paginacji) - dla dużych importów'
        )

    def handle(self, *args, **options):
        """Główna logika synchronizacji produktów"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        # Sprawdź konfliktujące opcje
        if options['update_only'] and options['create_only']:
            raise CommandError(
                "Nie można używać --update-only i --create-only jednocześnie")

        # Utwórz log synchronizacji
        sync_type = 'products_sync'
        if options['update_only']:
            sync_type = 'products_update'
        elif options['create_only']:
            sync_type = 'products_create'

        self.create_sync_log(sync_type)

        try:
            # Pobierz dane z API
            self.stdout.write("Pobieranie danych z API...")
            products_data = self.fetch_products_data(options)

            if not products_data:
                self.stdout.write("Brak danych do synchronizacji")
                self.complete_sync_log('success')
                return

            self.stdout.write(f"Pobrano {len(products_data)} produktów z API")

            # Przetwórz dane w batchach
            batch_size = options.get('batch_size', 100)
            result = self.process_batch(
                products_data,
                batch_size,
                self.process_products_batch,
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
                f"\n✅ Synchronizacja zakończona!\n"
                f"   Przetworzono: {result['processed']}\n"
                f"   Utworzono: {result['created']}\n"
                f"   Zaktualizowano: {result['updated']}\n"
                f"   Błędów: {result['errors']}"
            ))

        except Exception as e:
            logger.error(f"Błąd synchronizacji produktów: {e}")
            self.complete_sync_log('error', str(e))
            raise CommandError(f"Błąd synchronizacji: {e}")

    def fetch_products_data(self, options):
        """Pobierz dane produktów z API"""
        create_endpoint = options.get('create_endpoint', '/B2BAPI/ITEMS/')
        update_endpoint = options.get(
            'update_endpoint', '/B2BAPI/ITEMS/INVENTORY/')
        product_ids = options.get('product_ids')
        limit = options.get('limit', 500)
        last_update = options.get('last_update')
        update_only = options.get('update_only', False)
        create_only = options.get('create_only', False)
        id_range_mode = options.get('id_range_mode', False)
        start_id = options.get('start_id')
        end_id = options.get('end_id')

        # Tryb pobierania po ID (dla dużych importów)
        if id_range_mode:
            # Pobierz ostatni ID z bazy jeśli nie podano start_id
            if start_id is None:
                last_id = self.get_last_product_id()
                start_id = last_id + 1
                self.stdout.write(
                    f"Ostatni ID w bazie: {last_id}, rozpoczynam od: {start_id}")

            # Ustaw end_id jeśli nie podano
            if end_id is None:
                end_id = start_id + 1000  # Domyślnie 1000 produktów
                self.stdout.write(f"Ustawiam end_id na: {end_id}")

            self.stdout.write(
                f"Pobieranie produktów ID {start_id}-{end_id}...")

            # Pobierz dane po ID
            products_data = self.fetch_products_by_id_range(
                start_id, end_id, create_endpoint, batch_size=100
            )

            return products_data

        if product_ids:
            # Synchronizuj konkretne produkty
            ids_list = [id.strip() for id in product_ids.split(',')]
            products_data = []

            for product_id in ids_list:
                try:
                    # Sprawdź czy produkt istnieje w bazie
                    try:
                        Product.objects.get(product_id=product_id)
                        # Produkt istnieje - użyj endpoint do aktualizacji
                        if not create_only:
                            data = self.make_api_request(
                                f"{update_endpoint}{product_id}")
                        else:
                            self.stdout.write(
                                f"  ⚠️ Produkt {product_id} już istnieje, pomijanie (--create-only)")
                            continue
                    except Product.DoesNotExist:
                        # Produkt nie istnieje - użyj endpoint do tworzenia
                        if not update_only:
                            data = self.make_api_request(
                                f"{create_endpoint}{product_id}")
                        else:
                            self.stdout.write(
                                f"  ⚠️ Produkt {product_id} nie istnieje, pomijanie (--update-only)")
                            continue

                    if data:
                        products_data.append(data)
                except CommandError:
                    self.stdout.write(
                        f"  ⚠️ Nie można pobrać produktu {product_id}")
                    continue
        else:
            # Pobierz wszystkie produkty z odpowiedniego endpointu
            if update_only:
                # Tylko aktualizacja - użyj endpoint do aktualizacji
                endpoint = update_endpoint
                params = {}
                # Tylko produkty, które już istnieją w bazie
                existing_ids = list(
                    Product.objects.values_list('product_id', flat=True))
                if existing_ids:
                    params['ids'] = ','.join(existing_ids)
                else:
                    self.stdout.write(
                        "Brak istniejących produktów do aktualizacji")
                    return []
            elif create_only:
                # Tylko tworzenie - użyj endpoint do tworzenia
                endpoint = create_endpoint
                params = {}
            else:
                # Pełna synchronizacja - pobierz z obu endpointów
                self.stdout.write("Pobieranie nowych produktów...")
                new_products = self.fetch_paginated_data(
                    create_endpoint,
                    limit=limit,
                    last_update=last_update,
                    params={}
                )

                self.stdout.write("Pobieranie produktów do aktualizacji...")
                existing_ids = list(
                    Product.objects.values_list('product_id', flat=True))
                update_products = []
                if existing_ids:
                    update_products = self.fetch_paginated_data(
                        update_endpoint,
                        limit=limit,
                        last_update=last_update,
                        params={'ids': ','.join(existing_ids)}
                    )

                # Połącz dane
                products_data = new_products + update_products
                return products_data

            # Użyj nowej metody z paginacją
            products_data = self.fetch_paginated_data(
                endpoint,
                limit=limit,
                last_update=last_update,
                params=params
            )

        return products_data

    def process_products_batch(self, products_data):
        """Przetwórz batch produktów"""
        created_count = 0
        updated_count = 0
        error_count = 0
        error_details = []

        for product_data in products_data:
            try:
                product_id = product_data.get('product_id')
                if not product_id:
                    error_count += 1
                    error_details.append({
                        'product_id': 'unknown',
                        'error': 'Brak product_id'
                    })
                    continue

                # Sprawdź czy produkt już istnieje
                try:
                    existing_product = Product.objects.get(
                        product_id=product_id)

                    # Aktualizuj istniejący produkt
                    serializer = ProductSerializer(
                        existing_product, data=product_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        updated_count += 1
                    else:
                        error_count += 1
                        error_details.append({
                            'product_id': product_id,
                            'error': f"Błąd walidacji: {serializer.errors}"
                        })

                except Product.DoesNotExist:
                    # Utwórz nowy produkt
                    serializer = ProductSerializer(data=product_data)
                    if serializer.is_valid():
                        serializer.save()
                        created_count += 1
                    else:
                        error_count += 1
                        error_details.append({
                            'product_id': product_id,
                            'error': f"Błąd walidacji: {serializer.errors}"
                        })

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

    def convert_inventory_to_product(self, inventory_item):
        """Konwertuj dane inventory na format produktu"""
        try:
            product_id = inventory_item.get('id')
            if not product_id:
                return None

            # Podstawowe dane produktu
            product_data = {
                'product_id': product_id,
                'prices': inventory_item.get('prices', {}),
                'variants': [],
                'images': []  # Inventory nie zawiera obrazów
            }

            # Konwertuj inventory na warianty
            if 'inventory' in inventory_item:
                for variant_data in inventory_item['inventory']:
                    variant = {
                        'variant_uid': variant_data.get('variant_uid'),
                        'name': variant_data.get('variant_name', ''),
                        'stock': variant_data.get('stock', '0'),
                        'ean': variant_data.get('ean', ''),
                        'max_processing_time': 0
                    }
                    product_data['variants'].append(variant)

            return product_data

        except Exception as e:
            logger.error(f"Błąd konwersji inventory do produktu: {e}")
            return None
