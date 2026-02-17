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

from .base import normalize_ean
from .registry import get_adapters_for_source, get_adapter_for_source

logger = logging.getLogger(__name__)


def _get_mpd_db() -> str:
    from django.conf import settings
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def _update_source_product_mapped(source, source_product_id: int, mpd_product_id: int) -> None:
    """Ustawia mapped_product_uid w hurtowni źródłowej (Tabu/Matterhorn)."""
    from django.conf import settings
    name = (source.name or '').lower()
    if 'tabu' in name:
        from tabu.models import TabuProduct
        tabu_db = 'zzz_tabu' if 'zzz_tabu' in settings.DATABASES else 'tabu'
        TabuProduct.objects.using(tabu_db).filter(id=source_product_id).update(
            mapped_product_uid=mpd_product_id
        )
    elif 'matterhorn' in name:
        from matterhorn1.models import Product
        mh_db = 'zzz_matterhorn1' if 'zzz_matterhorn1' in settings.DATABASES else 'matterhorn1'
        Product.objects.using(mh_db).filter(id=source_product_id).update(
            mapped_product_uid=mpd_product_id,
            is_mapped=True
        )


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
            ean_norm = normalize_ean(s.ean)
            if ean_norm:
                ean_by_variant[s.variant_id] = ean_norm

        if not ean_by_variant:
            logger.info(
                "link_variants_from_other_sources: brak EAN dla produktu MPD %s",
                mpd_product_id
            )
            return stats

        ean_list = list(set(ean_by_variant.values()))
        variant_by_ean = {ean: vid for vid, ean in ean_by_variant.items()}
        adapters = list(get_adapters_for_source(exclude_source_id=current_source_id))
        logger.info(
            "link_variants_from_other_sources: mpd_product_id=%s ean_list=%s (exclude source %s), adapters=%s",
            mpd_product_id, ean_list[:10], current_source_id, len(adapters)
        )
        if not adapters:
            logger.warning(
                "link_variants_from_other_sources: brak adapterów dla innych źródeł (tylko 1 źródło?)"
            )
            return stats

        for source_id, adapter in adapters:
            try:
                matches = adapter.get_variants_by_eans(
                    ean_list, mpd_product_id=None
                )
                source = Sources.objects.using(db).get(id=source_id)

                logger.info(
                    "link_variants_from_other_sources: źródło %s zwróciło %s dopasowań",
                    source.name, len(matches)
                )
                updated_source_products = set()  # unikalne produkty w hurtowni (mapped_product_uid)
                for m in matches:
                    mpd_variant_id = variant_by_ean.get(m.ean)
                    if not mpd_variant_id:
                        logger.debug(
                            "Pominięto match ean=%s - brak w variant_by_ean",
                            m.ean
                        )
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

                    # Ustaw mapped_product_uid w hurtowni źródłowej (jak przy ręcznym mapowaniu)
                    if m.source_product_id and m.source_product_id not in updated_source_products:
                        try:
                            _update_source_product_mapped(
                                source, m.source_product_id, mpd_product_id
                            )
                            updated_source_products.add(m.source_product_id)
                            logger.info(
                                "Ustawiono mapped_product_uid=%s dla produktu %s w %s",
                                mpd_product_id, m.source_product_id, source.name
                            )
                        except Exception as upd_err:
                            logger.warning(
                                "Błąd ustawiania mapped_product_uid dla %s: %s",
                                m.source_product_id, upd_err
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
        ean_norm = normalize_ean(pvs.ean)
        if ean_norm:
            ean_to_variant[ean_norm] = (pvs.variant_id, pvs.variant.product_id)

    ean_list = list(ean_to_variant.keys())
    if not ean_list:
        return stats

    matches = adapter.get_variants_by_eans(ean_list, mpd_product_id=None)
    updated_source_products = set()

    for m in matches:
        key = ean_to_variant.get(m.ean)
        if not key:
            continue
        mpd_variant_id, mpd_product_id = key

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

            # Ustaw mapped_product_uid w nowej hurtowni
            if m.source_product_id and m.source_product_id not in updated_source_products:
                try:
                    _update_source_product_mapped(source, m.source_product_id, mpd_product_id)
                    updated_source_products.add(m.source_product_id)
                    logger.info(
                        "Ustawiono mapped_product_uid=%s dla produktu %s w nowej hurtowni %s",
                        mpd_product_id, m.source_product_id, source.name
                    )
                except Exception as upd_err:
                    logger.warning(
                        "Błąd ustawiania mapped_product_uid dla %s: %s",
                        m.source_product_id, upd_err
                    )
        except Exception as e:
            logger.exception("Błąd dopinania variant=%s: %s", mpd_variant_id, e)
            stats['errors'].append(str(e))

    return stats
