import json
import logging
from django.core.management.base import CommandError

from .base_api_command import BaseAPICommand
from matterhorn1.models import Brand, Category
from matterhorn1.serializers import BrandSerializer, CategorySerializer

logger = logging.getLogger(__name__)


class Command(BaseAPICommand):
    """
    Komenda do synchronizacji marek i kategorii z API Matterhorn
    """

    help = 'Synchronizuje marki i kategorie z API Matterhorn'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla synchronizacji marek i kategorii"""
        self.add_common_arguments(parser)

        parser.add_argument(
            '--brands-endpoint',
            type=str,
            help='Endpoint API dla marek (domyślnie /B2BAPI/BRANDS/)',
            default='/B2BAPI/BRANDS/'
        )
        parser.add_argument(
            '--categories-endpoint',
            type=str,
            help='Endpoint API dla kategorii (domyślnie /B2BAPI/CATEGORIES/)',
            default='/B2BAPI/CATEGORIES/'
        )
        parser.add_argument(
            '--sync-brands',
            action='store_true',
            help='Synchronizuj tylko marki'
        )
        parser.add_argument(
            '--sync-categories',
            action='store_true',
            help='Synchronizuj tylko kategorie'
        )
        parser.add_argument(
            '--update-only',
            action='store_true',
            help='Tylko aktualizuj istniejące rekordy (nie tworz nowych)'
        )
        parser.add_argument(
            '--create-only',
            action='store_true',
            help='Tylko twórz nowe rekordy (nie aktualizuj istniejących)'
        )

    def handle(self, *args, **options):
        """Główna logika synchronizacji marek i kategorii"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        # Sprawdź konfliktujące opcje
        if options['update_only'] and options['create_only']:
            raise CommandError(
                "Nie można używać --update-only i --create-only jednocześnie")

        if not options['sync_brands'] and not options['sync_categories']:
            # Jeśli nie określono, synchronizuj oba
            options['sync_brands'] = True
            options['sync_categories'] = True

        total_created = 0
        total_updated = 0
        total_errors = 0
        all_error_details = []

        # Synchronizuj marki
        if options['sync_brands']:
            self.stdout.write("Synchronizacja marek...")
            brands_result = self.sync_brands(options)
            total_created += brands_result['created']
            total_updated += brands_result['updated']
            total_errors += brands_result['errors']
            all_error_details.extend(brands_result['error_details'])

        # Synchronizuj kategorie
        if options['sync_categories']:
            self.stdout.write("Synchronizacja kategorii...")
            categories_result = self.sync_categories(options)
            total_created += categories_result['created']
            total_updated += categories_result['updated']
            total_errors += categories_result['errors']
            all_error_details.extend(categories_result['error_details'])

        # Utwórz log synchronizacji
        sync_type = 'brands_categories_sync'
        if options['update_only']:
            sync_type = 'brands_categories_update'
        elif options['create_only']:
            sync_type = 'brands_categories_create'

        self.create_sync_log(sync_type)
        self.update_sync_log(
            records_processed=total_created + total_updated + total_errors,
            records_created=total_created,
            records_updated=total_updated,
            records_errors=total_errors,
            error_details=json.dumps(
                all_error_details) if all_error_details else ''
        )
        self.complete_sync_log(
            'success' if total_errors == 0 else 'partial',
            json.dumps(all_error_details) if all_error_details else None
        )

        # Wyświetl podsumowanie
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Synchronizacja zakończona!\n"
            f"   Utworzono: {total_created}\n"
            f"   Zaktualizowano: {total_updated}\n"
            f"   Błędów: {total_errors}"
        ))

    def sync_brands(self, options):
        """Synchronizuj marki"""
        try:
            # Pobierz dane marek z API
            brands_data = self.make_api_request(options['brands_endpoint'])

            if not isinstance(brands_data, list):
                raise CommandError("Odpowiedź API nie zawiera listy marek")

            if not brands_data:
                self.stdout.write("Brak danych marek do synchronizacji")
                return {'created': 0, 'updated': 0, 'errors': 0, 'error_details': []}

            self.stdout.write(f"Pobrano {len(brands_data)} marek z API")

            # Przetwórz dane w batchach
            batch_size = options.get('batch_size', 100)
            result = self.process_batch(
                brands_data,
                batch_size,
                self.process_brands_batch,
                options.get('dry_run', False)
            )

            return result

        except Exception as e:
            logger.error(f"Błąd synchronizacji marek: {e}")
            raise CommandError(f"Błąd synchronizacji marek: {e}")

    def sync_categories(self, options):
        """Synchronizuj kategorie"""
        try:
            # Pobierz dane kategorii z API
            categories_data = self.make_api_request(
                options['categories_endpoint'])

            if not isinstance(categories_data, list):
                raise CommandError("Odpowiedź API nie zawiera listy kategorii")

            if not categories_data:
                self.stdout.write("Brak danych kategorii do synchronizacji")
                return {'created': 0, 'updated': 0, 'errors': 0, 'error_details': []}

            self.stdout.write(
                f"Pobrano {len(categories_data)} kategorii z API")

            # Przetwórz dane w batchach
            batch_size = options.get('batch_size', 100)
            result = self.process_batch(
                categories_data,
                batch_size,
                self.process_categories_batch,
                options.get('dry_run', False)
            )

            return result

        except Exception as e:
            logger.error(f"Błąd synchronizacji kategorii: {e}")
            raise CommandError(f"Błąd synchronizacji kategorii: {e}")

    def process_brands_batch(self, brands_data):
        """Przetwórz batch marek"""
        created_count = 0
        updated_count = 0
        error_count = 0
        error_details = []

        for brand_data in brands_data:
            try:
                brand_id = brand_data.get('brand_id')
                if not brand_id:
                    error_count += 1
                    error_details.append({
                        'brand_id': 'unknown',
                        'error': 'Brak brand_id'
                    })
                    continue

                # Sprawdź czy marka już istnieje
                try:
                    existing_brand = Brand.objects.get(brand_id=brand_id)

                    # Aktualizuj istniejącą markę
                    serializer = BrandSerializer(
                        existing_brand, data=brand_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        updated_count += 1
                    else:
                        error_count += 1
                        error_details.append({
                            'brand_id': brand_id,
                            'error': f"Błąd walidacji: {serializer.errors}"
                        })

                except Brand.DoesNotExist:
                    # Utwórz nową markę
                    serializer = BrandSerializer(data=brand_data)
                    if serializer.is_valid():
                        serializer.save()
                        created_count += 1
                    else:
                        error_count += 1
                        error_details.append({
                            'brand_id': brand_id,
                            'error': f"Błąd walidacji: {serializer.errors}"
                        })

            except Exception as e:
                error_count += 1
                error_details.append({
                    'brand_id': brand_data.get('brand_id', 'unknown'),
                    'error': str(e)
                })
                logger.error(f"Błąd przetwarzania marki: {e}")

        return {
            'created': created_count,
            'updated': updated_count,
            'errors': error_count,
            'error_details': error_details
        }

    def process_categories_batch(self, categories_data):
        """Przetwórz batch kategorii"""
        created_count = 0
        updated_count = 0
        error_count = 0
        error_details = []

        for category_data in categories_data:
            try:
                category_id = category_data.get('category_id')
                if not category_id:
                    error_count += 1
                    error_details.append({
                        'category_id': 'unknown',
                        'error': 'Brak category_id'
                    })
                    continue

                # Sprawdź czy kategoria już istnieje
                try:
                    existing_category = Category.objects.get(
                        category_id=category_id)

                    # Aktualizuj istniejącą kategorię
                    serializer = CategorySerializer(
                        existing_category, data=category_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        updated_count += 1
                    else:
                        error_count += 1
                        error_details.append({
                            'category_id': category_id,
                            'error': f"Błąd walidacji: {serializer.errors}"
                        })

                except Category.DoesNotExist:
                    # Utwórz nową kategorię
                    serializer = CategorySerializer(data=category_data)
                    if serializer.is_valid():
                        serializer.save()
                        created_count += 1
                    else:
                        error_count += 1
                        error_details.append({
                            'category_id': category_id,
                            'error': f"Błąd walidacji: {serializer.errors}"
                        })

            except Exception as e:
                error_count += 1
                error_details.append({
                    'category_id': category_data.get('category_id', 'unknown'),
                    'error': str(e)
                })
                logger.error(f"Błąd przetwarzania kategorii: {e}")

        return {
            'created': created_count,
            'updated': updated_count,
            'errors': error_count,
            'error_details': error_details
        }
