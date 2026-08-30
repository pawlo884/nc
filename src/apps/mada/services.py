"""
Serwis tworzenia produktu MPD z danych Mada.
Używany przez admin (mpd_create / assign_mapping).

Flow oparty o Saga (dwie bazy: MPD + Mada) z kompensacją przy błędzie.
Analogiczny do tabu.services / matterhorn1.saga.

Uwaga na różnice modelu Mada:
- wariant Mada nie ma numerycznego id (klucz = variant_key, zwykle EAN) — do
  ProductvariantsSources.variant_uid (PG integer) nic nie zapisujemy;
- cena jest na produkcie (MadaProduct.price), nie na wariancie;
- brak kodu producenta w feedzie — bierzemy tylko z formularza;
- zdjęcia wyłącznie w relacji product.images (brak głównego image_url na produkcie).
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from .saga import SagaStatus, MadaSagaOrchestrator

logger = logging.getLogger(__name__)

_MADA_SOURCE_NAME = 'Mada API'
_MADA_SOURCE_LOCATION = 'https://www.mada.pl'


def _saga_create_mpd_mada(
    mada_product_id: int,
    form_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Krok 1 Sagi: utworzenie produktu i wariantów w MPD (bez zapisu w Mada).
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

    from mada.models import MadaProduct
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
    from core.db_routers import _get_mpd_db, _get_mada_db
    from django.utils import timezone

    mpd_db = _get_mpd_db()
    mada_db = _get_mada_db()
    mada_product = (
        MadaProduct.objects.using(mada_db)
        .select_related('brand')
        .get(pk=mada_product_id)
    )

    name = _post('mpd_name') or mada_product.name or 'Produkt z Mada'
    short_desc = _post('mpd_short_description')
    description = _post('mpd_description') or (mada_product.desc or '')

    brand_id = None
    brand_name = _post('mpd_brand') or (mada_product.brand.name if mada_product.brand else '')
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

    variant_mapping: List[Tuple[int, int]] = []  # (mada_variant_pk, mpd_variant_id)

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
        producer_code = _post('producer_code').strip()[:255] or None
        main_color = None
        if main_color_id is not None and str(main_color_id).isdigit():
            try:
                main_color = Colors.objects.using(mpd_db).get(id=int(main_color_id))
            except Colors.DoesNotExist:
                pass

        producer_color = None
        if producer_color_name:
            # Lookup po samej nazwie (colors.name UNIQUE) – parent_id tylko w defaults,
            # analogicznie do Matterhorn/Tabu (bez colors_name_key crash).
            producer_color, _ = Colors.objects.using(mpd_db).get_or_create(
                name=producer_color_name[:50],
                defaults={'parent_id': main_color.id if main_color else None},
            )

        mada_source, _ = Sources.objects.using(mpd_db).get_or_create(
            name=_MADA_SOURCE_NAME,
            defaults={'type': 'api', 'location': _MADA_SOURCE_LOCATION},
        )

        product_price = mada_product.price or Decimal('0')
        variants = list(mada_product.variants.all())
        for v in variants:
            color_obj = main_color if main_color else None
            if not color_obj and v.color:
                color_obj, _ = Colors.objects.using(mpd_db).get_or_create(
                    name=v.color[:50],
                    defaults={'parent_id': None},
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
                source=mada_source,
                defaults={
                    'ean': (v.ean or '')[:50],
                    'producer_code': producer_code,
                },
            )

            StockAndPrices.objects.using(mpd_db).get_or_create(
                variant=pv,
                source=mada_source,
                defaults={
                    'stock': v.stock if v.stock is not None else 0,
                    'price': product_price,
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
                source=mada_source,
                defaults={'producer_code': producer_code},
            )
            StockAndPrices.objects.using(mpd_db).get_or_create(
                variant=pv,
                source=mada_source,
                defaults={
                    'stock': 0,
                    'price': product_price,
                    'currency': 'PLN',
                    'last_updated': timezone.now(),
                },
            )

        upload_images = bool(form_data.get('upload_images'))
        if upload_images:
            try:
                from matterhorn1.defs_db import upload_image_to_bucket_and_get_url
                images_to_upload = []
                seen_urls = set()
                for img in mada_product.images.order_by('order', 'api_image_id'):
                    url = (img.image_url or '').strip()
                    if url and url not in seen_urls:
                        images_to_upload.append((url, len(images_to_upload) + 1))
                        seen_urls.add(url)
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
                            defaults={'producer_color': producer_color},
                        )
            except Exception as img_err:
                logger.warning("Błąd uploadu zdjęć Mada→MPD: %s", img_err)

    return {'mpd_product_id': mpd_product.id, 'variant_mapping': variant_mapping}


def _saga_delete_mpd_mada(mpd_product_id: Optional[int] = None, **kwargs: Any) -> None:
    """Kompensacja kroku 1: usuń produkt z MPD (CASCADE usuwa warianty, PVS, itd.)."""
    if not mpd_product_id:
        return
    from MPD.models import Products
    from core.db_routers import _get_mpd_db
    mpd_db = _get_mpd_db()
    deleted, _ = Products.objects.using(mpd_db).filter(id=mpd_product_id).delete()
    if deleted:
        logger.info("Saga kompensacja: usunięto produkt MPD id=%s", mpd_product_id)


def _saga_update_mada_mapping(
    mada_product_id: int,
    mpd_product_id: Optional[int] = None,
    variant_mapping: Optional[List[Tuple[int, int]]] = None,
    **kwargs: Any,
) -> None:
    """Krok 2 Sagi: zapisz mapowanie produktu i wariantów w Mada."""
    from mada.models import MadaProduct, MadaProductVariant
    from core.db_routers import _get_mada_db

    mada_db = _get_mada_db()
    if mpd_product_id is not None:
        MadaProduct.objects.using(mada_db).filter(pk=mada_product_id).update(
            mapped_product_uid=mpd_product_id
        )
    variant_mapping = variant_mapping or []
    for mada_variant_pk, mpd_variant_id in variant_mapping:
        MadaProductVariant.objects.using(mada_db).filter(pk=mada_variant_pk).update(
            mapped_variant_uid=mpd_variant_id,
            is_mapped=True,
        )


def _saga_clear_mada_mapping(mada_product_id: int, **kwargs: Any) -> None:
    """Kompensacja kroku 2: wyzeruj mapowanie w Mada."""
    from mada.models import MadaProduct, MadaProductVariant
    from core.db_routers import _get_mada_db

    mada_db = _get_mada_db()
    MadaProduct.objects.using(mada_db).filter(pk=mada_product_id).update(
        mapped_product_uid=None
    )
    MadaProductVariant.objects.using(mada_db).filter(product_id=mada_product_id).update(
        mapped_variant_uid=None,
        is_mapped=False,
    )
    logger.info("Saga kompensacja: wyzerowano mapowanie Mada product id=%s", mada_product_id)


def create_mpd_product_from_mada(
    mada_product_id: int,
    form_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tworzy produkt w MPD na podstawie produktu Mada (Saga: MPD + Mada, z kompensacją).

    Returns:
        Dict z kluczami: success (bool), mpd_product_id (int|None), error_message (str|None).
    """
    form_data = form_data or {}

    try:
        from mada.models import MadaProduct
        from core.db_routers import _get_mada_db

        mada_db = _get_mada_db()
        try:
            mada_product = (
                MadaProduct.objects.using(mada_db)
                .select_related('brand')
                .get(pk=mada_product_id)
            )
        except MadaProduct.DoesNotExist:
            return {
                'success': False,
                'mpd_product_id': None,
                'error_message': 'Produkt Mada nie istnieje',
            }

        if mada_product.mapped_product_uid:
            return {
                'success': False,
                'mpd_product_id': None,
                'error_message': 'Produkt jest już zmapowany do MPD',
            }

        saga = MadaSagaOrchestrator()
        saga.add_step(
            name='create_mpd',
            execute_func=_saga_create_mpd_mada,
            compensate_func=_saga_delete_mpd_mada,
            data={'mada_product_id': mada_product_id, 'form_data': form_data},
        )
        saga.add_step(
            name='update_mada_mapping',
            execute_func=_saga_update_mada_mapping,
            compensate_func=_saga_clear_mada_mapping,
            data={
                'mada_product_id': mada_product_id,
                'mpd_product_id': None,
                'variant_mapping': None,
            },
        )
        result = saga.execute()

        if result.status == SagaStatus.COMPLETED:
            mpd_product_id = result.steps[0].result.get('mpd_product_id') if result.steps else None
            logger.info("Utworzono produkt MPD %s z Mada produktu %s (Saga)", mpd_product_id, mada_product_id)
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
        logger.exception("Błąd tworzenia produktu MPD z Mada %s: %s", mada_product_id, e)
        return {
            'success': False,
            'mpd_product_id': None,
            'error_message': 'Nie udało się utworzyć produktu w MPD',
        }


def create_mpd_variants_from_mada(
    mpd_product_id: int,
    mada_product_id: int,
    size_category: str,
    producer_code: Optional[str] = None,
    main_color_id: Optional[int] = None,
    producer_color_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tworzy/dopina warianty w MPD z wariantów Mada (wzór: create_mpd_variants_from_tabu).
    Dla każdego wariantu Mada: szuka istniejącego wariantu MPD po EAN (inna hurtownia)
    lub tworzy nowy, dopina ProductvariantsSources + StockAndPrices dla źródła Mada,
    ustawia mapped_variant_uid w Mada.
    """
    from django.utils import timezone
    from mada.models import MadaProduct, MadaProductVariant
    from MPD.models import (
        Colors,
        ProductVariants,
        ProductvariantsSources,
        Sizes,
        Sources,
        StockAndPrices,
    )
    from MPD.source_adapters.base import normalize_ean
    from core.db_routers import _get_mpd_db, _get_mada_db

    mpd_db = _get_mpd_db()
    mada_db = _get_mada_db()

    mada_product = MadaProduct.objects.using(mada_db).get(pk=mada_product_id)
    mada_variants = list(
        MadaProductVariant.objects.using(mada_db).filter(product_id=mada_product_id)
    )
    if not mada_variants:
        logger.warning("Brak wariantów Mada dla produktu %s", mada_product_id)
        return {"created_variants": 0, "variant_ids": []}

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
        mada_color_name = (mada_variants[0].color or (mada_product.brand.name if mada_product.brand else "Brak koloru")).strip() or "Brak koloru"
        mada_producer_name = (producer_color_name or "").strip()[:50] if producer_color_name else ""
        if first_mpd and first_mpd.color and (first_mpd.color.name or "").strip() == mada_color_name:
            if mada_producer_name:
                if first_mpd.producer_color and (first_mpd.producer_color.name or "").strip() == mada_producer_name:
                    color_id = first_mpd.color_id
                    producer_color_id = first_mpd.producer_color_id
                    logger.info("Ten sam kolor i kolor producenta – dopisuję tylko warianty (color_id=%s, producer_color_id=%s)", color_id, producer_color_id)
            else:
                color_id = first_mpd.color_id
                producer_color_id = first_mpd.producer_color_id
                logger.info("Ten sam kolor – dopisuję tylko warianty (color_id=%s)", color_id)

    if color_id is None:
        mada_color_name = (mada_variants[0].color or (mada_product.brand.name if mada_product.brand else "Brak koloru")).strip() or "Brak koloru"
        color = Colors.objects.using(mpd_db).filter(name=mada_color_name).first()
        if not color:
            color = Colors.objects.using(mpd_db).create(name=mada_color_name)
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

    mada_source = Sources.objects.using(mpd_db).filter(name__icontains="Mada").first()
    if not mada_source:
        mada_source = Sources.objects.using(mpd_db).create(
            name=_MADA_SOURCE_NAME, type="api", location=_MADA_SOURCE_LOCATION
        )

    producer_code_val = (producer_code or "").strip()[:255] or None
    product_price = mada_product.price or Decimal("0")
    created_count = 0
    variant_ids = []

    for mada_var in mada_variants:
        if mada_var.mapped_variant_uid:
            logger.info("Wariant Mada %s już zmapowany (mpd variant %s) - pomijam", mada_var.variant_key, mada_var.mapped_variant_uid)
            continue

        size_name = (mada_var.size or "").strip()
        ean_raw = (mada_var.ean or "").strip()
        ean_norm = normalize_ean(mada_var.ean)

        size = (
            Sizes.objects.using(mpd_db)
            .filter(name__iexact=size_name, category=size_category)
            .first()
        )
        if not size and size_name:
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

        variant = None
        if ean_norm:
            for pvs in (
                ProductvariantsSources.objects.using(mpd_db)
                .filter(variant__product_id=mpd_product_id)
                .exclude(source=mada_source)
                .select_related("variant")
            ):
                if normalize_ean(pvs.ean) == ean_norm:
                    variant = pvs.variant
                    logger.info(
                        "Znaleziono wariant MPD po EAN %s (variant_id=%s) - dopinam Mada",
                        ean_norm, variant.variant_id,
                    )
                    break

        # Wariant Mada bez numerycznego id — dedup po (source, variant__product, ean)
        if variant is not None and ean_norm and ProductvariantsSources.objects.using(mpd_db).filter(
            source=mada_source, variant__product_id=mpd_product_id, ean__iexact=ean_raw
        ).exists():
            logger.info("Wariant Mada ean=%s już dopięty w MPD - pomijam", ean_raw)
            continue

        if variant is None:
            variant = ProductVariants.objects.using(mpd_db).create(
                product_id=mpd_product_id,
                color_id=color_id,
                producer_color_id=producer_color_id,
                size=size,
            )
            logger.info("Utworzono wariant MPD %s dla Mada %s", variant.variant_id, mada_var.variant_key)

        ProductvariantsSources.objects.using(mpd_db).get_or_create(
            variant=variant,
            source=mada_source,
            defaults={
                "ean": (ean_raw or "")[:50] if ean_raw else "",
                "producer_code": producer_code_val,
            },
        )
        StockAndPrices.objects.using(mpd_db).get_or_create(
            variant=variant,
            source=mada_source,
            defaults={
                "stock": mada_var.stock if mada_var.stock is not None else 0,
                "price": product_price,
                "currency": "PLN",
                "last_updated": timezone.now(),
            },
        )
        MadaProductVariant.objects.using(mada_db).filter(pk=mada_var.pk).update(
            mapped_variant_uid=variant.variant_id,
            is_mapped=True,
        )
        variant_ids.append(variant.variant_id)
        created_count += 1

    if created_count > 0:
        from MPD.tasks import link_variants_from_other_sources_task
        link_variants_from_other_sources_task.apply_async(
            args=(mpd_product_id, mada_source.id),
            queue="default",
        )
        logger.info(
            "Wysłano task linkowania po EAN dla produktu MPD %s (source %s)",
            mpd_product_id, mada_source.id,
        )

    return {"created_variants": created_count, "variant_ids": variant_ids}


def upload_mada_images_to_mpd(
    mpd_product_id: int,
    mada_product_id: int,
    producer_color_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Upload zdjęć produktu Mada do bucketa i zapis do MPD (jak Matterhorn1/Tabu).
    Ustawia product_images.producer_color_id wprost (jawne grupowanie po kolorze).
    Zwraca dict z kluczami: uploaded_images (int), images (lista), upload_error (str, opcjonalnie).
    """
    try:
        from mada.models import MadaProduct
        from MPD.models import Colors, Products, ProductImage
        from core.db_routers import _get_mpd_db, _get_mada_db
        from matterhorn1.defs_db import upload_image_to_bucket_and_get_url

        mpd_db = _get_mpd_db()
        mada_db = _get_mada_db()
        mada_product = MadaProduct.objects.using(mada_db).get(pk=mada_product_id)

        images_to_upload = []
        seen = set()
        for img in mada_product.images.order_by("order", "api_image_id"):
            url = (img.image_url or "").strip()
            if url and url not in seen:
                images_to_upload.append((url, len(images_to_upload) + 1))
                seen.add(url)

        if not images_to_upload:
            logger.info("Brak zdjęć Mada do uploadu dla produktu %s", mada_product_id)
            return {"uploaded_images": 0, "images": []}

        mpd_product = Products.objects.using(mpd_db).get(pk=mpd_product_id)
        producer_color = (producer_color_name or "").strip()
        producer_color_obj = (
            Colors.objects.using(mpd_db).filter(name=producer_color).first()
            if producer_color else None
        )
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
                    defaults={"producer_color": producer_color_obj},
                )
                uploaded_count += 1
                uploaded_images.append({"original_url": img_url, "storage_key": bucket_key, "order": order_num})
                logger.info("Uploadowano zdjęcie Mada %s -> MPD %s (nr %s)", mada_product_id, mpd_product_id, order_num)

        logger.info("Uploadowano %s zdjęć Mada do MPD produktu %s", uploaded_count, mpd_product_id)
        return {"uploaded_images": uploaded_count, "images": uploaded_images}
    except Exception as e:
        logger.exception("Błąd uploadu zdjęć Mada→MPD: %s", e)
        return {"uploaded_images": 0, "images": [], "upload_error": str(e)}
