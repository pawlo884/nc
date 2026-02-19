"""
Adapter dla hurtowni Tabu.

Mapowanie na product_variants_sources:
- variant_uid = api_id z tabu_product_variant (pole „id” wariantu z API Tabu)
- producer_code = symbol z tabu_product_variant (pusty, gdy symbol pusty)
"""
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q

from .base import SourceAdapter, VariantMatch, normalize_ean


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
        qs = TabuProductVariant.objects.filter(q).select_related('product')
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

        qs = TabuProductVariant.objects.filter(product_id=source_product_id).select_related('product')
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
        """Ustawia mapped_product_uid w Tabu TabuProduct."""
        from django.conf import settings
        from tabu.models import TabuProduct

        tabu_db = 'zzz_tabu' if 'zzz_tabu' in settings.DATABASES else 'tabu'
        TabuProduct.objects.using(tabu_db).filter(id=source_product_id).update(
            mapped_product_uid=mpd_product_id,
        )
