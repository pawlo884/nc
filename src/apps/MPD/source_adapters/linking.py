"""
Logika dopinania wariantów z innych hurtowni po EAN.
"""
import logging
from decimal import Decimal
from typing import Dict, Optional, Set

from django.utils import timezone

from MPD.models import (
    ProductVariants,
    ProductvariantsSources,
    Sizes,
    Sources,
    StockAndPrices,
)

from .base import normalize_ean
from .registry import get_adapters_for_source, get_adapter_for_source

logger = logging.getLogger(__name__)


def _get_mpd_db() -> str:
    from django.conf import settings
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def _variant_uid_int(m) -> Optional[int]:
    """Konwersja variant_uid z matcha na int do kolumny ProductvariantsSources.variant_uid."""
    uid = getattr(m, 'variant_uid', None)
    if uid is None:
        return None
    s = str(uid).strip()
    return int(s) if s.isdigit() else None


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
                updated_source_products: Set[int] = set()  # unikalne produkty w hurtowni (mapped_product_uid)
                for m in matches:
                    mpd_variant_id = variant_by_ean.get(m.ean)
                    if not mpd_variant_id:
                        logger.debug(
                            "Pominięto match ean=%s - brak w variant_by_ean",
                            m.ean
                        )
                        continue

                    variant_uid_int = _variant_uid_int(m)
                    defaults_pvs = {
                        'ean': (m.ean or '')[:50] if m.ean else '',
                        'variant_uid': variant_uid_int,
                    }
                    if getattr(m, 'producer_code', None) and (m.producer_code or '').strip():
                        defaults_pvs['producer_code'] = (m.producer_code or '').strip()[:255]
                    pvs, created = ProductvariantsSources.objects.using(db).get_or_create(
                        variant_id=mpd_variant_id,
                        source=source,
                        defaults=defaults_pvs,
                    )
                    if not created and pvs.variant_uid is None and variant_uid_int is not None:
                        pvs.variant_uid = variant_uid_int
                        pvs.save(update_fields=['variant_uid'], using=db)
                    if created:
                        stats['linked_count'] += 1
                        logger.info(
                            "Dopięto ProductvariantsSources: variant=%s source=%s ean=%s variant_uid=%s",
                            mpd_variant_id, source.name, m.ean, variant_uid_int
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
                            adapter.update_source_product_mapped(
                                m.source_product_id, mpd_product_id
                            )
                            updated_source_products.add(m.source_product_id)
                            logger.info(
                                "Ustawiono mapped_product_uid=%s dla produktu %s w źródle %s",
                                mpd_product_id, m.source_product_id, source.name
                            )
                        except Exception as upd_err:
                            logger.warning(
                                "Błąd ustawiania mapped_product_uid dla %s: %s",
                                m.source_product_id, upd_err
                            )

                # Pozostałe warianty z tego samego produktu w źródle (wszystkie hurtownie)
                ean_linked: Set[str] = set(variant_by_ean.keys())
                for source_product_id in updated_source_products:
                    try:
                        all_in_source = adapter.get_all_variants_for_product(source_product_id)
                        first_mpd = variants[0] if variants else None
                        if not first_mpd:
                            continue
                        for m in all_in_source:
                            ean_norm = normalize_ean(m.ean) if m.ean else ''
                            if ean_norm and ean_norm in ean_linked:
                                continue
                            # Nowy wariant MPD dla „pozostałego” rozmiaru z hurtowni
                            size_name = (m.size or '').strip()[:255] if m.size else ''
                            size_obj = None
                            if size_name:
                                size_obj = (
                                    Sizes.objects.using(db).filter(name__iexact=size_name).first()
                                    or Sizes.objects.using(db).filter(name=size_name).first()
                                )
                                if not size_obj:
                                    size_obj = Sizes.objects.using(db).create(
                                        name=size_name,
                                        category=None,
                                        unit=None,
                                        name_lower=size_name.lower() if size_name else '',
                                    )
                            # Kod producenta w ProductvariantsSources.producer_code (per hurtownia)
                            new_pv = ProductVariants.objects.using(db).create(
                                product_id=mpd_product_id,
                                color_id=first_mpd.color_id,
                                producer_color_id=first_mpd.producer_color_id,
                                size=size_obj,
                            )
                            variant_uid_int = _variant_uid_int(m)
                            ProductvariantsSources.objects.using(db).create(
                                variant_id=new_pv.variant_id,
                                source=source,
                                ean=(m.ean or '')[:50] if m.ean else '',
                                variant_uid=variant_uid_int,
                                producer_code=(getattr(m, 'producer_code', None) or '').strip()[:255] or None,
                            )
                            StockAndPrices.objects.using(db).create(
                                variant_id=new_pv.variant_id,
                                source=source,
                                stock=m.stock or 0,
                                price=m.price or Decimal('0'),
                                currency=m.currency or 'PLN',
                                last_updated=timezone.now(),
                            )
                            if ean_norm:
                                variant_by_ean[ean_norm] = new_pv.variant_id
                                ean_linked.add(ean_norm)
                            stats['linked_count'] += 1
                            logger.info(
                                "Dodano pozostały wariant z produktu %s: size=%s ean=%s variant_id=%s",
                                source_product_id, size_name, m.ean, new_pv.variant_id
                            )
                    except Exception as rem_err:
                        logger.exception(
                            "Błąd dopinania pozostałych wariantów dla produktu %s: %s",
                            source_product_id, rem_err
                        )
                        stats['errors'].append(str(rem_err))

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
            variant_uid_int = _variant_uid_int(m)
            defaults_pvs = {
                'ean': (m.ean or '')[:50] if m.ean else '',
                'variant_uid': variant_uid_int,
            }
            if getattr(m, 'producer_code', None) and (m.producer_code or '').strip():
                defaults_pvs['producer_code'] = (m.producer_code or '').strip()[:255]
            pvs, created = ProductvariantsSources.objects.using(db).get_or_create(
                variant_id=mpd_variant_id,
                source=source,
                defaults=defaults_pvs,
            )
            if not created and pvs.variant_uid is None and variant_uid_int is not None:
                pvs.variant_uid = variant_uid_int
                pvs.save(update_fields=['variant_uid'], using=db)
            if created:
                stats['linked_count'] += 1
                logger.info(
                    "Dopięto ProductvariantsSources (new source): variant=%s source=%s ean=%s variant_uid=%s",
                    mpd_variant_id, source.name, m.ean, variant_uid_int
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
                    adapter.update_source_product_mapped(m.source_product_id, mpd_product_id)
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
