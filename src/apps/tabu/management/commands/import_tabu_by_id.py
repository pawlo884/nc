wa"""
Import produktów Tabu pojedynczo: GET products/1, products/2, ... do 404.
Użycie po clear_tabu_data.
API: https://tabu.com.pl/api/v1/products/{id}
Użycie:
  python manage.py import_tabu_by_id --settings=core.settings.dev
  python manage.py import_tabu_by_id --start-id 1 --delay 1 --settings=core.settings.dev
"""
import logging
import signal
import time

from django.db import router, transaction
from django.db.models import Max

from tabu.models import TabuProduct

from .base_tabu_api_command import BaseTabuAPICommand
from .sync_tabu_products import Command as SyncProductsCommand

logger = logging.getLogger(__name__)


class Command(BaseTabuAPICommand):
    help = (
        'Import produktów Tabu pojedynczo (GET products/1, 2, 3...) do 404. '
        'Uruchom clear_tabu_data przed pierwszym importem.'
    )

    def add_arguments(self, parser):
        self.add_common_arguments(parser)
        parser.add_argument(
            '--start-id',
            type=int,
            default=None,
            help='ID od którego zacząć (domyślnie: max(api_id)+1 w bazie, lub 1 gdy pusta)',
        )
        parser.add_argument(
            '--stop-after-404',
            type=int,
            default=2500,
            help='Zatrzymaj po N kolejnych 404 (domyślnie: 2500)',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Opóźnienie między requestami w sekundach (domyślnie: 1)',
        )
        parser.add_argument(
            '--max-products',
            type=int,
            default=None,
            help='Maks. liczba produktów (do testów)',
        )
        parser.add_argument(
            '--max-minutes',
            type=int,
            default=None,
            help='Maks. czas działania w minutach – po tym czasie graceful exit (np. 60 dla cron co godzinę)',
        )

    def handle(self, *args, **options):
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        stop_after_404 = options['stop_after_404']

        if options['start_id'] is not None:
            start_id = options['start_id']
        else:
            db = router.db_for_write(TabuProduct)
            last_id = TabuProduct.objects.using(db).aggregate(
                max_id=Max('api_id')
            )['max_id'] or 0
            start_id = last_id + 1
            self.stdout.write(f'Ostatnie api_id w bazie: {last_id}, start od {start_id}')
        delay = max(0.7, float(options.get('delay', 1.0)))
        max_products = options.get('max_products')
        max_minutes = options.get('max_minutes')
        dry_run = options.get('dry_run', False)

        start_time = time.time()
        interrupted = [False]  # list aby mutable w closure

        def _on_signal(signum, frame):
            interrupted[0] = True
            logger.warning('Otrzymano sygnał %s – zakończenie po bieżącym produkcie', signum)

        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)

        if not dry_run:
            self.create_sync_log('products_import_by_id')

        sync_cmd = SyncProductsCommand()
        sync_cmd.api_base_url = self.api_base_url
        sync_cmd.api_key = self.api_key

        self.stdout.write(
            f'Import produktów: GET products/{{id}} od {start_id}, '
            f'stop po {stop_after_404} kolejnych 404, delay={delay}s'
        )
        if max_products:
            self.stdout.write(f'Limit: {max_products} produktów')
        if max_minutes:
            self.stdout.write(f'Maks. czas: {max_minutes} minut')

        success_count = 0
        fail_count = 0
        consecutive_404 = 0
        api_id = start_id
        db = router.db_for_write(TabuProduct)
        exit_reason = None  # None=normal, 'interrupted', 'max_minutes', 'max_products'

        try:
            while True:
                if interrupted[0]:
                    exit_reason = 'interrupted'
                    self.stdout.write('\n⚠️ Przerwano (SIGINT/SIGTERM)')
                    break
                if max_products and success_count >= max_products:
                    exit_reason = 'max_products'
                    self.stdout.write(
                        f'\nOsiągnięto limit {max_products} produktów')
                    break
                if max_minutes and (time.time() - start_time) / 60 >= max_minutes:
                    exit_reason = 'max_minutes'
                    self.stdout.write(
                        f'\n⏱ Osiągnięto limit {max_minutes} minut – graceful exit'
                    )
                    break

                time.sleep(delay)
                api_product = self.fetch_product_by_id(api_id)

                if api_product is None:
                    consecutive_404 += 1
                    if consecutive_404 >= stop_after_404:
                        self.stdout.write(
                            f'\n{stop_after_404} kolejnych 404 – koniec importu (ostatni sprawdzony: {api_id})'
                        )
                        break
                    if consecutive_404 == 1 and api_id == start_id:
                        self.stdout.write(f'   {api_id}: 404 (brak)')
                    api_id += 1
                    continue

                consecutive_404 = 0
                try:
                    if not dry_run:
                        with transaction.atomic(using=db):
                            sync_cmd._save_product(api_product)
                    success_count += 1
                    self.stdout.write(f'   #{api_id} ✓ ({success_count})')
                except Exception as e:
                    fail_count += 1
                    logger.error('Błąd produktu %s: %s', api_id, e)
                    self.stdout.write(self.style.ERROR(f'   #{api_id} ✗: {e}'))

                if not dry_run and self.sync_log and (success_count + fail_count) % 10 == 0:
                    self.update_sync_log(
                        products_processed=success_count + fail_count,
                        products_success=success_count,
                        products_failed=fail_count,
                    )

                api_id += 1

        except Exception as e:
            logger.exception('Błąd importu Tabu: %s', e)
            if not dry_run and self.sync_log:
                self.complete_sync_log('failed', str(e))
            raise

        if not dry_run and self.sync_log:
            log_kw = dict(
                products_processed=success_count + fail_count,
                products_success=success_count,
                products_failed=fail_count,
            )
            if exit_reason == 'max_minutes':
                log_kw['raw_response'] = {'exit_reason': 'max_minutes', 'max_minutes': max_minutes}
            self.update_sync_log(**log_kw)
            if exit_reason == 'interrupted':
                self.complete_sync_log('failed', 'Przerwano przez użytkownika (SIGINT/SIGTERM)')
            else:
                self.complete_sync_log('completed' if fail_count == 0 else 'completed')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Zakończono! Zaimportowano: {success_count}, błędy: {fail_count}'
            )
        )
