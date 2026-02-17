"""
Adapter dla hurtowni Tabu.
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
                result.append(VariantMatch(
                    ean=ean_norm,
                    variant_uid=str(v.api_id),
                    stock=v.store or 0,
                    price=v.price_net or Decimal('0'),
                    currency='PLN',
                    size=v.size or '',
                    color=v.color or '',
                    source_product_id=v.product_id if v.product_id else None,
                ))
        return result
