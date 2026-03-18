"""
Serwis tworzenia produktu MPD z danych Tabu.
Używany przez admin (mpd_create) i przez automatyzację web_agent.

Flow oparty o Saga (dwie bazy: MPD + Tabu) z kompensacją przy błędzie.
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from .saga import SagaStatus, TabuSagaOrchestrator

logger = logging.getLogger(__name__)


def _saga_create_mpd_tabu(
    tabu_product_id: int,
    form_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Krok 1 Sagi: utworzenie produktu i wariantów w MPD (bez zapisu w Tabu).
    Zwraca mpd_product_id i variant_mapping do użycia w kroku 2.
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
    tabu_product = TabuProduct.objects.select_related('brand').get(pk=tabu_product_id)

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
            brand_id=brand_id,
            name=series_name[:255],
            defaults={'name': series_name[:255], 'brand_id': brand_id},
        )
        series_id = series.id

    unit_id = None
    unit_val = form_data.get('unit_id')
    if unit_val is not None and str(unit_val).isdigit():
        unit_id = int(unit_val)

    variant_mapping: List[Tuple[int, int]] = []  # (tabu_variant_pk, mpd_variant_id)

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

        variants = list(tabu_product.api_variants.all())
        for v in variants:
            color_obj = main_color if main_color else None
            if not color_obj and v.color:
                color_obj, _ = Colors.objects.using(mpd_db).get_or_create(
                    name=v.color[:50],
                    defaults={'name': v.color[:50]},
                )
            size_obj = None
            if v.size:
                size_obj = Sizes.objects.using(mpd_db).filter(name=v.size[:255]).first()

            pv = ProductVariants.objects.using(mpd_db).create(
                product=mpd_product,
                color=color_obj,
                producer_color=producer_color,
                size=size_obj,
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
            variant_mapping.append((v.pk, pv.variant_id))

        if not variants:
            pv = ProductVariants.objects.using(mpd_db).create(
                product=mpd_product,
                color=main_color,
                producer_color=producer_color,
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

        upload_images = bool(form_data.get('upload_images'))
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

    return {'mpd_product_id': mpd_product.id, 'variant_mapping': variant_mapping}


def _saga_delete_mpd_tabu(mpd_product_id: Optional[int] = None, **kwargs: Any) -> None:
    """Kompensacja kroku 1: usuń produkt z MPD (CASCADE usuwa warianty, PVS, itd.)."""
    if not mpd_product_id:
        return
    from MPD.models import Products
    from core.db_routers import _get_mpd_db
    mpd_db = _get_mpd_db()
    deleted, _ = Products.objects.using(mpd_db).filter(id=mpd_product_id).delete()
    if deleted:
        logger.info("Saga kompensacja: usunięto produkt MPD id=%s", mpd_product_id)


def _saga_update_tabu_mapping(
    tabu_product_id: int,
    mpd_product_id: Optional[int] = None,
    variant_mapping: Optional[List[Tuple[int, int]]] = None,
    **kwargs: Any,
) -> None:
    """Krok 2 Sagi: zapisz mapowanie produktu i wariantów w Tabu."""
    from tabu.models import TabuProduct, TabuProductVariant
    if mpd_product_id is not None:
        TabuProduct.objects.filter(pk=tabu_product_id).update(mapped_product_uid=mpd_product_id)
    variant_mapping = variant_mapping or []
    for tabu_variant_pk, mpd_variant_id in variant_mapping:
        TabuProductVariant.objects.filter(pk=tabu_variant_pk).update(
            mapped_variant_uid=mpd_variant_id,
            is_mapped=True,
        )


def _saga_clear_tabu_mapping(tabu_product_id: int, **kwargs: Any) -> None:
    """Kompensacja kroku 2: wyzeruj mapowanie w Tabu."""
    from tabu.models import TabuProduct, TabuProductVariant
    TabuProduct.objects.filter(pk=tabu_product_id).update(mapped_product_uid=None)
    TabuProductVariant.objects.filter(product_id=tabu_product_id).update(
        mapped_variant_uid=None,
        is_mapped=False,
    )
    logger.info("Saga kompensacja: wyzerowano mapowanie Tabu product id=%s", tabu_product_id)


def create_mpd_product_from_tabu(
    tabu_product_id: int,
    form_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tworzy produkt w MPD na podstawie produktu Tabu (Saga: MPD + Tabu, z kompensacją).

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

    try:
        from tabu.models import TabuProduct

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

        saga = TabuSagaOrchestrator()
        saga.add_step(
            name='create_mpd',
            execute_func=_saga_create_mpd_tabu,
            compensate_func=_saga_delete_mpd_tabu,
            data={'tabu_product_id': tabu_product_id, 'form_data': form_data},
        )
        saga.add_step(
            name='update_tabu_mapping',
            execute_func=_saga_update_tabu_mapping,
            compensate_func=_saga_clear_tabu_mapping,
            data={
                'tabu_product_id': tabu_product_id,
                'mpd_product_id': None,
                'variant_mapping': None,
            },
        )
        result = saga.execute()

        if result.status == SagaStatus.COMPLETED:
            mpd_product_id = result.steps[0].result.get('mpd_product_id') if result.steps else None
            logger.info("Utworzono produkt MPD %s z Tabu produktu %s (Saga)", mpd_product_id, tabu_product_id)
            return {
                'success': True,
                'mpd_product_id': mpd_product_id,
                'error_message': None,
            }

        return {
            'success': False,
            'mpd_product_id': None,
            'error_message': result.error or 'Saga zakończona kompensacją',
        }

    except Exception as e:
        logger.exception("Błąd tworzenia produktu MPD z Tabu %s: %s", tabu_product_id, e)
        return {
            'success': False,
            'mpd_product_id': None,
            'error_message': str(e),
        }


def create_mpd_variants_from_tabu(
    mpd_product_id: int,
    tabu_product_id: int,
    size_category: str,
    producer_code: Optional[str] = None,
    main_color_id: Optional[int] = None,
    producer_color_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tworzy/dopina warianty w MPD z wariantów Tabu (wzór: matterhorn1/saga_variants.create_mpd_variants).
    Dla każdego wariantu Tabu: szuka istniejącego wariantu MPD po EAN (inna hurtownia) lub tworzy nowy,
    dopina ProductvariantsSources + StockAndPrices dla źródła Tabu, ustawia mapped_variant_uid w Tabu.
    """
    from django.db import connections
    from django.utils import timezone
    from tabu.models import TabuProduct, TabuProductVariant
    from MPD.models import (
        Colors,
        ProductVariants,
        ProductvariantsSources,
        Sizes,
        Sources,
        StockAndPrices,
    )
    from MPD.source_adapters.base import normalize_ean
    from core.db_routers import _get_mpd_db

    mpd_db = _get_mpd_db()

    tabu_product = TabuProduct.objects.get(pk=tabu_product_id)
    tabu_variants = list(TabuProductVariant.objects.filter(product_id=tabu_product_id))
    if not tabu_variants:
        logger.warning("Brak wariantów Tabu dla produktu %s", tabu_product_id)
        return {"created_variants": 0, "variant_ids": []}

    # Główny kolor: z formularza (main_color_id) albo z produktu MPD / Tabu
    color_id = None
    producer_color_id = None
    if main_color_id:
        main_color_obj = Colors.objects.using(mpd_db).filter(pk=main_color_id).first()
        if main_color_obj:
            color_id = main_color_obj.id
            logger.info("Użyto głównego koloru z formularza: %s (id=%s)", main_color_obj.name, color_id)

    if color_id is None:
        first_mpd = (
            ProductVariants.objects.using(mpd_db)
            .filter(product_id=mpd_product_id)
            .select_related("color", "producer_color")
            .first()
        )
        tabu_color_name = (tabu_variants[0].color or (tabu_product.brand.name if tabu_product.brand else "Brak koloru")).strip() or "Brak koloru"
        tabu_producer_name = (producer_color_name or "").strip()[:50] if producer_color_name else ""
        if first_mpd and first_mpd.color and (first_mpd.color.name or "").strip() == tabu_color_name:
            if tabu_producer_name:
                if first_mpd.producer_color and (first_mpd.producer_color.name or "").strip() == tabu_producer_name:
                    color_id = first_mpd.color_id
                    producer_color_id = first_mpd.producer_color_id
                    logger.info("Ten sam kolor i kolor producenta – dopisuję tylko warianty (color_id=%s, producer_color_id=%s)", color_id, producer_color_id)
            else:
                color_id = first_mpd.color_id
                producer_color_id = first_mpd.producer_color_id
                logger.info("Ten sam kolor – dopisuję tylko warianty (color_id=%s)", color_id)

    if color_id is None:
        tabu_color_name = (tabu_variants[0].color or (tabu_product.brand.name if tabu_product.brand else "Brak koloru")).strip() or "Brak koloru"
        color = Colors.objects.using(mpd_db).filter(name=tabu_color_name).first()
        if not color:
            color = Colors.objects.using(mpd_db).create(name=tabu_color_name)
        color_id = color.id

    if producer_color_id is None and producer_color_name:
        name_key = producer_color_name.strip()[:50]
        defaults = {"hex_code": ""}
        if main_color_id:
            parent_color = Colors.objects.using(mpd_db).filter(pk=main_color_id).first()
            if parent_color:
                defaults["parent_id"] = parent_color
        producer_color, _ = Colors.objects.using(mpd_db).get_or_create(
            name=name_key,
            defaults=defaults,
        )
        producer_color_id = producer_color.id

    tabu_source = Sources.objects.using(mpd_db).filter(name__icontains="Tabu").first()
    if not tabu_source:
        tabu_source = Sources.objects.using(mpd_db).create(
            name="Tabu API", type="api", location="https://b2b.tabu.com.pl"
        )

    producer_code_val = (producer_code or getattr(tabu_product, "symbol", None) or "").strip()[:255] or None
    created_count = 0
    variant_ids = []

    for tabu_var in tabu_variants:
        size_name = (tabu_var.size or "").strip()
        ean_raw = (tabu_var.ean or "").strip()
        ean_norm = normalize_ean(tabu_var.ean)
        variant_uid_int = tabu_var.api_id

        size = (
            Sizes.objects.using(mpd_db)
            .filter(name__iexact=size_name, category=size_category)
            .first()
        )
        if not size and size_name:
            # Ten sam produkt – brakujący rozmiar dopisz w tej samej kategorii co produkt MPD
            size, _ = Sizes.objects.using(mpd_db).get_or_create(
                name=size_name[:255],
                category=size_category,
                defaults={
                    "name_lower": size_name.lower()[:255] if size_name else "",
                    "unit": "",
                },
            )
            logger.info("Dodano rozmiar w MPD: %s (kategoria %s)", size_name, size_category)
        if not size:
            logger.warning("Rozmiar %s nie znaleziony w kategorii %s – pomijam wariant", size_name, size_category)
            continue

        if ProductvariantsSources.objects.using(mpd_db).filter(
            variant_uid=variant_uid_int, source=tabu_source
        ).exists():
            logger.info("Wariant Tabu api_id=%s już istnieje w MPD - pomijam", variant_uid_int)
            continue

        variant = None
        if ean_norm:
            for pvs in (
                ProductvariantsSources.objects.using(mpd_db)
                .filter(variant__product_id=mpd_product_id)
                .exclude(source=tabu_source)
                .select_related("variant")
            ):
                if normalize_ean(pvs.ean) == ean_norm:
                    variant = pvs.variant
                    logger.info(
                        "Znaleziono wariant MPD po EAN %s (variant_id=%s) - dopinam Tabu",
                        ean_norm, variant.variant_id,
                    )
                    break

        if variant is None:
            variant = ProductVariants.objects.using(mpd_db).create(
                product_id=mpd_product_id,
                color_id=color_id,
                producer_color_id=producer_color_id,
                size=size,
            )
            logger.info("Utworzono wariant MPD %s dla Tabu api_id=%s", variant.variant_id, tabu_var.api_id)

        ProductvariantsSources.objects.using(mpd_db).get_or_create(
            variant=variant,
            source=tabu_source,
            defaults={
                "ean": (ean_raw or "")[:50] if ean_raw else "",
                "variant_uid": variant_uid_int,
                "producer_code": (tabu_var.symbol or producer_code_val or "").strip()[:255] or None,
            },
        )
        StockAndPrices.objects.using(mpd_db).get_or_create(
            variant=variant,
            source=tabu_source,
            defaults={
                "stock": tabu_var.store if tabu_var.store is not None else 0,
                "price": tabu_var.price_net or Decimal("0"),
                "currency": "PLN",
                "last_updated": timezone.now(),
            },
        )
        TabuProductVariant.objects.filter(pk=tabu_var.pk).update(
            mapped_variant_uid=variant.variant_id,
            is_mapped=True,
        )
        variant_ids.append(variant.variant_id)
        created_count += 1

    if created_count > 0:
        from MPD.tasks import link_variants_from_other_sources_task
        link_variants_from_other_sources_task.apply_async(
            args=(mpd_product_id, tabu_source.id),
            queue="default",
        )
        logger.info(
            "Wysłano task linkowania po EAN dla produktu MPD %s (source %s)",
            mpd_product_id, tabu_source.id,
        )

    return {"created_variants": created_count, "variant_ids": variant_ids}


def upload_tabu_images_to_mpd(
    mpd_product_id: int,
    tabu_product_id: int,
    producer_color_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Upload zdjęć produktu Tabu do bucketa i zapis do MPD (jak Matterhorn1 _upload_product_images).
    Zwraca dict z kluczami: uploaded_images (int), images (lista), upload_error (str, opcjonalnie).
    """
    try:
        from tabu.models import TabuProduct
        from MPD.models import Products, ProductImage
        from core.db_routers import _get_mpd_db
        from matterhorn1.defs_db import upload_image_to_bucket_and_get_url

        mpd_db = _get_mpd_db()
        tabu_product = TabuProduct.objects.get(pk=tabu_product_id)
        images_to_upload = []
        if tabu_product.image_url and tabu_product.image_url.strip():
            images_to_upload.append((tabu_product.image_url.strip(), 1))
        seen = {u for u, _ in images_to_upload}
        for img in tabu_product.gallery_images.order_by("order", "api_image_id"):
            if img.image_url and img.image_url.strip() and img.image_url.strip() not in seen:
                images_to_upload.append((img.image_url.strip(), len(images_to_upload) + 1))
                seen.add(img.image_url.strip())

        if not images_to_upload:
            logger.info("Brak zdjęć Tabu do uploadu dla produktu %s", tabu_product_id)
            return {"uploaded_images": 0, "images": []}

        mpd_product = Products.objects.using(mpd_db).get(pk=mpd_product_id)
        producer_color = (producer_color_name or "").strip()
        uploaded_count = 0
        uploaded_images = []
        for idx, (img_url, order_num) in enumerate(images_to_upload, 1):
            bucket_key = upload_image_to_bucket_and_get_url(
                image_path=img_url,
                product_id=mpd_product_id,
                producer_color_name=producer_color,
                image_number=order_num,
            )
            if bucket_key:
                ProductImage.objects.using(mpd_db).get_or_create(
                    product=mpd_product,
                    file_path=bucket_key,
                    defaults={"product": mpd_product, "file_path": bucket_key},
                )
                uploaded_count += 1
                uploaded_images.append({"original_url": img_url, "storage_key": bucket_key, "order": order_num})
                logger.info("Uploadowano zdjęcie Tabu %s -> MPD %s (nr %s)", tabu_product_id, mpd_product_id, order_num)

        logger.info("Uploadowano %s zdjęć Tabu do MPD produktu %s", uploaded_count, mpd_product_id)
        return {"uploaded_images": uploaded_count, "images": uploaded_images}
    except Exception as e:
        logger.exception("Błąd uploadu zdjęć Tabu→MPD: %s", e)
        return {"uploaded_images": 0, "images": [], "upload_error": str(e)}
