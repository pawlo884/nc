"""
Logika importu sparsowanych danych Mada do bazy - współdzielona między
management commands `sync_mada_full` i `sync_mada_partial`.
"""
import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Tuple

from django.utils import timezone

from .models import Brand, Category, MadaProduct, MadaProductImage, MadaProductVariant
from .stock_tracker import track_stock_change

logger = logging.getLogger(__name__)


def _to_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def sync_brands(db: str, producers: Dict[str, str]) -> int:
    """Upsert Brand z dict producer_id -> name. Zwraca liczbę utworzonych/zaktualizowanych."""
    if not producers:
        return 0
    existing = {
        b.producer_id: b
        for b in Brand.objects.using(db).filter(producer_id__in=producers.keys())
    }
    to_create = []
    to_update = []
    for producer_id, name in producers.items():
        brand = existing.get(producer_id)
        if brand is None:
            to_create.append(Brand(producer_id=producer_id, name=name))
        elif brand.name != name:
            brand.name = name
            to_update.append(brand)
    if to_create:
        Brand.objects.using(db).bulk_create(to_create, batch_size=500, ignore_conflicts=True)
    if to_update:
        Brand.objects.using(db).bulk_update(to_update, ['name', 'updated_at'], batch_size=500)
    return len(to_create) + len(to_update)


def resolve_category(db: str, categories: list, category_cache: dict) -> Optional[Category]:
    """Zwraca (tworząc w razie potrzeby) Category dla pierwszej pozycji z listy
    CATEGORY produktu ({'c1', 'c2', 'name'}) - w feedzie produkt ma zwykle jedną
    kategorię. `category_cache` żyje w obrębie jednego przebiegu importu (nie
    globalnie), żeby uniknąć nieaktualnych danych między osobnymi taskami."""
    if not categories:
        return None
    cat = categories[0]
    c1, c2, name = cat.get('c1'), cat.get('c2'), cat.get('name') or ''
    if not c1 or not c2:
        return None
    category_id = f'{c1}-{c2}'

    cached = category_cache.get(category_id)
    if cached is not None:
        return cached

    parent = None
    if c1 != c2:
        parent_name = name.split('/')[0].strip() if '/' in name else name
        parent = category_cache.get(str(c1))
        if parent is None:
            parent, _ = Category.objects.using(db).get_or_create(
                category_id=str(c1), defaults={'name': parent_name},
            )
            category_cache[str(c1)] = parent

    category, created = Category.objects.using(db).get_or_create(
        category_id=category_id,
        defaults={'name': name, 'path': name, 'parent': parent},
    )
    if not created and (category.name != name or category.parent_id != (parent.id if parent else None)):
        category.name = name
        category.path = name
        category.parent = parent
        category.save(using=db, update_fields=['name', 'path', 'parent', 'updated_at'])

    category_cache[category_id] = category
    return category


def upsert_product(db: str, product_dict: dict, category_cache: dict) -> Tuple[MadaProduct, bool]:
    api_id = product_dict['api_id']
    brand = None
    producer_id = product_dict.get('producer_id')
    if producer_id:
        brand = Brand.objects.using(db).filter(producer_id=producer_id).first()
    category = resolve_category(db, product_dict.get('categories') or [], category_cache)

    defaults = {
        'name': product_dict.get('name') or '',
        'desc': product_dict.get('desc') or '',
        'brand': brand,
        'category': category,
        'price': _to_decimal(product_dict.get('price')) or Decimal('0'),
        'old_price': _to_decimal(product_dict.get('old_price')),
        'vat': _to_decimal(product_dict.get('vat')) or Decimal('23'),
        'raw_data': product_dict.get('raw_data') or {},
        'is_active': True,
        'last_api_sync': timezone.now(),
    }
    product, created = MadaProduct.objects.using(db).update_or_create(
        api_id=api_id, defaults=defaults,
    )
    return product, created


def upsert_variants(db: str, product: MadaProduct, variants: list) -> int:
    """Upsert wariantów produktu, zapisując zmiany stanu do StockHistory. Zwraca
    liczbę utworzonych/zmienionych wariantów."""
    existing = {
        v.variant_key: v
        for v in MadaProductVariant.objects.using(db).filter(product=product)
    }
    changed = 0
    for v in variants:
        key = v['variant_key']
        label = f"{v['color']}/{v['size']}"
        current = existing.get(key)
        if current is None:
            # Feed Mada bywa "brudny": ten sam variant_key (zwykle EAN) potrafi
            # pojawić się dwukrotnie w obrębie jednego produktu - zapisujemy
            # utworzony obiekt do `existing`, żeby drugie wystąpienie trafiło
            # w gałąź update, a nie w drugi create() (naruszenie unique_together).
            current = MadaProductVariant.objects.using(db).create(
                product=product, variant_key=key, color=v['color'], size=v['size'],
                ean=v['ean'], stock=v['stock'],
            )
            existing[key] = current
            track_stock_change(
                product_api_id=product.api_id, variant_key=key,
                old_stock=0, new_stock=v['stock'],
                product_name=product.name, variant_label=label,
            )
            changed += 1
            continue

        fields_changed = []
        if current.stock != v['stock']:
            track_stock_change(
                product_api_id=product.api_id, variant_key=key,
                old_stock=current.stock, new_stock=v['stock'],
                product_name=product.name, variant_label=label,
            )
            current.stock = v['stock']
            fields_changed.append('stock')
        if current.color != v['color']:
            current.color = v['color']
            fields_changed.append('color')
        if current.size != v['size']:
            current.size = v['size']
            fields_changed.append('size')
        if current.ean != v['ean']:
            current.ean = v['ean']
            fields_changed.append('ean')
        if fields_changed:
            fields_changed.append('updated_at')
            current.save(using=db, update_fields=fields_changed)
            changed += 1
    return changed


def upsert_images(db: str, product: MadaProduct, images: list) -> None:
    existing_ids = set(
        MadaProductImage.objects.using(db).filter(product=product).values_list('api_image_id', flat=True)
    )
    new_ids = {img['api_image_id'] for img in images}
    to_create = [
        MadaProductImage(
            product=product, api_image_id=img['api_image_id'],
            image_url=img['url'], order=img['order'],
        )
        for img in images if img['api_image_id'] not in existing_ids
    ]
    if to_create:
        MadaProductImage.objects.using(db).bulk_create(to_create, batch_size=200, ignore_conflicts=True)
    stale_ids = existing_ids - new_ids
    if stale_ids:
        MadaProductImage.objects.using(db).filter(product=product, api_image_id__in=stale_ids).delete()


def import_product_dict(db: str, product_dict: dict, category_cache: dict) -> bool:
    """Importuje jeden produkt (+ warianty, + zdjęcia). Zwraca True gdy produkt był nowy."""
    product, created = upsert_product(db, product_dict, category_cache)
    upsert_variants(db, product, product_dict.get('variants') or [])
    upsert_images(db, product, product_dict.get('images') or [])
    return created
