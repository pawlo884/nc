"""
Funkcje pomocnicze dla tworzenia wariantów w Sadze
"""
import json
import logging
from decimal import Decimal
from typing import Dict, List

from django.conf import settings
from django.db import connections

logger = logging.getLogger(__name__)


def _get_mpd_db() -> str:
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def _get_mh_db() -> str:
    return 'zzz_matterhorn1' if 'zzz_matterhorn1' in settings.DATABASES else 'matterhorn1'


def create_mpd_variants(
    mpd_product_id: int,
    matterhorn_product_id: int,
    size_category: str,
    producer_code: str = None,
    main_color_id: int = None,
    producer_color_name: str = None,
) -> Dict:
    """Utwórz warianty w MPD - na koniec wysyłany jest 1 task linkowania po EAN (product_id + source_id)."""
    from matterhorn1.models import Product as MhProduct, ProductVariant as MhProductVariant
    from MPD.models import (
        Colors,
        ProductVariants,
        ProductvariantsSources,
        Sizes,
        Sources,
        StockAndPrices,
    )
    from django.utils import timezone

    mpd_db = _get_mpd_db()
    mh_db = _get_mh_db()

    logger.info(
        "Tworzę warianty w MPD dla produktu %s, kategoria: %s",
        mpd_product_id,
        size_category,
    )
    logger.info(
        "Parametry: producer_code='%s', main_color_id=%s, producer_color_name='%s'",
        producer_code,
        main_color_id,
        producer_color_name,
    )

    try:
        # Pobierz produkt z matterhorn1
        mh_product = MhProduct.objects.using(mh_db).get(id=matterhorn_product_id)
        product_color = mh_product.color or 'Brak koloru'
        product_prices = mh_product.prices or {}
        if isinstance(product_prices, str):
            product_prices = json.loads(product_prices) if product_prices else {}
        product_price = product_prices.get('PLN', 0) if isinstance(product_prices, dict) else 0
        if isinstance(product_price, str):
            product_price = float(product_price)

        logger.info("Produkt: kolor=%s, cena=%s", product_color, product_price)

        # Kolor w MPD
        color = Colors.objects.using(mpd_db).filter(name=product_color).first()
        if not color:
            raise ValueError("Color %s not found in MPD" % product_color)
        color_id = color.id

        # Producer color
        producer_color_id = None
        if producer_color_name and main_color_id:
            producer_color, created = Colors.objects.using(mpd_db).get_or_create(
                name=producer_color_name,
                parent_id=main_color_id,
                defaults={'hex_code': ''},
            )
            producer_color_id = producer_color.id
            if created:
                logger.info("Utworzono kolor producenta: %s", producer_color_name)
        else:
            logger.warning(
                "Brak producer_color_name lub main_color_id - producer_color_id będzie None"
            )

        # IaiProductCounter - atomic increment (raw SQL dla ON CONFLICT)
        with connections[mpd_db].cursor() as cursor:
            cursor.execute("""
                INSERT INTO iai_product_counter (id, counter_value)
                VALUES (1, 1)
                ON CONFLICT (id)
                DO UPDATE SET counter_value = iai_product_counter.counter_value + 1
                RETURNING counter_value
            """)
            row = cursor.fetchone()
            iai_product_id = row[0] if row else 1
        logger.info("Wygenerowano iai_product_id: %s", iai_product_id)

        # Źródło Matterhorn
        mh_source = Sources.objects.using(mpd_db).filter(
            name__icontains='matterhorn'
        ).first()
        if not mh_source:
            raise ValueError("Brak źródła Matterhorn w MPD")

        # Warianty z matterhorn1
        mh_variants = list(
            MhProductVariant.objects.using(mh_db).filter(product_id=matterhorn_product_id)
        )
        if not mh_variants:
            logger.warning("Brak wariantów dla produktu %s", matterhorn_product_id)
            return {
                "created_variants": 0,
                "iai_product_id": iai_product_id,
                "variant_ids": [],
            }

        created_count = 0
        variant_ids = []

        for mh_var in mh_variants:
            size_name = mh_var.name
            stock = mh_var.stock
            ean = (mh_var.ean or '').strip() if mh_var.ean else ''
            variant_uid_raw = mh_var.variant_uid
            try:
                variant_uid_int = int(variant_uid_raw) if variant_uid_raw and str(variant_uid_raw).isdigit() else None
            except (ValueError, TypeError):
                variant_uid_int = None

            # Rozmiar
            size = (
                Sizes.objects.using(mpd_db)
                .filter(name__iexact=size_name, category=size_category)
                .first()
            )
            if not size:
                logger.warning(
                    "Rozmiar %s nie znaleziony w kategorii %s", size_name, size_category
                )
                continue

            # Już istnieje?
            if ProductvariantsSources.objects.using(mpd_db).filter(
                variant_uid=variant_uid_int, source=mh_source
            ).exists():
                logger.info("Wariant %s już istnieje - pomijam", variant_uid_raw)
                continue

            # Wariant po EAN z innej hurtowni?
            variant_id = None
            if ean:
                # Szukaj istniejącego wariantu po EAN (bez użycia ORM ProductVariants,
                # żeby nie odwoływać się do nieistniejącej kolumny iai_product_id)
                with connections[mpd_db].cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT pv.variant_id
                        FROM product_variants pv
                        INNER JOIN product_variants_sources pvs
                            ON pv.variant_id = pvs.variant_id
                        WHERE pvs.ean = %s
                          AND pv.product_id = %s
                          AND (pvs.source_id IS NULL OR pvs.source_id <> %s)
                        LIMIT 1
                        """,
                        [ean, mpd_product_id, mh_source.id],
                    )
                    row = cursor.fetchone()
                    if row:
                        variant_id = row[0]
                        logger.info(
                            "Znaleziono wariant po EAN %s (variant_id=%s) - dopinam Matterhorn",
                            ean,
                            variant_id,
                        )

            # Utwórz nowy wariant jeśli nie znaleziono (producer_code tylko w ProductvariantsSources)
            if variant_id is None:
                with connections[mpd_db].cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO product_variants (product_id, color_id, producer_color_id, size_id)
                        VALUES (%s, %s, %s, %s)
                        RETURNING variant_id
                        """,
                        [mpd_product_id, color_id, producer_color_id, size.id],
                    )
                    row = cursor.fetchone()
                    variant_id = row[0]
                logger.info(
                    "Utworzono wariant %s (producer_color_id=%s)",
                    variant_id,
                    producer_color_id,
                )

            # ProductvariantsSources: kod producenta w producer_code (per hurtownia)
            pvs, pvs_created = ProductvariantsSources.objects.using(mpd_db).get_or_create(
                variant_id=variant_id,
                source=mh_source,
                defaults={
                    'ean': (ean or '')[:50] if ean else '',
                    'variant_uid': variant_uid_int,
                    'producer_code': (producer_code or '').strip()[:255] or None,
                },
            )

            # StockAndPrices
            StockAndPrices.objects.using(mpd_db).get_or_create(
                variant_id=variant_id,
                source=mh_source,
                defaults={
                    'stock': stock,
                    'price': Decimal(str(product_price)),
                    'currency': 'PLN',
                    'last_updated': timezone.now(),
                },
            )

            # Aktualizacja mapped_variant_uid w matterhorn1
            MhProductVariant.objects.using(mh_db).filter(
                variant_uid=variant_uid_raw
            ).update(
                mapped_variant_uid=variant_id,
                is_mapped=True,
                updated_at=timezone.now(),
            )

            variant_ids.append(variant_id)
            created_count += 1
            logger.info("Utworzono wariant %s -> %s", variant_uid_raw, variant_id)

        logger.info("Utworzono %s wariantów w MPD", created_count)

        # Jeden task linkowania wariantów po EAN na produkt (nie per wariant)
        if created_count > 0:
            from MPD.tasks import link_variants_from_other_sources_task
            link_variants_from_other_sources_task.apply_async(
                args=(mpd_product_id, mh_source.id),
                queue='default',
            )
            logger.info("Wysłano task linkowania po EAN dla produktu MPD %s (source %s)", mpd_product_id, mh_source.id)

        return {
            "created_variants": created_count,
            "iai_product_id": iai_product_id,
            "variant_ids": variant_ids,
        }

    except MhProduct.DoesNotExist:
        raise ValueError("Product %s not found in matterhorn1" % matterhorn_product_id)
    except Exception as e:
        raise Exception("Failed to create MPD variants: %s" % e) from e


def delete_mpd_variants(
    mpd_product_id: int,
    matterhorn_product_id: int = None,
    variant_ids: List[int] = None,
    **kwargs,
) -> Dict:
    """Usuń warianty z MPD (kompensacja)"""
    from matterhorn1.models import ProductVariant as MhProductVariant
    from MPD.models import ProductVariants, ProductvariantsSources, StockAndPrices

    mpd_db = _get_mpd_db()
    mh_db = _get_mh_db()

    logger.info("Usuwam warianty z MPD dla produktu %s", mpd_product_id)

    try:
        if variant_ids is None:
            variant_ids = list(
                ProductVariants.objects.using(mpd_db)
                .filter(product_id=mpd_product_id)
                .values_list('variant_id', flat=True)
            )

        for variant_id in variant_ids:
            StockAndPrices.objects.using(mpd_db).filter(variant_id=variant_id).delete()
            ProductvariantsSources.objects.using(mpd_db).filter(
                variant_id=variant_id
            ).delete()
            ProductVariants.objects.using(mpd_db).filter(variant_id=variant_id).delete()

        if variant_ids:
            logger.info("Usunięto %s wariantów", len(variant_ids))
        else:
            logger.info("Usunięto wszystkie warianty produktu %s", mpd_product_id)

        if matterhorn_product_id:
            from django.utils import timezone
            MhProductVariant.objects.using(mh_db).filter(
                product_id=matterhorn_product_id
            ).update(
                mapped_variant_uid=None,
                is_mapped=False,
                updated_at=timezone.now(),
            )

    except Exception as e:
        logger.error("Błąd podczas usuwania wariantów: %s", e)

    return {}
