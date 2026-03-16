import logging
from django.core.management.base import CommandError
from django.core.management import call_command

from .base_api_command import BaseAPICommand

logger = logging.getLogger(__name__)


class Command(BaseAPICommand):
    """
    Komenda do pełnej synchronizacji wszystkich danych z API Matterhorn
    """

    help = 'Pełna synchronizacja wszystkich danych z API Matterhorn'

    def add_arguments(self, parser):
        """Dodaj argumenty specyficzne dla pełnej synchronizacji"""
        self.add_common_arguments(parser)

        parser.add_argument(
            '--skip-brands',
            action='store_true',
            help='Pomiń synchronizację marek'
        )
        parser.add_argument(
            '--skip-categories',
            action='store_true',
            help='Pomiń synchronizację kategorii'
        )
        parser.add_argument(
            '--skip-products',
            action='store_true',
            help='Pomiń synchronizację produktów'
        )
        parser.add_argument(
            '--skip-variants',
            action='store_true',
            help='Pomiń synchronizację wariantów'
        )
        parser.add_argument(
            '--sequential-mode',
            action='store_true',
            help='Użyj trybu sekwencyjnego: najpierw ITEMS, potem INVENTORY'
        )
        parser.add_argument(
            '--max-products',
            type=int,
            help='Maksymalna liczba produktów do importu w trybie sekwencyjnym (domyślnie 10000)',
            default=10000
        )
        parser.add_argument(
            '--order',
            type=str,
            help='Kolejność synchronizacji (domyślnie: brands,categories,products,variants)',
            default='brands,categories,products,variants'
        )

    def handle(self, *args, **options):
        """Główna logika pełnej synchronizacji"""
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        # Utwórz log synchronizacji
        self.create_sync_log('full_sync')

        try:
            # Określ kolejność synchronizacji
            sync_order = options['order'].split(',')

            # Filtruj pominięte komponenty
            if options['skip_brands']:
                sync_order = [item for item in sync_order if item != 'brands']
            if options['skip_categories']:
                sync_order = [
                    item for item in sync_order if item != 'categories']
            if options['skip_products']:
                sync_order = [
                    item for item in sync_order if item != 'products']
            if options['skip_variants']:
                sync_order = [
                    item for item in sync_order if item != 'variants']

            if not sync_order:
                raise CommandError("Wszystkie komponenty zostały pominięte")

            self.stdout.write(
                f"Kolejność synchronizacji: {', '.join(sync_order)}")

            # Sprawdź czy używać trybu sekwencyjnego
            sequential_mode = options.get('sequential_mode', False)

            if sequential_mode and ('products' in sync_order or 'variants' in sync_order):
                self.stdout.write(
                    "\n🔄 TRYB SEKWENCYJNY: Najpierw ITEMS, potem INVENTORY")

                # Usuń products i variants z normalnej kolejności
                sync_order = [item for item in sync_order if item not in [
                    'products', 'variants']]

                # Wykonaj normalną synchronizację (brands, categories)
                for component in sync_order:
                    self.stdout.write(f"\n🔄 Synchronizacja {component}...")
                    self.execute_component_sync(component, options)

                # Wykonaj sekwencyjny import produktów
                self.stdout.write("\n🔄 Sekwencyjny import produktów...")
                call_command('import_products_sequence',
                             '--api-url', options.get('api_url', ''),
                             '--username', options.get('username', ''),
                             '--password', options.get('password', ''),
                             '--max-products', str(
                                 options.get('max_products', 10000)),
                             '--fetch-batch-size', str(
                                 options.get('batch_size', 100)),
                             '--verbose' if options.get(
                                 'verbose') else '--no-verbose',
                             '--dry-run' if options.get('dry_run') else '--no-dry-run')

            else:
                # Wykonaj synchronizację w określonej kolejności
                for component in sync_order:
                    self.stdout.write(f"\n🔄 Synchronizacja {component}...")
                    self.execute_component_sync(component, options)

            # Zakończ log synchronizacji
            self.complete_sync_log('success')

            self.stdout.write(self.style.SUCCESS(
                "\n✅ Pełna synchronizacja zakończona pomyślnie!"
            ))

        except Exception as e:
            logger.error(f"Błąd pełnej synchronizacji: {e}")
            self.complete_sync_log('error', str(e))
            raise CommandError(f"Błąd synchronizacji: {e}")

    def execute_component_sync(self, component, options):
        """Wykonaj synchronizację konkretnego komponentu"""
        try:
            if component == 'brands':
                call_command('sync_brands_categories',
                             '--sync-brands',
                             '--api-url', options.get('api_url', ''),
                             '--username', options.get('username', ''),
                             '--password', options.get('password', ''),
                             '--batch-size', str(options.get('batch_size', 100)),
                             '--verbose' if options.get(
                                 'verbose') else '--no-verbose',
                             '--dry-run' if options.get('dry_run') else '--no-dry-run')

            elif component == 'categories':
                call_command('sync_brands_categories',
                             '--sync-categories',
                             '--api-url', options.get('api_url', ''),
                             '--username', options.get('username', ''),
                             '--password', options.get('password', ''),
                             '--batch-size', str(options.get('batch_size', 100)),
                             '--verbose' if options.get(
                                 'verbose') else '--no-verbose',
                             '--dry-run' if options.get('dry_run') else '--no-dry-run')

            elif component == 'products':
                call_command('sync_products',
                             '--api-url', options.get('api_url', ''),
                             '--username', options.get('username', ''),
                             '--password', options.get('password', ''),
                             '--batch-size', str(options.get('batch_size', 100)),
                             '--verbose' if options.get(
                                 'verbose') else '--no-verbose',
                             '--dry-run' if options.get('dry_run') else '--no-dry-run')

            elif component == 'variants':
                call_command('sync_variants',
                             '--api-url', options.get('api_url', ''),
                             '--username', options.get('username', ''),
                             '--password', options.get('password', ''),
                             '--batch-size', str(options.get('batch_size', 100)),
                             '--verbose' if options.get(
                                 'verbose') else '--no-verbose',
                             '--dry-run' if options.get('dry_run') else '--no-dry-run')

        except Exception as e:
            logger.error(f"Błąd synchronizacji {component}: {e}")
            self.stdout.write(f"❌ Błąd synchronizacji {component}: {e}")
            raise
