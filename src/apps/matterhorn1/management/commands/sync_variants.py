import json
import logging
from django.core.management.base import CommandError
from django.db import transaction

from .base_api_command import BaseAPICommand
from matterhorn1.models import Product, ProductVariant
from matterhorn1.serializers import ProductVariantSerializer

logger = logging.getLogger(__name__)


class Command(BaseAPICommand):
    """
    Komenda do synchronizacji wariantów produktów z API Matterhorn
    """

    help = 'Synchronizuje warianty produktów z API Matterhorn'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla synchronizacji wariantów"""
        self.add_common_arguments(parser)

        parser.add_argument(
            '--create-endpoint',
            type=str,
            help='Endpoint API dla dodawania wariantów (domyślnie /B2BAPI/VARIANTS/)',
            default='/B2BAPI/VARIANTS/'
        )
        parser.add_argument(
            '--update-endpoint',
            type=str,
            help='Endpoint API dla aktualizacji wariantów (domyślnie /B2BAPI/ITEMS/INVENTORY/)',
            default='/B2BAPI/ITEMS/INVENTORY/'
        )
        parser.add_argument(
            '--product-id',
            type=str,
            help='ID produktu do synchronizacji wariantów',
            default=None
        )
        parser.add_argument(
            '--variant-uids',
            type=str,
            help='Lista UID wariantów do synchronizacji (oddzielone przecinkami)',
            default=None
        )
        parser.add_argument(
            '--update-only',
            action='store_true',
            help='Tylko aktualizuj istniejące warianty (nie tworz nowych)'
        )
        parser.add_argument(
            '--create-only',
            action='store_true',
            help='Tylko twórz nowe warianty (nie aktualizuj istniejących)'
        )

    def handle(self, *args, **options):
        """Główna logika synchronizacji wariantów"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        # Sprawdź konfliktujące opcje
        if options['update_only'] and options['create_only']:
            raise CommandError(
                "Nie można używać --update-only i --create-only jednocześnie")

        # Utwórz log synchronizacji
        sync_type = 'variants_sync'
        if options['update_only']:
            sync_type = 'variants_update'
        elif options['create_only']:
            sync_type = 'variants_create'

        self.create_sync_log(sync_type)

        try:
            # Pobierz dane z API
            self.stdout.write("Pobieranie danych wariantów z API...")
            variants_data = self.fetch_variants_data(options)

            if not variants_data:
                self.stdout.write("Brak danych wariantów do synchronizacji")
                self.complete_sync_log('success')
                return

            self.stdout.write(f"Pobrano {len(variants_data)} wariantów z API")

            # Przetwórz dane w batchach
            batch_size = options.get('batch_size', 100)
            result = self.process_batch(
                variants_data,
                batch_size,
                self.process_variants_batch,
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
                f"\n✅ Synchronizacja wariantów zakończona!\n"
                f"   Przetworzono: {result['processed']}\n"
                f"   Utworzono: {result['created']}\n"
                f"   Zaktualizowano: {result['updated']}\n"
                f"   Błędów: {result['errors']}"
            ))

        except Exception as e:
            logger.error(f"Błąd synchronizacji wariantów: {e}")
            self.complete_sync_log('error', str(e))
            raise CommandError(f"Błąd synchronizacji: {e}")

    def fetch_variants_data(self, options):
        """Pobierz dane wariantów z API"""
        create_endpoint = options.get('create_endpoint', '/B2BAPI/VARIANTS/')
        update_endpoint = options.get(
            'update_endpoint', '/B2BAPI/VARIANTS/UPDATE/')
        product_id = options.get('product_id')
        variant_uids = options.get('variant_uids')
        limit = options.get('limit', 500)
        last_update = options.get('last_update')
        update_only = options.get('update_only', False)
        create_only = options.get('create_only', False)

        if variant_uids:
            # Synchronizuj konkretne warianty
            uids_list = [uid.strip() for uid in variant_uids.split(',')]
            variants_data = []

            for variant_uid in uids_list:
                try:
                    # Sprawdź czy wariant istnieje w bazie
                    try:
                        ProductVariant.objects.get(variant_uid=variant_uid)
                        # Wariant istnieje - użyj endpoint do aktualizacji
                        if not create_only:
                            data = self.make_api_request(
                                f"{update_endpoint}{variant_uid}")
                        else:
                            self.stdout.write(
                                f"  ⚠️ Wariant {variant_uid} już istnieje, pomijanie (--create-only)")
                            continue
                    except ProductVariant.DoesNotExist:
                        # Wariant nie istnieje - użyj endpoint do tworzenia
                        if not update_only:
                            data = self.make_api_request(
                                f"{create_endpoint}{variant_uid}")
                        else:
                            self.stdout.write(
                                f"  ⚠️ Wariant {variant_uid} nie istnieje, pomijanie (--update-only)")
                            continue

                    if data:
                        variants_data.append(data)
                except CommandError:
                    self.stdout.write(
                        f"  ⚠️ Nie można pobrać wariantu {variant_uid}")
                    continue
        elif product_id:
            # Synchronizuj warianty konkretnego produktu
            try:
                # Sprawdź czy produkt ma warianty w bazie
                existing_variants = ProductVariant.objects.filter(
                    product__product_id=product_id)

                if existing_variants.exists() and not create_only:
                    # Użyj endpoint do aktualizacji
                    variants_data = self.make_api_request(
                        f"{update_endpoint}product/{product_id}")
                elif not existing_variants.exists() and not update_only:
                    # Użyj endpoint do tworzenia
                    variants_data = self.make_api_request(
                        f"{create_endpoint}product/{product_id}")
                else:
                    self.stdout.write(
                        f"  ⚠️ Brak wariantów dla produktu {product_id} zgodnie z trybem")
                    return []

                if not isinstance(variants_data, list):
                    variants_data = [variants_data] if variants_data else []
            except CommandError:
                self.stdout.write(
                    f"  ⚠️ Nie można pobrać wariantów dla produktu {product_id}")
                return []
        else:
            # Pobierz wszystkie warianty z odpowiedniego endpointu
            if update_only:
                # Tylko aktualizacja - użyj endpoint do aktualizacji
                endpoint = update_endpoint
                params = {}
                # Tylko warianty, które już istnieją w bazie
                existing_uids = list(
                    ProductVariant.objects.values_list('variant_uid', flat=True))
                if existing_uids:
                    params['uids'] = ','.join(existing_uids)
                else:
                    self.stdout.write(
                        "Brak istniejących wariantów do aktualizacji")
                    return []
            elif create_only:
                # Tylko tworzenie - użyj endpoint do tworzenia
                endpoint = create_endpoint
                params = {}
            else:
                # Pełna synchronizacja - pobierz z obu endpointów
                self.stdout.write("Pobieranie nowych wariantów...")
                new_variants = self.fetch_paginated_data(
                    create_endpoint,
                    limit=limit,
                    last_update=last_update,
                    params={}
                )

                self.stdout.write("Pobieranie wariantów do aktualizacji...")
                existing_uids = list(
                    ProductVariant.objects.values_list('variant_uid', flat=True))
                update_variants = []
                if existing_uids:
                    update_variants = self.fetch_paginated_data(
                        update_endpoint,
                        limit=limit,
                        last_update=last_update,
                        params={'uids': ','.join(existing_uids)}
                    )

                # Połącz dane
                variants_data = new_variants + update_variants
                return variants_data

            # Użyj nowej metody z paginacją
            variants_data = self.fetch_paginated_data(
                endpoint,
                limit=limit,
                last_update=last_update,
                params=params
            )

        return variants_data

    def process_variants_batch(self, variants_data):
        """Przetwórz batch wariantów"""
        created_count = 0
        updated_count = 0
        error_count = 0
        error_details = []

        for variant_data in variants_data:
            try:
                variant_uid = variant_data.get('variant_uid')
                if not variant_uid:
                    error_count += 1
                    error_details.append({
                        'variant_uid': 'unknown',
                        'error': 'Brak variant_uid'
                    })
                    continue

                # Sprawdź czy wariant już istnieje
                try:
                    existing_variant = ProductVariant.objects.get(
                        variant_uid=variant_uid)

                    # Aktualizuj istniejący wariant
                    serializer = ProductVariantSerializer(
                        existing_variant, data=variant_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        updated_count += 1
                    else:
                        error_count += 1
                        error_details.append({
                            'variant_uid': variant_uid,
                            'error': f"Błąd walidacji: {serializer.errors}"
                        })

                except ProductVariant.DoesNotExist:
                    # Utwórz nowy wariant
                    # Sprawdź czy product_id istnieje
                    product_id = variant_data.get('product_id')
                    if not product_id:
                        error_count += 1
                        error_details.append({
                            'variant_uid': variant_uid,
                            'error': 'Brak product_id'
                        })
                        continue

                    try:
                        product = Product.objects.get(
                            product_id=int(product_id))
                        variant_data['product'] = product.id
                    except Product.DoesNotExist:
                        error_count += 1
                        error_details.append({
                            'variant_uid': variant_uid,
                            'error': f'Produkt {product_id} nie istnieje'
                        })
                        continue

                    serializer = ProductVariantSerializer(data=variant_data)
                    if serializer.is_valid():
                        serializer.save()
                        created_count += 1
                    else:
                        error_count += 1
                        error_details.append({
                            'variant_uid': variant_uid,
                            'error': f"Błąd walidacji: {serializer.errors}"
                        })

            except Exception as e:
                error_count += 1
                error_details.append({
                    'variant_uid': variant_data.get('variant_uid', 'unknown'),
                    'error': str(e)
                })
                logger.error(f"Błąd przetwarzania wariantu: {e}")

        return {
            'created': created_count,
            'updated': updated_count,
            'errors': error_count,
            'error_details': error_details
        }
