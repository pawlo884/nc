"""
Sprawdza czy w API Tabu są nowe produkty – persistentny licznik check_range.

Logika:
  - Każde uruchomienie sprawdza o 1 ID więcej niż poprzednie (check_range += 1).
  - Gdy znajdzie produkt → importuje i resetuje check_range = 0.
  - check_range jest zapisywany w ApiSyncLog.raw_response i odczytywany przy starcie.

Przykład:
  Task 1: check_range=1, sprawdza max+1            → 404, zapisuje check_range=1
  Task 2: check_range=2, sprawdza max+1, max+2     → 404, 404, zapisuje check_range=2
  Task 3: check_range=3, sprawdza max+1 .. max+3   → 404, 200 (import!), reset check_range=0
  Task 4: check_range=1, sprawdza nowe max+1       → ...

Użycie:
  python manage.py sync_tabu_new_products --settings=core.settings.dev
  python manage.py sync_tabu_new_products --delay 0.7 --settings=core.settings.dev
"""
import logging
import time

from billiard.exceptions import SoftTimeLimitExceeded
from django.db import router, transaction
from django.db.models import Max

from tabu.models import ApiSyncLog, TabuProduct

from .base_tabu_api_command import BaseTabuAPICommand
from .sync_tabu_products import Command as SyncProductsCommand

logger = logging.getLogger(__name__)


class Command(BaseTabuAPICommand):
    help = 'Sprawdza nowe produkty Tabu: persistentny check_range rośnie o 1 co task, zeruje po znalezieniu'

    def add_arguments(self, parser):
        super().add_common_arguments(parser)
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Opóźnienie między requestami (s)',
        )

    def _load_check_range(self, db):
        """Odczytaj check_range z ostatniego logu. Zwraca 0 jeśli brak."""
        last_log = (
            ApiSyncLog.objects.using(db)  # type: ignore[attr-defined]
            .filter(sync_type='products_new_check', status='completed')
            .order_by('-started_at')
            .values('raw_response')
            .first()
        )
        if last_log and last_log.get('raw_response'):
            return last_log['raw_response'].get('check_range', 0)
        return 0

    def handle(self, *args, **options):
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        delay = max(0.7, float(options.get('delay', 1.0)))
        dry_run = options.get('dry_run', False)

        if not dry_run:
            self.create_sync_log('products_new_check')

        imported = 0
        next_id = 0
        check_range = 0
        missing_ids = []
        last_checked_id = 0

        try:
            db = router.db_for_write(TabuProduct)

            # Odczytaj persistentny licznik z poprzedniego uruchomienia
            prev_check_range = self._load_check_range(db)
            check_range = prev_check_range + 1

            last_id = TabuProduct.objects.using(db).aggregate(  # type: ignore[attr-defined]
                max_id=Max('api_id')
            )['max_id'] or 0
            next_id = last_id + 1
            last_checked_id = last_id

            self.stdout.write(
                f'Ostatnie api_id w bazie: {last_id} | '
                f'check_range: {prev_check_range} → {check_range} | '
                f'Sprawdzam #{next_id} .. #{next_id + check_range - 1}'
            )

            sync_cmd = SyncProductsCommand()
            sync_cmd.api_base_url = self.api_base_url
            sync_cmd.api_key = self.api_key
            sync_cmd.sync_log = self.sync_log

            found = False
            for i in range(check_range):
                current_id = last_id + 1 + i
                time.sleep(delay)
                api_product = self.fetch_product_by_id(current_id)
                last_checked_id = current_id

                if api_product is None:
                    self.stdout.write(f'   #{current_id} → 404')
                    missing_ids.append(current_id)
                    continue

                # Znaleziono produkt – importuj i resetuj licznik
                if not dry_run:
                    try:
                        with transaction.atomic(using=db):  # type: ignore[misc]
                            sync_cmd._save_product(api_product)
                        self.stdout.write(f'   #{current_id} → zaimportowano')
                    except Exception as e:
                        logger.error(f'Błąd importu #{current_id}: {e}')
                        break

                imported += 1
                found = True

            # Jeśli już znaleźliśmy nowy produkt, importuj dalej kolejne ID aż do 404.
            if found:
                current_id = last_id + check_range + 1
                while True:
                    time.sleep(delay)
                    api_product = self.fetch_product_by_id(current_id)
                    last_checked_id = current_id
                    if api_product is None:
                        self.stdout.write(f'   #{current_id} → 404 (koniec serii nowych)')
                        break

                    if not dry_run:
                        try:
                            with transaction.atomic(using=db):  # type: ignore[misc]
                                sync_cmd._save_product(api_product)
                            self.stdout.write(f'   #{current_id} → zaimportowano')
                        except Exception as e:
                            logger.error(f'Błąd importu #{current_id}: {e}')
                            break

                    imported += 1
                    current_id += 1

            # Jeżeli znaleziono nowy produkt, spróbuj ponownie ID z wcześniejszym 404
            # (czasem API zwraca z opóźnieniem i produkt pojawia się chwilę później).
            if found and missing_ids:
                self.stdout.write(
                    f'   🔁 Dodatkowa weryfikacja {len(missing_ids)} wcześniejszych 404...'
                )
                for missing_id in missing_ids:
                    time.sleep(delay)
                    api_product = self.fetch_product_by_id(missing_id)
                    if api_product is None:
                        continue
                    if not dry_run:
                        try:
                            with transaction.atomic(using=db):  # type: ignore[misc]
                                sync_cmd._save_product(api_product)
                            self.stdout.write(f'   #{missing_id} → zaimportowano (retry)')
                        except Exception as e:
                            logger.error(f'Błąd importu retry #{missing_id}: {e}')
                            continue
                    imported += 1

            if found:
                check_range = 0  # reset – następny task startuje od 1

            if not dry_run:
                self.update_sync_log(
                    products_processed=check_range if not found else 0,
                    products_success=imported,
                    products_failed=0,
                    raw_response={
                        'check_range': check_range,
                        'new_products_imported': imported,
                        'last_checked_id': last_checked_id,
                    },
                )
                self.complete_sync_log('completed')

            self.stdout.write(
                self.style.SUCCESS(  # type: ignore[attr-defined]
                    f'\n✅ Zakończono. Zaimportowano {imported} nowych produktów. '
                    f'Następny task sprawdzi {check_range + 1 if not found else 1} ID.'
                )
            )

        except SoftTimeLimitExceeded:
            if not dry_run and self.sync_log:
                self.update_sync_log(
                    products_processed=0,
                    products_success=imported,
                    products_failed=0,
                    raw_response={
                        'check_range': check_range,
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
