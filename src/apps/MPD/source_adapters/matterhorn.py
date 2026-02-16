"""
Adapter dla hurtowni Matterhorn.
"""
import json
from decimal import Decimal
from typing import List, Optional

from .base import SourceAdapter, VariantMatch


class MatterhornAdapter(SourceAdapter):
    source_name = 'Matterhorn'

    def get_variants_by_eans(
        self,
        ean_list: List[str],
        mpd_product_id: Optional[int] = None,
    ) -> List[VariantMatch]:
        """Pobiera warianty Matterhorn po EAN."""
        from matterhorn1.models import ProductVariant

        ean_set = {e.strip() for e in ean_list if e and str(e).strip()}
        if not ean_set:
            return []

        qs = ProductVariant.objects.filter(ean__in=ean_set).select_related('product')
        if mpd_product_id:
            qs = qs.filter(product__mapped_product_uid=mpd_product_id)

        result = []
        for v in qs:
            ean = (v.ean or '').strip()
            if ean in ean_set:
                price = Decimal('0')
                if v.product and v.product.prices:
                    prices = v.product.prices
                    if isinstance(prices, str):
                        prices = json.loads(prices) if prices else {}
                    price = Decimal(str(prices.get('PLN', 0) or 0))

                result.append(VariantMatch(
                    ean=ean,
                    variant_uid=v.variant_uid,
                    stock=v.stock or 0,
                    price=price,
                    currency='PLN',
                    size=v.name or '',
                    color=v.product.color if v.product else '',
                ))
        return result
