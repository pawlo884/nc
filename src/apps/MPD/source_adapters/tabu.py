"""
Adapter dla hurtowni Tabu.
"""
from decimal import Decimal
from typing import List, Optional

from .base import SourceAdapter, VariantMatch


class TabuAdapter(SourceAdapter):
    source_name = 'Tabu API'

    def get_variants_by_eans(
        self,
        ean_list: List[str],
        mpd_product_id: Optional[int] = None,
    ) -> List[VariantMatch]:
        """Pobiera warianty Tabu po EAN."""
        from tabu.models import TabuProductVariant

        ean_set = {e.strip() for e in ean_list if e and str(e).strip()}
        if not ean_set:
            return []

        qs = TabuProductVariant.objects.filter(ean__in=ean_set).select_related('product')
        if mpd_product_id:
            qs = qs.filter(product__mapped_product_uid=mpd_product_id)

        result = []
        for v in qs:
            ean = (v.ean or '').strip()
            if ean in ean_set:
                result.append(VariantMatch(
                    ean=ean,
                    variant_uid=str(v.api_id),
                    stock=v.store or 0,
                    price=v.price_net or Decimal('0'),
                    currency='PLN',
                    size=v.size or '',
                    color=v.color or '',
                ))
        return result
