"""
Komenda do synchronizacji produktów z API Tabu.
Pobiera produkty POJEDYNCZO (GET products/{id}) – pełne dane: gallery, desc_long, dictionaries.
Użycie:
  python manage.py sync_tabu_products --settings=core.settings.dev
  python manage.py sync_tabu_products --update-from 2026-01-01 --settings=core.settings.dev
  python manage.py sync_tabu_products --max-products 20 --settings=core.settings.dev
"""
import logging
import time
from datetime import datetime
from decimal import Decimal

from django.db import router, transaction
from django.utils import timezone

from tabu.models import Brand, Category, TabuProduct, TabuProductImage, TabuProductVariant

from .base_tabu_api_command import BaseTabuAPICommand

logger = logging.getLogger(__name__)


def parse_datetime(value):
    """Parsuj datę z API (format: '2026-01-20 12:29:24') - zwraca timezone-aware"""
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.strptime(str(value)[:19], '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return None
    return timezone.make_aware(dt) if dt.tzinfo is None else dt


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
    Mapuj pełną odpowiedź GET products/{id} na dict do TabuProduct.
    Zawiera: desc_long, desc_safety, groups, dictionaries, stores, gallery.
    """
    variants = api_product.get('variants') or []
    store_total = sum(int(v.get('store') or 0) for v in variants)
    last_update = parse_datetime(api_product.get('last_update'))

    return {
        'api_id': int(api_product['id']),
        'symbol': str(api_product.get('symbol') or ''),
        'ean': str(api_product.get('ean') or '')[:50],
        'name': str(api_product.get('name') or ''),
        'desc_short': api_product.get('desc_short') or '',
        'desc_long': api_product.get('desc_long') or '',
        'desc_safety': api_product.get('desc_safety') or '',
        'category_path': str(api_product.get('category') or ''),
        'api_category_id': int(api_product.get('category_id') or 0),
        'producer_name': str(api_product.get('producer') or ''),
        'api_producer_id': int(api_product.get('producer_id') or 0),
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
        'shipment': str(api_product.get('shipment') or '')[:200],
        'shipment_id': str(api_product.get('shipment_id') or '')[:50],
        'shipment_days': str(api_product.get('shipment_days') or '')[:50],
        'status_label': str(api_product.get('status') or '')[:50],
        'status_id': int(api_product.get('status_id') or 1),
        'status_auto': bool(api_product.get('status_auto') in (True, 1, '1', 'true')),
        'url': str(api_product.get('url') or 'https://tabu.com.pl/')[:1000],
        'version_signature': str(api_product.get('version_signature') or '')[:100],
        'preorder': str(api_product.get('preorder') or '')[:50],
        'hidden_search': bool(api_product.get('hidden_search') in (True, 1)),
        'last_update': last_update or timezone.now(),
        'groups': api_product.get('groups') or [],
        'dictionaries': api_product.get('dictionaries') or [],
        'stores': api_product.get('stores') or [],
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
        'stores': api_variant.get('stores') or [],
        'raw_data': api_variant,
    }


class Command(BaseTabuAPICommand):
    """Import produktów Tabu – pobiera pojedynczo (GET products/{id}) dla pełnych danych."""

    help = 'Importuje produkty z API Tabu (pobieranie pojedyncze - pełne dane: gallery, opisy, słowniki)'

    def add_arguments(self, parser):
        self.add_common_arguments(parser)
        parser.add_argument(
            '--update-from',
            type=str,
            help='Data od (YYYY-MM-DD) - tylko produkty zaktualizowane po tej dacie',
            default=None,
        )
        parser.add_argument(
            '--update-to',
            type=str,
            help='Data do - filtrowanie update_to',
            default=None,
        )
        parser.add_argument(
            '--max-products',
            type=int,
            default=None,
            help='Maks. liczba produktów (do testów)',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Opóźnienie między requestami (s) - domyślnie 1s (~60 req/min)',
        )

    def handle(self, *args, **options):
        self.setup_logging(options.get('verbose', False))
        self.get_api_credentials(options)

        update_from = options.get('update_from')
        update_to = options.get('update_to')
        max_products = options.get('max_products')
        delay = max(0.7, float(options.get('delay', 1.0)))
        dry_run = options.get('dry_run', False)

        sync_type = 'products_update' if update_from else 'products_full_import'
        if not dry_run:
            self.create_sync_log(sync_type)

        try:
            self.stdout.write('1. Pobieranie listy ID produktów...')
            product_ids = self._fetch_product_ids(update_from, update_to, max_products)
            if not product_ids:
                self.stdout.write('Brak produktów do importu')
                if not dry_run:
                    self.complete_sync_log('completed')
                return

            self.stdout.write(f'   Znaleziono {len(product_ids)} produktów')
            self.stdout.write('2. Pobieranie szczegółów pojedynczo (GET products/{id})...')

            success_count = 0
            fail_count = 0
            for i, api_id in enumerate(product_ids, 1):
                if i % 10 == 0 or i == 1:
                    self.stdout.write(f'   [{i}/{len(product_ids)}] produkt #{api_id}...')

                time.sleep(delay)
                api_product = self._fetch_product_detail(api_id)
                if not api_product:
                    fail_count += 1
                    continue

                if not dry_run:
                    try:
                        db = router.db_for_write(TabuProduct)
                        with transaction.atomic(using=db):
                            self._save_product(api_product)
                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        logger.error(f'Błąd produktu {api_id}: {e}')
                else:
                    success_count += 1

                if not dry_run and self.sync_log and i % 50 == 0:
                    self.update_sync_log(
                        products_processed=i,
                        products_success=success_count,
                        products_failed=fail_count,
                    )

            if not dry_run:
                self.update_sync_log(
                    products_processed=len(product_ids),
                    products_success=success_count,
                    products_failed=fail_count,
                )
                self.complete_sync_log('completed' if fail_count == 0 else 'completed')

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Zakończono! Przetworzono: {len(product_ids)}, '
                    f'sukces: {success_count}, błędy: {fail_count}'
                )
            )

        except Exception as e:
            logger.exception(f'Błąd synchronizacji Tabu: {e}')
            if not dry_run and self.sync_log:
                self.complete_sync_log('failed', str(e))
            raise

    def _fetch_product_ids(self, update_from, update_to, max_products):
        """Pobierz listę ID z GET products (lekkie requesty)."""
        ids = []
        page = 1
        limit = 1000
        while True:
            params = {'page': page, 'limit': limit}
            if update_from:
                params['update_from'] = update_from
            if update_to:
                params['update_to'] = update_to

            data = self.make_api_request('products', params=params)
            products = data.get('products', [])
            if not products:
                break
            for p in products:
                ids.append(int(p['id']))
            total = data.get('total', 0)
            if len(ids) >= total or len(products) < limit:
                break
            if max_products and len(ids) >= max_products:
                ids = ids[:max_products]
                break
            page += 1
            time.sleep(1)
        return ids

    def _fetch_product_detail(self, api_id):
        """Pobierz pełne dane produktu GET products/{id}."""
        try:
            data = self.make_api_request(f'products/{api_id}')
            if isinstance(data, dict) and 'id' in data:
                return data
            return None
        except Exception as e:
            logger.warning(f'Nie udało się pobrać produktu {api_id}: {e}')
            return None

    def _get_or_create_brand(self, producer_id, producer_name):
        if not producer_id and not producer_name:
            return None
        bid = str(producer_id) if producer_id else f"n_{abs(hash(producer_name or '')) % 10**10}"
        brand, _ = Brand.objects.get_or_create(
            brand_id=bid,
            defaults={'name': producer_name or f'Producent {producer_id}'},
        )
        return brand

    def _get_or_create_category(self, category_id, category_path):
        if not category_id and not category_path:
            return None
        cid = str(category_id) if category_id else f"p_{abs(hash(category_path or '')) % 10**10}"
        name = (category_path or '').split(' > ')[-1].strip() or f'Kategoria {category_id}'
        cat, _ = Category.objects.get_or_create(
            category_id=cid,
            defaults={'name': name, 'path': category_path or ''},
        )
        return cat

    def _save_product(self, api_product):
        """Zapisz produkt, gallery, warianty."""
        product_data = map_api_product_to_model(api_product)
        api_id = product_data.pop('api_id')
        raw_data = product_data.pop('raw_data')
        variants_data = raw_data.get('variants') or []
        gallery_data = raw_data.get('gallery') or []

        product_data['brand'] = self._get_or_create_brand(
            product_data.get('api_producer_id'),
            product_data.get('producer_name', ''),
        )
        product_data['category'] = self._get_or_create_category(
            product_data.get('api_category_id'),
            product_data.get('category_path', ''),
        )

        product, _ = TabuProduct.objects.update_or_create(
            api_id=api_id,
            defaults={**product_data, 'raw_data': raw_data},
        )

        # Gallery – zdjęcia (w tym kolory)
        TabuProductImage.objects.filter(product=product).delete()
        for order, img in enumerate(gallery_data):
            TabuProductImage.objects.create(
                product=product,
                api_image_id=int(img.get('id', order)),
                image_url=str(img.get('image', ''))[:1000],
                is_main=bool(img.get('main')),
                order=order,
            )

        # Warianty
        for api_variant in variants_data:
            variant_data = map_api_variant_to_model(api_variant, product)
            v_api_id = variant_data.pop('api_id')
            TabuProductVariant.objects.update_or_create(
                api_id=v_api_id,
                defaults=variant_data,
            )
