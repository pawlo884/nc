"""
Adapter dla hurtowni Tabu.

Mapowanie na product_variants_sources:
- variant_uid = api_id z tabu_product_variant (pole „id” wariantu z API Tabu)
- producer_code = symbol z tabu_product_variant (pusty, gdy symbol pusty)
"""
import logging
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q

from core.db_routers import _get_tabu_db
from .base import SourceAdapter, VariantMatch, normalize_ean

logger = logging.getLogger(__name__)


class TabuAdapter(SourceAdapter):
    source_name = 'Tabu API'

    def get_variants_by_eans(
        self,
        ean_list: List[str],
        mpd_product_id: Optional[int] = None,
    ) -> List[VariantMatch]:
        """Pobiera warianty Tabu po EAN (case-insensitive)."""
        from tabu.models import TabuProductVariant

        ean_set = {normalize_ean(e) for e in ean_list if e and str(e).strip()}
        if not ean_set:
            return []

        q = Q()
        for e in ean_set:
            q |= Q(ean__iexact=e)
        # .using() jawnie – automatyczny routing przez DATABASE_ROUTERS bywa niezawodny
        # tylko w normalnym request/shell, w środowisku testowym (manage.py test) łańcuch
        # routerów bywa pusty i zapytanie bez .using() trafia do bazy 'default'.
        qs = TabuProductVariant.objects.using(_get_tabu_db()).filter(q).select_related('product')
        if mpd_product_id:
            qs = qs.filter(product__mapped_product_uid=mpd_product_id)

        result = []
        for v in qs:
            ean_norm = normalize_ean(v.ean)
            if ean_norm in ean_set:
                # variant_uid = api_id; producer_code = symbol z tabu_product_variant
                result.append(VariantMatch(
                    ean=ean_norm,
                    variant_uid=str(v.api_id),
                    stock=v.store or 0,
                    price=v.price_net or Decimal('0'),
                    currency='PLN',
                    size=v.size or '',
                    color=v.color or '',
                    source_product_id=v.product_id if v.product_id else None,
                    producer_code=(v.symbol or '').strip() or None,
                ))
        return result

    def get_all_variants_for_product(
        self,
        source_product_id: int,
    ) -> List[VariantMatch]:
        """Wszystkie warianty produktu Tabu (do dopinania pozostałych rozmiarów)."""
        from tabu.models import TabuProductVariant

        qs = TabuProductVariant.objects.using(_get_tabu_db()).filter(
            product_id=source_product_id
        ).select_related('product')
        result = []
        for v in qs:
            ean_norm = normalize_ean(v.ean) if v.ean else ''
            # variant_uid = api_id; producer_code = symbol z tabu_product_variant
            result.append(VariantMatch(
                ean=ean_norm,
                variant_uid=str(v.api_id),
                stock=v.store or 0,
                price=v.price_net or Decimal('0'),
                currency='PLN',
                size=v.size or '',
                color=v.color or '',
                source_product_id=v.product_id if v.product_id else None,
                producer_code=(v.symbol or '').strip() or None,
            ))
        return result

    def update_source_product_mapped(
        self,
        source_product_id: int,
        mpd_product_id: int,
    ) -> None:
        """Ustawia mapped_product_uid w Tabu TabuProduct — pomija nadpisanie, jeśli produkt
        jest już zmapowany do INNEGO produktu MPD (przypadkowy duplikat EAN w danych
        źródłowych nie powinien po cichu przepinać istniejącego mapowania)."""
        from tabu.models import TabuProduct

        tabu_db = _get_tabu_db()
        product = TabuProduct.objects.using(tabu_db).filter(id=source_product_id).first()
        if product is None:
            return
        if product.mapped_product_uid is not None and product.mapped_product_uid != mpd_product_id:
            logger.warning(
                "Pomijam nadpisanie mapped_product_uid produktu tabu %s: już zmapowany "
                "do %s (próba przepięcia na %s przez dopasowanie EAN)",
                source_product_id, product.mapped_product_uid, mpd_product_id,
            )
            return
        TabuProduct.objects.using(tabu_db).filter(id=source_product_id).update(
            mapped_product_uid=mpd_product_id,
        )

    def update_source_variant_mapped(
        self,
        source_product_id: int,
        source_variant_uid: Optional[str],
        mpd_variant_id: int,
    ) -> None:
        """Ustawia mapped_variant_uid i is_mapped w Tabu TabuProductVariant (wzorzec jak
        Matterhorn) — pomija nadpisanie, jeśli wariant jest już zmapowany do INNEGO wariantu MPD."""
        if not source_variant_uid or not str(source_variant_uid).strip():
            return
        try:
            api_id = int(source_variant_uid.strip())
        except (ValueError, TypeError):
            return
        from tabu.models import TabuProductVariant

        tabu_db = _get_tabu_db()
        variant = TabuProductVariant.objects.using(tabu_db).filter(
            product_id=source_product_id,
            api_id=api_id,
        ).first()
        if variant is None:
            return
        if variant.mapped_variant_uid is not None and variant.mapped_variant_uid != mpd_variant_id:
            logger.warning(
                "Pomijam nadpisanie mapped_variant_uid wariantu tabu %s: już zmapowany "
                "do %s (próba przepięcia na %s przez dopasowanie EAN)",
                api_id, variant.mapped_variant_uid, mpd_variant_id,
            )
            return
        TabuProductVariant.objects.using(tabu_db).filter(pk=variant.pk).update(
            mapped_variant_uid=mpd_variant_id, is_mapped=True,
        )
