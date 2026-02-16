"""
Logika dopinania wariantów z innych hurtowni po EAN.
"""
import logging
from decimal import Decimal
from typing import Dict, Optional

from django.utils import timezone

from MPD.models import (
    ProductVariants,
    ProductvariantsSources,
    Sources,
    StockAndPrices,
)

from .registry import get_adapters_for_source, get_adapter_for_source

logger = logging.getLogger(__name__)


def _get_mpd_db() -> str:
    from django.conf import settings
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def link_variants_from_other_sources(
    mpd_product_id: int,
    current_source_id: int,
) -> Dict:
    """
    Dla produktu MPD dopina warianty z pozostałych hurtowni (dopasowanie po EAN).

    Args:
        mpd_product_id: ID produktu w MPD
        current_source_id: Źródło z którego właśnie dodano (pomijane)

    Returns:
        Dict z statystykami: linked_count, sources_processed, errors
    """
    db = _get_mpd_db()
    stats = {'linked_count': 0, 'sources_processed': 0, 'errors': []}

    try:
        variants = list(
            ProductVariants.objects.using(db).filter(product_id=mpd_product_id)
        )
        if not variants:
            return stats

        variant_ids = [v.variant_id for v in variants]
        sources_qs = ProductvariantsSources.objects.using(db).filter(
            variant_id__in=variant_ids
        )
        ean_by_variant: Dict[int, str] = {}
        for s in sources_qs:
            if s.ean and str(s.ean).strip():
                ean_by_variant[s.variant_id] = str(s.ean).strip()

        if not ean_by_variant:
            return stats

        ean_list = list(set(ean_by_variant.values()))
        variant_by_ean = {ean: vid for vid, ean in ean_by_variant.items()}

        for source_id, adapter in get_adapters_for_source(exclude_source_id=current_source_id):
            try:
                matches = adapter.get_variants_by_eans(
                    ean_list, mpd_product_id=mpd_product_id
                )
                source = Sources.objects.using(db).get(id=source_id)

                for m in matches:
                    mpd_variant_id = variant_by_ean.get(m.ean)
                    if not mpd_variant_id:
                        continue

                    pvs, created = ProductvariantsSources.objects.using(db).get_or_create(
                        variant_id=mpd_variant_id,
                        source=source,
                        defaults={
                            'ean': m.ean,
                            'variant_uid': int(m.variant_uid) if m.variant_uid.isdigit() else None,
                        }
                    )
                    if created:
                        stats['linked_count'] += 1
                        logger.info(
                            "Dopięto ProductvariantsSources: variant=%s source=%s ean=%s",
                            mpd_variant_id, source.name, m.ean
                        )

                    sap, created = StockAndPrices.objects.using(db).get_or_create(
                        variant_id=mpd_variant_id,
                        source=source,
                        defaults={
                            'stock': m.stock,
                            'price': m.price,
                            'currency': m.currency or 'PLN',
                            'last_updated': timezone.now(),
                        }
                    )
                    if created:
                        logger.info(
                            "Dopięto StockAndPrices: variant=%s source=%s stock=%s price=%s",
                            mpd_variant_id, source.name, m.stock, m.price
                        )

                stats['sources_processed'] += 1
            except Exception as e:
                logger.exception("Błąd linkowania ze źródła %s: %s", source_id, e)
                stats['errors'].append(str(e))

    except Exception as e:
        logger.exception("Błąd link_variants_from_other_sources: %s", e)
        stats['errors'].append(str(e))

    return stats


def link_all_products_to_new_source(new_source_id: int) -> Dict:
    """
    Dla nowej hurtowni - dopina warianty do wszystkich produktów MPD (po EAN).

    Uruchamiane gdy dodajemy nową hurtownię do systemu.
    Szuka w nowej hurtowni wariantów o EAN istniejących w MPD i dopina je.
    """
    db = _get_mpd_db()
    stats = {'products_processed': 0, 'linked_count': 0, 'errors': []}

    adapter = get_adapter_for_source(new_source_id)
    if not adapter:
        stats['errors'].append(f"Brak adaptera dla source_id={new_source_id}")
        return stats

    try:
        source = Sources.objects.using(db).get(id=new_source_id)
    except Sources.DoesNotExist:
        stats['errors'].append(f"Źródło {new_source_id} nie istnieje")
        return stats

    ean_to_variant = {}
    for pvs in ProductvariantsSources.objects.using(db).select_related('variant').filter(
        ean__isnull=False
    ).exclude(ean=''):
        ean = str(pvs.ean).strip()
        if ean:
            ean_to_variant[ean] = (pvs.variant_id, pvs.variant.product_id)

    ean_list = list(ean_to_variant.keys())
    if not ean_list:
        return stats

    matches = adapter.get_variants_by_eans(ean_list, mpd_product_id=None)

    for m in matches:
        key = ean_to_variant.get(m.ean)
        if not key:
            continue
        mpd_variant_id, _ = key

        try:
            pvs, created = ProductvariantsSources.objects.using(db).get_or_create(
                variant_id=mpd_variant_id,
                source=source,
                defaults={
                    'ean': m.ean,
                    'variant_uid': int(m.variant_uid) if m.variant_uid.isdigit() else None,
                }
            )
            if created:
                stats['linked_count'] += 1
                logger.info(
                    "Dopięto ProductvariantsSources (new source): variant=%s source=%s ean=%s",
                    mpd_variant_id, source.name, m.ean
                )

            sap, created = StockAndPrices.objects.using(db).get_or_create(
                variant_id=mpd_variant_id,
                source=source,
                defaults={
                    'stock': m.stock,
                    'price': m.price,
                    'currency': m.currency or 'PLN',
                    'last_updated': timezone.now(),
                }
            )
            if created:
                stats['products_processed'] += 1
        except Exception as e:
            logger.exception("Błąd dopinania variant=%s: %s", mpd_variant_id, e)
            stats['errors'].append(str(e))

    return stats
