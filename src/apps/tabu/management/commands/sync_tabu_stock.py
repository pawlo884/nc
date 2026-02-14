"""
Synchronizacja stanów magazynowych i cen z API Tabu (GET products/basic).
Wszystko w jednym endpoincie: stany, ceny. Historia zmian jak w Matterhorn.
Użycie:
  python manage.py sync_tabu_stock --settings=core.settings.dev
  python manage.py sync_tabu_stock --update-from 2026-01-01 --settings=core.settings.dev
  python manage.py sync_tabu_stock --debug-sample --settings=core.settings.dev  # diagnostyka struktury API
"""
import logging
import time
from decimal import Decimal

from django.db import router, transaction

from tabu.models import TabuProduct, TabuProductVariant
from tabu.stock_tracker import track_stock_change

from .base_tabu_api_command import BaseTabuAPICommand

logger = logging.getLogger(__name__)


class Command(BaseTabuAPICommand):
    help = 'Synchronizuje stany magazynowe i ceny z API Tabu (products/basic)'

    def add_arguments(self, parser):
        super().add_common_arguments(parser)
        parser.add_argument(
            '--update-from',
            type=str,
            default=None,
            help='Data od której pobierać zmiany (format: YYYY-MM-DD lub YYYY-MM-DD HH:MM:SS)',
        )
        parser.add_argument(
            '--update-to',
            type=str,
            default=None,
            help='Data do której pobierać zmiany',
        )
        parser.add_argument(
            '--debug-sample',
            action='store_true',
            help='Pobierz 1 stronę, wypisz strukturę pierwszego produktu (diagnostyka API)',
        )

    def handle(self, *args, **options):
        if options.get('debug_sample'):
            self._debug_sample(options)
            return
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        update_from = options.get('update_from')
        update_to = options.get('update_to')
        dry_run = options.get('dry_run', False)

        sync_type = 'stock_update' if update_from else 'stock_full'
        if not dry_run:
            self.create_sync_log(sync_type)

        try:
            self.stdout.write('Pobieranie stanów i cen (GET products/basic)...')

            all_products = []
            page = 1
            limit = 1000

            while True:
                params = {'page': page, 'limit': limit}
                if update_from:
                    params['update_from'] = update_from
                if update_to:
                    params['update_to'] = update_to

                data = self.make_api_request('products/basic', params=params)
                products = data.get('products', [])

                if not products:
                    break

                all_products.extend(products)

                if len(products) < limit:
                    break

                total = data.get('total')
                if total is not None and len(all_products) >= int(total):
                    break

                page += 1
                if page > 1:
                    self.stdout.write(f'   Strona {page}...')
                time.sleep(1)  # Limit API: 100 req/min

            self.stdout.write(f'   Pobrano {len(all_products)} rekordów (wariantów)')

            success_count = 0
            fail_count = 0
            history_count = 0
            variants_compared = 0
            variants_with_change = 0

            for i, api_variant in enumerate(all_products):
                if not dry_run:
                    try:
                        h, cmp_count, chg_count = self._update_variant(api_variant)
                        success_count += 1
                        history_count += h
                        variants_compared += cmp_count
                        variants_with_change += chg_count
                    except Exception as e:
                        fail_count += 1
                        logger.error(
                            f'Błąd aktualizacji wariantu {api_variant.get("variant_id")}: {e}'
                        )
                else:
                    success_count += 1

                if (i + 1) % 500 == 0:
                    self.stdout.write(f'   Przetworzono {i + 1}/{len(all_products)}...')
                    if not dry_run and self.sync_log:
                        self.update_sync_log(
                            products_processed=i + 1,
                            products_success=success_count,
                            products_failed=fail_count,
                        )

            if not dry_run:
                self.update_sync_log(
                    products_processed=len(all_products),
                    products_success=success_count,
                    products_failed=fail_count,
                    raw_response={
                        'stock_changes_logged': history_count,
                        'update_from': update_from,
                    },
                )
                self.complete_sync_log('completed' if fail_count == 0 else 'completed')

            if variants_compared > 0:
                self.stdout.write(
                    self.style.HTTP_INFO(
                        f'\n📊 Porównano {variants_compared} wariantów, '
                        f'{variants_with_change} ze zmianą stanu → {history_count} wpisów w historii.'
                    )
                )
            if history_count == 0 and variants_compared > 0:
                self.stdout.write(
                    self.style.WARNING(
                        '\n⚠️  Brak wpisów w historii – stany w API identyczne z bazą.'
                    )
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Zakończono! Przetworzono: {len(all_products)}, '
                    f'sukces: {success_count}, błędy: {fail_count}, '
                    f'zmiany w historii: {history_count}'
                )
            )

        except Exception as e:
            logger.exception(f'Błąd synchronizacji Tabu: {e}')
            if not dry_run and self.sync_log:
                self.complete_sync_log('failed', str(e))
            raise

    def _update_variant(self, api_variant):
        """
        products/basic zwraca płaską listę – każdy element to wariant (id=product_id, variant_id=variant).
        Aktualizuj stan, ceny wariantu i produktu. Zwraca (history_count, 1 lub 0, 1 lub 0).
        """
        variant_id = api_variant.get('variant_id')
        product_api_id = api_variant.get('id')
        if variant_id is None:
            logger.debug(f'Brak variant_id w rekordzie, pomijam')
            return 0, 0, 0

        variant_id = int(variant_id)
        product_api_id = int(product_api_id or 0)
        new_store = int(api_variant.get('store') or 0)

        db = router.db_for_write(TabuProduct)
        history_count = 0
        compared = 0
        with_change = 0

        with transaction.atomic(using=db):
            try:
                variant = TabuProductVariant.objects.using(db).select_related('product').get(
                    api_id=variant_id
                )
            except TabuProductVariant.DoesNotExist:
                logger.debug(f'Wariant {variant_id} nie istnieje, pomijam')
                return 0, 0, 0

            product = variant.product
            old_store = variant.store
            compared = 1

            variant.store = new_store
            vf = ['store']
            if api_variant.get('price_net') is not None:
                variant.price_net = Decimal(str(api_variant.get('price_net') or 0))
                vf.append('price_net')
            if api_variant.get('price_gross') is not None:
                variant.price_gross = Decimal(str(api_variant.get('price_gross') or 0))
                vf.append('price_gross')
            variant.save(update_fields=vf)

            product.store_total = max(
                0,
                (product.store_total or 0) - (old_store or 0) + new_store
            )
            product.save(update_fields=['store_total'])

            if old_store != new_store:
                with_change = 1
                sh = track_stock_change(
                    variant_api_id=variant_id,
                    product_api_id=product.api_id,
                    old_stock=old_store,
                    new_stock=new_store,
                    product_name=product.name,
                    variant_symbol=variant.symbol,
                )
                if sh:
                    history_count = 1

        return history_count, compared, with_change

    def _debug_sample(self, options):
        """Diagnostyka: products/basic zwraca płaską listę wariantów (id=product, variant_id=variant)."""
        self.setup_logging(True)
        self.get_api_credentials(options)
        update_from = options.get('update_from')
        if not update_from:
            from django.utils import timezone
            from datetime import timedelta
            update_from = (
                timezone.now() - timedelta(minutes=60)
            ).strftime('%Y-%m-%d %H:%M:%S')
            self.stdout.write(f'Brak --update-from, używam {update_from} (1h wstecz)')

        params = {'page': 1, 'limit': 5, 'update_from': update_from}
        data = self.make_api_request('products/basic', params=params)
        items = data.get('products', [])

        self.stdout.write(f'\n=== Odpowiedź API products/basic (płaska lista wariantów) ===')
        self.stdout.write(f'Klucze: {list(data.keys())}, total={data.get("total")}, count={data.get("count")}')
        self.stdout.write(f'Liczba rekordów: {len(items)}')

        if not items:
            self.stdout.write(self.style.WARNING('Brak rekordów'))
            return

        r = items[0]
        self.stdout.write(f'\n=== Pierwszy rekord: id(prod)={r.get("id")}, variant_id={r.get("variant_id")} ===')
        self.stdout.write(f'Klucze: {list(r.keys())}')
        self.stdout.write(f'store={r.get("store")!r}')

        db = router.db_for_read(TabuProduct)
        for r in items[:5]:
            vid = r.get('variant_id')
            pid = r.get('id')
            if vid is None:
                continue
            try:
                vdb = TabuProductVariant.objects.using(db).select_related('product').get(api_id=int(vid))
                new_s = int(r.get('store') or 0)
                self.stdout.write(
                    f'  variant_id={vid}: DB store={vdb.store}, API={new_s}, zmiana={vdb.store != new_s}'
                )
            except TabuProductVariant.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  variant_id={vid}: NIE ISTNIEJE w DB'))
