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
from decimal import Decimal, InvalidOperation

from django.db import router
from django.db.models import Sum

from tabu.models import ApiSyncLog, StockHistory, TabuProduct, TabuProductVariant

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

            fetch_fingerprint = self._fetch_fingerprint(all_products)

            if update_from and not dry_run and self._should_skip_processing(fetch_fingerprint):
                self.stdout.write(
                    self.style.WARNING(
                        '   Pomijam aktualizację: pobrane dane identyczne jak w poprzednim runie.'
                    )
                )
                self.update_sync_log(
                    products_processed=len(all_products),
                    products_success=0,
                    products_failed=0,
                    raw_response={
                        'stock_changes_logged': 0,
                        'update_from': update_from,
                        'skipped_reason': 'identical_fetch_as_previous_run',
                        'fetched_variants': len(all_products),
                        'fetch_fingerprint': fetch_fingerprint,
                    },
                )
                self.complete_sync_log('completed')
                return

            history_count = 0
            variants_compared = 0
            variants_with_change = 0
            fail_count = 0

            if not dry_run:
                history_count, variants_compared, variants_with_change, fail_count = (
                    self._apply_stock_updates(all_products)
                )
            success_count = variants_compared

            if not dry_run:
                self.update_sync_log(
                    products_processed=len(all_products),
                    products_success=success_count,
                    products_failed=fail_count,
                    raw_response={
                        'stock_changes_logged': history_count,
                        'update_from': update_from,
                        'fetch_fingerprint': fetch_fingerprint,
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

    @staticmethod
    def _fetch_fingerprint(records):
        """Stabilny odcisk pobranej listy wariantów - `(variant_id, store,
        price_net, price_gross)` posortowane. Dwa runy o tym samym odcisku
        pobrały DOKŁADNIE te same dane (nie tylko tyle samo rekordów - stąd
        stary bug: 'ta sama liczba' pomijał realne zmiany innych wariantów).
        """
        import hashlib

        rows = sorted(
            (
                int(r.get('variant_id') or 0),
                int(r.get('store') or 0),
                str(r.get('price_net') or ''),
                str(r.get('price_gross') or ''),
            )
            for r in records
            if isinstance(r, dict) and r.get('variant_id') is not None
        )
        return hashlib.sha1(repr(rows).encode()).hexdigest()

    def _should_skip_processing(self, fetch_fingerprint):
        """
        Pomija przetwarzanie stock_update tylko jeśli pobrane dane są
        IDENTYCZNE jak w poprzednim zakończonym uruchomieniu (ten sam odcisk).
        """
        if not self.sync_log:
            return False

        previous_log = (
            ApiSyncLog.objects
            .filter(sync_type='stock_update', status='completed')
            .exclude(pk=self.sync_log.pk)
            .order_by('-started_at')
            .values('raw_response')
            .first()
        )

        if not previous_log or not previous_log.get('raw_response'):
            return False

        return previous_log['raw_response'].get('fetch_fingerprint') == fetch_fingerprint

    @staticmethod
    def _parse_price(value):
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _apply_stock_updates(self, records):
        """Batch: 1 SELECT wariantów po `api_id__in` zamiast query per rekord;
        warunkowy `filter(pk=..., store=old).update(...)` per zmieniony wariant
        (idempotencja + brak wyścigu jak matterhorn1 #230); `bulk_create`
        historii; `store_total` policzony z SUMY wariantów produktu (bez dryfu
        - #233 pkt 3). Zwraca (history_count, compared, with_change, fail_count).
        """
        db = router.db_for_write(TabuProduct)

        parsed, fail_count = [], 0
        for r in records:
            if not isinstance(r, dict) or r.get('variant_id') is None:
                continue
            try:
                parsed.append({
                    'variant_id': int(r['variant_id']),
                    'new_store': int(r.get('store') or 0),
                    'price_net': self._parse_price(r.get('price_net')),
                    'price_gross': self._parse_price(r.get('price_gross')),
                })
            except (ValueError, TypeError) as e:
                fail_count += 1
                logger.error(f'Zły rekord stanu (variant_id={r.get("variant_id")}): {e}')

        if not parsed:
            return 0, 0, 0, fail_count

        variants_by_api = {
            v.api_id: v for v in
            TabuProductVariant.objects.using(db).select_related('product').filter(
                api_id__in=[p['variant_id'] for p in parsed])
        }

        history_to_create = []
        price_only = []
        affected_products = set()
        compared = 0

        for p in parsed:
            v = variants_by_api.get(p['variant_id'])
            if v is None:
                continue
            compared += 1
            old_store, new_store = v.store, p['new_store']

            if old_store != new_store:
                fields = {'store': new_store}
                if p['price_net'] is not None:
                    fields['price_net'] = p['price_net']
                if p['price_gross'] is not None:
                    fields['price_gross'] = p['price_gross']
                changed = TabuProductVariant.objects.using(db).filter(
                    pk=v.pk, store=old_store).update(**fields)
                if not changed:
                    continue  # inny run już złapał tę zmianę
                affected_products.add(v.product_id)
                history_to_create.append(StockHistory(
                    variant_api_id=v.api_id,
                    product_api_id=v.product.api_id,
                    product_name=v.product.name,
                    variant_symbol=v.symbol,
                    old_stock=old_store,
                    new_stock=new_store,
                    stock_change=new_store - old_store,
                    change_type='increase' if new_store > old_store else 'decrease',
                ))
            elif p['price_net'] is not None or p['price_gross'] is not None:
                if p['price_net'] is not None:
                    v.price_net = p['price_net']
                if p['price_gross'] is not None:
                    v.price_gross = p['price_gross']
                price_only.append(v)

        if price_only:
            TabuProductVariant.objects.using(db).bulk_update(
                price_only, ['price_net', 'price_gross'], batch_size=200)

        if affected_products:
            totals = dict(
                TabuProductVariant.objects.using(db)
                .filter(product_id__in=affected_products)
                .values('product_id').annotate(t=Sum('store'))
                .values_list('product_id', 't')
            )
            prods = list(TabuProduct.objects.using(db).filter(pk__in=affected_products))
            for prod in prods:
                prod.store_total = max(0, totals.get(prod.pk, 0) or 0)
            TabuProduct.objects.using(db).bulk_update(prods, ['store_total'], batch_size=200)

        if history_to_create:
            StockHistory.objects.using(db).bulk_create(history_to_create, batch_size=200)

        return len(history_to_create), compared, len(history_to_create), fail_count

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
