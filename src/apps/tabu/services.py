"""
Serwis tworzenia produktu MPD z danych Tabu.
Używany przez admin (mpd_create) i przez automatyzację web_agent.
"""
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction

logger = logging.getLogger(__name__)


def create_mpd_product_from_tabu(
    tabu_product_id: int,
    form_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tworzy produkt w MPD na podstawie produktu Tabu.

    Args:
        tabu_product_id: ID produktu w Tabu (TabuProduct.pk).
        form_data: Opcjonalne dane z formularza (jak request.POST).
                    Klucze: mpd_name, mpd_short_description, mpd_description,
                    mpd_brand, series_name, unit_id, main_color_id,
                    producer_color_name, producer_code,
                    mpd_paths (lista id), mpd_attributes (lista id),
                    fabric_component (lista), fabric_percentage (lista).
                    Gdy None – używane są wyłącznie dane z Tabu.

    Returns:
        Dict z kluczami: success (bool), mpd_product_id (int|None), error_message (str|None).
    """
    form_data = form_data or {}

    def _post(key: str, default: str = '') -> str:
        val = form_data.get(key, default)
        return (val or '') if val is not None else ''

    def _post_list(key: str) -> list:
        val = form_data.get(key)
        if isinstance(val, list):
            return val
        if val is None:
            return []
        return [val]

    try:
        from tabu.models import TabuProduct
        from MPD.models import (
            Products,
            Brands,
            ProductVariants,
            Colors,
            Sizes,
            Sources,
            ProductPaths,
            ProductAttribute,
            ProductFabric,
            ProductSeries,
            ProductvariantsSources,
            StockAndPrices,
            ProductImage,
        )
        from core.db_routers import _get_mpd_db
        from django.utils import timezone

        mpd_db = _get_mpd_db()

        try:
            tabu_product = TabuProduct.objects.select_related('brand').get(pk=tabu_product_id)
        except TabuProduct.DoesNotExist:
            return {
                'success': False,
                'mpd_product_id': None,
                'error_message': 'Produkt Tabu nie istnieje',
            }

        if tabu_product.mapped_product_uid:
            return {
                'success': False,
                'mpd_product_id': None,
                'error_message': 'Produkt jest już zmapowany do MPD',
            }

        name = _post('mpd_name') or tabu_product.name or 'Produkt z Tabu'
        short_desc = _post('mpd_short_description') or (tabu_product.desc_short or '')
        description = _post('mpd_description') or (tabu_product.desc_long or '')

        brand_id = None
        brand_name = _post('mpd_brand') or (tabu_product.brand.name if tabu_product.brand else '')
        if brand_name:
            brand_name = brand_name.strip()[:255]
            brand = Brands.objects.using(mpd_db).filter(name=brand_name).first()
            if not brand:
                brand = Brands.objects.using(mpd_db).create(name=brand_name)
            brand_id = brand.id

        series_id = None
        series_name = _post('series_name').strip()
        if series_name:
            series, _ = ProductSeries.objects.using(mpd_db).get_or_create(
                name=series_name[:255],
                defaults={'name': series_name[:255]},
            )
            series_id = series.id

        unit_id = None
        unit_val = form_data.get('unit_id')
        if unit_val is not None and str(unit_val).isdigit():
            unit_id = int(unit_val)

        with transaction.atomic(using=mpd_db):
            mpd_product = Products.objects.using(mpd_db).create(
                name=name[:255],
                description=description,
                short_description=short_desc[:500],
                brand_id=brand_id,
                series_id=series_id,
                unit_id=unit_id,
                visibility=False,
            )

            for path_id in _post_list('mpd_paths'):
                if str(path_id).isdigit():
                    ProductPaths.objects.using(mpd_db).get_or_create(
                        product_id=mpd_product.id,
                        path_id=int(path_id),
                        defaults={'product_id': mpd_product.id, 'path_id': int(path_id)},
                    )

            for attr_id in _post_list('mpd_attributes'):
                if str(attr_id).isdigit():
                    ProductAttribute.objects.using(mpd_db).get_or_create(
                        product=mpd_product,
                        attribute_id=int(attr_id),
                        defaults={'product': mpd_product, 'attribute_id': int(attr_id)},
                    )

            fabric_ids = _post_list('fabric_component')
            fabric_pcts = _post_list('fabric_percentage')
            for comp_id, pct in zip(fabric_ids, fabric_pcts):
                if comp_id and pct and str(comp_id).isdigit() and str(pct).isdigit():
                    pct_val = int(pct)
                    if 0 < pct_val <= 100:
                        ProductFabric.objects.using(mpd_db).update_or_create(
                            product=mpd_product,
                            component_id=int(comp_id),
                            defaults={'percentage': pct_val},
                        )

            main_color_id = form_data.get('main_color_id')
            producer_color_name = _post('producer_color_name').strip()
            _ = _post('producer_code')  # producer_code w form_data nie zmienia logiki

            main_color = None
            if main_color_id is not None and str(main_color_id).isdigit():
                try:
                    main_color = Colors.objects.using(mpd_db).get(id=int(main_color_id))
                except Colors.DoesNotExist:
                    pass

            producer_color = None
            if producer_color_name:
                producer_color, _ = Colors.objects.using(mpd_db).get_or_create(
                    name=producer_color_name[:50],
                    defaults={'name': producer_color_name[:50]},
                )

            tabu_source, _ = Sources.objects.using(mpd_db).get_or_create(
                name='Tabu API',
                defaults={'type': 'api', 'location': 'https://b2b.tabu.com.pl'},
            )

            variants = tabu_product.api_variants.all()
            for v in variants:
                color_obj = main_color if main_color else None
                if not color_obj and v.color:
                    color_obj, _ = Colors.objects.using(mpd_db).get_or_create(
                        name=v.color[:50],
                        defaults={'name': v.color[:50]},
                    )
                size_obj = None
                if v.size:
                    # Używamy tylko istniejącego rozmiaru (Sizes w MPD może mieć wymagane pole category)
                    size_obj = Sizes.objects.using(mpd_db).filter(name=v.size[:255]).first()

                pv = ProductVariants.objects.using(mpd_db).create(
                    product=mpd_product,
                    color=color_obj,
                    producer_color=producer_color,
                    size=size_obj,
                    iai_product_id=v.api_id,
                )

                ProductvariantsSources.objects.using(mpd_db).get_or_create(
                    variant=pv,
                    source=tabu_source,
                    defaults={
                        'ean': (v.ean or '')[:50],
                        'variant_uid': v.api_id,
                        'producer_code': (v.symbol or '').strip()[:255] or None,
                    },
                )

                stock_val = v.store if v.store is not None else 0
                StockAndPrices.objects.using(mpd_db).get_or_create(
                    variant=pv,
                    source=tabu_source,
                    defaults={
                        'stock': stock_val,
                        'price': v.price_net or Decimal('0'),
                        'currency': 'PLN',
                        'last_updated': timezone.now(),
                    },
                )

                v.mapped_variant_uid = pv.variant_id
                v.is_mapped = True
                v.save(update_fields=['mapped_variant_uid', 'is_mapped'])

            if not variants:
                pv = ProductVariants.objects.using(mpd_db).create(
                    product=mpd_product,
                    color=main_color,
                    producer_color=producer_color,
                    iai_product_id=tabu_product.api_id,
                )
                ProductvariantsSources.objects.using(mpd_db).get_or_create(
                    variant=pv,
                    source=tabu_source,
                    defaults={
                        'ean': (tabu_product.ean or '')[:50],
                        'producer_code': (tabu_product.symbol or '').strip()[:255] or None,
                    },
                )
                StockAndPrices.objects.using(mpd_db).get_or_create(
                    variant=pv,
                    source=tabu_source,
                    defaults={
                        'stock': tabu_product.store_total or 0,
                        'price': tabu_product.price_net or Decimal('0'),
                        'currency': 'PLN',
                        'last_updated': timezone.now(),
                    },
                )

            upload_images = bool(form_data.get('upload_images') if form_data else False)
            if upload_images:
                try:
                    from matterhorn1.defs_db import upload_image_to_bucket_and_get_url
                    images_to_upload = []
                    if tabu_product.image_url and tabu_product.image_url.strip():
                        images_to_upload.append((tabu_product.image_url.strip(), 1))
                    seen_urls = {u for u, _ in images_to_upload}
                    for img in tabu_product.gallery_images.order_by('order', 'api_image_id'):
                        if img.image_url and img.image_url.strip() and img.image_url.strip() not in seen_urls:
                            images_to_upload.append((img.image_url.strip(), len(images_to_upload) + 1))
                            seen_urls.add(img.image_url.strip())
                    for _idx, (img_url, order_num) in enumerate(images_to_upload, 1):
                        bucket_key = upload_image_to_bucket_and_get_url(
                            image_path=img_url,
                            product_id=mpd_product.id,
                            producer_color_name=producer_color_name or '',
                            image_number=order_num,
                        )
                        if bucket_key:
                            ProductImage.objects.using(mpd_db).get_or_create(
                                product=mpd_product,
                                file_path=bucket_key,
                                defaults={'product': mpd_product, 'file_path': bucket_key},
                            )
                except Exception as img_err:
                    logger.warning("Błąd uploadu zdjęć Tabu→MPD: %s", img_err)

            tabu_product.mapped_product_uid = mpd_product.id
            tabu_product.save(update_fields=['mapped_product_uid'])

        logger.info("Utworzono produkt MPD %s z Tabu produktu %s", mpd_product.id, tabu_product_id)
        return {
            'success': True,
            'mpd_product_id': mpd_product.id,
            'error_message': None,
        }

    except Exception as e:
        logger.exception("Błąd tworzenia produktu MPD z Tabu %s: %s", tabu_product_id, e)
        return {
            'success': False,
            'mpd_product_id': None,
            'error_message': str(e),
        }
