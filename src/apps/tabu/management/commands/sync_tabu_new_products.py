"""
Sprawdza czy w API Tabu są nowe produkty – max(api_id)+1, potem kolejne.
Zatrzymanie po N kolejnych 404 (luki w numeracji – np. produkt usunięty).
Użycie:
  python manage.py sync_tabu_new_products --settings=core.settings.dev
  python manage.py sync_tabu_new_products --stop-after-404 10 --max-products 500 --settings=core.settings.dev
"""
import logging
import time

from billiard.exceptions import SoftTimeLimitExceeded
from django.db import router, transaction
from django.db.models import Max

from tabu.models import TabuProduct

from .base_tabu_api_command import BaseTabuAPICommand
from .sync_tabu_products import Command as SyncProductsCommand

logger = logging.getLogger(__name__)


class Command(BaseTabuAPICommand):
    help = 'Sprawdza nowe produkty Tabu: max(api_id)+1, stop po N kolejnych 404'

    def add_arguments(self, parser):
        super().add_common_arguments(parser)
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Opóźnienie między requestami (s)',
        )
        parser.add_argument(
            '--stop-after-404',
            type=int,
            default=10,
            help='Zatrzymaj po N kolejnych 404 (domyślnie: 10)',
        )
        parser.add_argument(
            '--max-products',
            type=int,
            default=None,
            help='Maks. produktów na uruchomienie (opcjonalnie, domyślnie: bez limitu)',
        )

    def handle(self, *args, **options):
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        delay = max(0.7, float(options.get('delay', 1.0)))
        stop_after_404 = options.get('stop_after_404', 10)
        max_products = options.get('max_products')
        dry_run = options.get('dry_run', False)

        if not dry_run:
            self.create_sync_log('products_new_check')

        try:
            db = router.db_for_write(TabuProduct)
            last_id = TabuProduct.objects.using(db).aggregate(
                max_id=Max('api_id')
            )['max_id'] or 0
            next_id = last_id + 1

            self.stdout.write(
                f'Ostatnie api_id w bazie: {last_id}, stop po {stop_after_404} kolejnych 404'
            )
            if max_products:
                self.stdout.write(f'Limit: {max_products} produktów na uruchomienie')
            self.stdout.write(f'Sprawdzam produkt #{next_id}...')

            sync_cmd = SyncProductsCommand()
            sync_cmd.api_base_url = self.api_base_url
            sync_cmd.api_key = self.api_key
            sync_cmd.sync_log = self.sync_log

            imported = 0
            consecutive_404 = 0
            while True:
                if max_products and imported >= max_products:
                    self.stdout.write(f'\nOsiągnięto limit {max_products} produktów')
                    break

                time.sleep(delay)
                api_product = self.fetch_product_by_id(next_id)
                if api_product is None:
                    consecutive_404 += 1
                    if consecutive_404 >= stop_after_404:
                        self.stdout.write(
                            f'\n{stop_after_404} kolejnych 404 – koniec (ostatni: #{next_id})'
                        )
                        break
                    if consecutive_404 == 1:
                        self.stdout.write(f'   #{next_id} → 404')
                    next_id += 1
                    continue

                consecutive_404 = 0
                if not dry_run:
                    try:
                        with transaction.atomic(using=db):
                            sync_cmd._save_product(api_product)
                        self.stdout.write(f'   Zaimportowano produkt #{next_id}')
                    except Exception as e:
                        logger.error(f'Błąd importu #{next_id}: {e}')
                        break

                next_id += 1
                imported += 1
                if imported > 0 and imported % 10 == 0:
                    self.stdout.write(f'   Sprawdzam #{next_id}...')
                if not dry_run and self.sync_log and imported > 0 and imported % 10 == 0:
                    self.update_sync_log(
                        products_processed=imported,
                        products_success=imported,
                        products_failed=0,
                        raw_response={
                            'new_products_imported': imported,
                            'last_checked_id': next_id - 1,
                        },
                    )

            if not dry_run:
                self.update_sync_log(
                    products_processed=imported,
                    products_success=imported,
                    products_failed=0,
                    raw_response={
                        'new_products_imported': imported,
                        'last_checked_id': next_id - 1,
                    },
                )
                self.complete_sync_log('completed')

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Zakończono. Zaimportowano {imported} nowych produktów.'
                )
            )

        except SoftTimeLimitExceeded:
            if not dry_run and self.sync_log:
                self.update_sync_log(
                    products_processed=imported,
                    products_success=imported,
                    products_failed=0,
                    raw_response={
                        'new_products_imported': imported,
                        'last_checked_id': next_id - 1,
                    },
                )
                self.complete_sync_log('failed', 'SoftTimeLimitExceeded')
            logger.warning('SoftTimeLimitExceeded - przerwano sprawdzanie nowych produktów')
            raise

        except Exception as e:
            logger.exception(f'Błąd sprawdzania nowych produktów: {e}')
            if not dry_run and self.sync_log:
                self.complete_sync_log('failed', str(e))
            raise
