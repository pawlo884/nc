"""
Adapter dla hurtowni Matterhorn.
"""
import json
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q

from .base import SourceAdapter, VariantMatch, normalize_ean


class MatterhornAdapter(SourceAdapter):
    source_name = 'Matterhorn'

    def get_variants_by_eans(
        self,
        ean_list: List[str],
        mpd_product_id: Optional[int] = None,
    ) -> List[VariantMatch]:
        """Pobiera warianty Matterhorn po EAN (case-insensitive)."""
        from matterhorn1.models import ProductVariant

        ean_set = {normalize_ean(e) for e in ean_list if e and str(e).strip()}
        if not ean_set:
            return []

        q = Q()
        for e in ean_set:
            q |= Q(ean__iexact=e)
        qs = ProductVariant.objects.filter(q).select_related('product')
        if mpd_product_id:
            qs = qs.filter(product__mapped_product_uid=mpd_product_id)

        result = []
        for v in qs:
            ean_norm = normalize_ean(v.ean)
            if ean_norm in ean_set:
                price = Decimal('0')
                if v.product and v.product.prices:
                    prices = v.product.prices
                    if isinstance(prices, str):
                        prices = json.loads(prices) if prices else {}
                    price = Decimal(str(prices.get('PLN', 0) or 0))

                result.append(VariantMatch(
                    ean=ean_norm,
                    variant_uid=v.variant_uid,
                    stock=v.stock or 0,
                    price=price,
                    currency='PLN',
                    size=v.name or '',
                    color=v.product.color if v.product else '',
                    source_product_id=v.product_id if v.product_id else None,
                    producer_code=getattr(v, 'producer_code', None) and (v.producer_code or '').strip() or None,
                ))
        return result

    def get_all_variants_for_product(
        self,
        source_product_id: int,
    ) -> List[VariantMatch]:
        """Wszystkie warianty produktu Matterhorn (do dopinania pozostałych rozmiarów)."""
        from matterhorn1.models import ProductVariant

        qs = ProductVariant.objects.filter(product_id=source_product_id).select_related('product')
        result = []
        for v in qs:
            ean_norm = normalize_ean(v.ean) if v.ean else ''
            price = Decimal('0')
            if v.product and v.product.prices:
                prices = v.product.prices
                if isinstance(prices, str):
                    prices = json.loads(prices) if prices else {}
                price = Decimal(str(prices.get('PLN', 0) or 0))
            result.append(VariantMatch(
                ean=ean_norm,
                variant_uid=v.variant_uid,
                stock=v.stock or 0,
                price=price,
                currency='PLN',
                size=v.name or '',
                color=v.product.color if v.product else '',
                source_product_id=v.product_id if v.product_id else None,
                producer_code=getattr(v, 'producer_code', None) and (v.producer_code or '').strip() or None,
            ))
        return result

    def update_source_product_mapped(
        self,
        source_product_id: int,
        mpd_product_id: int,
    ) -> None:
        """Ustawia mapped_product_uid i is_mapped w Matterhorn Product."""
        from django.conf import settings
        from matterhorn1.models import Product

        mh_db = 'zzz_matterhorn1' if 'zzz_matterhorn1' in settings.DATABASES else 'matterhorn1'
        Product.objects.using(mh_db).filter(id=source_product_id).update(
            mapped_product_uid=mpd_product_id,
            is_mapped=True,
        )
