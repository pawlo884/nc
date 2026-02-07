"""
Komenda do pełnego importu i synchronizacji produktów z API Tabu.
Użycie:
  python manage.py sync_tabu_products --settings=core.settings.dev
  python manage.py sync_tabu_products --update-from 2026-01-01 --settings=core.settings.dev
"""
import logging
from datetime import datetime
from decimal import Decimal

from django.db import router, transaction

from tabu.models import TabuProduct
from django.utils import timezone

from tabu.models import TabuProduct, TabuProductVariant

from .base_tabu_api_command import BaseTabuAPICommand

logger = logging.getLogger(__name__)


def parse_datetime(value):
    """Parsuj datę z API (format: '2026-01-20 12:29:24')"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value)[:19], '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return None


def _extract_color_size(items):
    """Wyciągnij kolor i rozmiar z items wariantu"""
    color = ''
    size = ''
    for item in items or []:
        name = (item.get('name') or '').lower()
        value = str(item.get('value') or '').strip()
        if 'kolor' in name or 'color' in name:
            color = value
        elif 'rozmiar' in name or 'size' in name:
            size = value
    return color, size


def map_api_product_to_model(api_product):
    """
    Mapuj dane produktu z API na dict do TabuProduct.
    API: id, symbol, ean, name, desc_short, category, category_id, image, producer,
         producer_id, producer_code, price_net, price_gross, price_old, price_kind,
         vat, vat_id, vat_value, store, unit, unit_id, weight, status, status_id,
         status_auto, url, version_signature, preorder, hidden_search, last_update, variants
    """
    variants = api_product.get('variants') or []
    store_total = sum(
        int(v.get('store') or 0)
        for v in variants
    )
    last_update = parse_datetime(api_product.get('last_update'))

    return {
        'api_id': int(api_product['id']),
        'symbol': str(api_product.get('symbol') or ''),
        'ean': str(api_product.get('ean') or '')[:50],
        'name': str(api_product.get('name') or ''),
        'desc_short': api_product.get('desc_short') or '',
        'category_path': str(api_product.get('category') or ''),
        'category_id': int(api_product.get('category_id') or 0),
        'producer_name': str(api_product.get('producer') or ''),
        'producer_id': int(api_product.get('producer_id') or 0),
        'producer_code': str(api_product.get('producer_code') or '')[:100],
        'image_url': str(api_product.get('image') or '')[:1000],
        'price_net': Decimal(str(api_product.get('price_net') or 0)),
        'price_gross': Decimal(str(api_product.get('price_gross') or 0)),
        'price_old': Decimal(str(api_product.get('price_old') or 0)),
        'price_kind': int(api_product.get('price_kind') or 1),
        'vat_label': str(api_product.get('vat') or '23%')[:20],
        'vat_id': int(api_product.get('vat_id') or 1),
        'vat_value': Decimal(str(api_product.get('vat_value') or 23)),
        'store_total': store_total,
        'unit_label': str(api_product.get('unit') or 'szt')[:50],
        'unit_id': int(api_product.get('unit_id') or 1),
        'weight': Decimal(str(api_product.get('weight') or 0)),
        'status_label': str(api_product.get('status') or '')[:50],
        'status_id': int(api_product.get('status_id') or 1),
        'status_auto': bool(api_product.get('status_auto') in (True, 1, '1', 'true')),
        'url': str(api_product.get('url') or 'https://tabu.com.pl/')[:1000],
        'version_signature': str(api_product.get('version_signature') or '')[:100],
        'preorder': str(api_product.get('preorder') or '')[:50],
        'hidden_search': bool(api_product.get('hidden_search') in (True, 1)),
        'last_update': last_update or timezone.now(),
        'raw_data': api_product,
    }


def map_api_variant_to_model(api_variant, product):
    """Mapuj wariant z API na dict do TabuProductVariant"""
    items = api_variant.get('items') or []
    color, size = _extract_color_size(items)

    return {
        'api_id': int(api_variant['id']),
        'product': product,
        'symbol': str(api_variant.get('symbol') or '')[:120],
        'ean': str(api_variant.get('ean') or '')[:50],
        'price_net': Decimal(str(api_variant.get('price_net') or 0)),
        'price_gross': Decimal(str(api_variant.get('price_gross') or 0)),
        'price_kind': int(api_variant.get('price_kind') or 1),
        'vat_label': str(api_variant.get('vat') or '23%')[:20],
        'vat_id': int(api_variant.get('vat_id') or 1),
        'vat_value': Decimal(str(api_variant.get('vat_value') or 23)),
        'store': int(api_variant.get('store') or 0),
        'weight': Decimal(str(api_variant.get('weight') or 0)),
        'color': color[:100],
        'size': size[:50],
        'items': items,
        'raw_data': api_variant,
    }


class Command(BaseTabuAPICommand):
    """Pełny import lub aktualizacja produktów z API Tabu"""

    help = 'Importuje/synchronizuje produkty z API Tabu do bazy zzz_tabu'

    def add_arguments(self, parser):
        self.add_common_arguments(parser)
        parser.add_argument(
            '--update-from',
            type=str,
            help='Data od (YYYY-MM-DD lub YYYY-MM-DD HH:MM:SS) - tylko produkty zaktualizowane po tej dacie',
            default=None,
        )
        parser.add_argument(
            '--update-to',
            type=str,
            help='Data do - filtrowanie update_to',
            default=None,
        )
        parser.add_argument(
            '--path',
            type=str,
            default='products',
            help='Ścieżka API (domyślnie: products, dla szczegółów: products/details)',
        )

    def handle(self, *args, **options):
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        update_from = options.get('update_from')
        update_to = options.get('update_to')
        path = options.get('path', 'products')
        limit = min(options.get('limit', 100), 1000)
        batch_size = options.get('batch_size', 50)
        dry_run = options.get('dry_run', False)

        sync_type = 'products_update' if update_from else 'products_full_import'
        if not dry_run:
            self.create_sync_log(sync_type)

        try:
            self.stdout.write('Pobieranie produktów z API Tabu...')
            products_data = self.fetch_paginated_products(
                path=path,
                limit=limit,
                update_from=update_from,
                update_to=update_to,
            )

            if not products_data:
                self.stdout.write('Brak produktów do importu')
                if not dry_run:
                    self.complete_sync_log('completed')
                return

            self.stdout.write(f'Pobrano {len(products_data)} produktów')

            success_count = 0
            fail_count = 0
            processed = 0

            for i in range(0, len(products_data), batch_size):
                batch = products_data[i:i + batch_size]
                self.stdout.write(
                    f'Przetwarzanie batch {i // batch_size + 1}/{(len(products_data) + batch_size - 1) // batch_size}...'
                )

                if not dry_run:
                    db = router.db_for_write(TabuProduct)
                    with transaction.atomic(using=db):
                        for api_product in batch:
                            try:
                                self._save_product(api_product)
                                success_count += 1
                            except Exception as e:
                                fail_count += 1
                                logger.error(
                                    f'Błąd produktu {api_product.get("id")}: {e}'
                                )
                    processed += len(batch)
                    if not dry_run:
                        self.update_sync_log(
                            products_processed=processed,
                            products_success=success_count,
                            products_failed=fail_count,
                        )

            if not dry_run:
                status = 'completed' if fail_count == 0 else 'completed'
                self.complete_sync_log(status)

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Zakończono! Przetworzono: {processed}, '
                    f'sukces: {success_count}, błędy: {fail_count}'
                )
            )

        except Exception as e:
            logger.exception(f'Błąd synchronizacji Tabu: {e}')
            if not dry_run and self.sync_log:
                self.complete_sync_log('failed', str(e))
            raise

    def _save_product(self, api_product):
        """Zapisz produkt i warianty do bazy"""
        product_data = map_api_product_to_model(api_product)
        api_id = product_data.pop('api_id')
        raw_data = product_data.pop('raw_data')
        variants_data = raw_data.get('variants') or []

        product, created = TabuProduct.objects.update_or_create(
            api_id=api_id,
            defaults={**product_data, 'raw_data': raw_data},
        )

        for api_variant in variants_data:
            variant_data = map_api_variant_to_model(api_variant, product)
            v_api_id = variant_data.pop('api_id')
            TabuProductVariant.objects.update_or_create(
                api_id=v_api_id,
                defaults=variant_data,
            )
