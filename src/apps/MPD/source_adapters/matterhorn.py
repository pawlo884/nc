"""
Adapter dla hurtowni Matterhorn.
"""
import json
import logging
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q

from core.db_routers import _get_matterhorn1_db
from .base import SourceAdapter, VariantMatch, normalize_ean

logger = logging.getLogger(__name__)


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
        # .using() jawnie – automatyczny routing przez DATABASE_ROUTERS bywa niezawodny
        # tylko w normalnym request/shell, w środowisku testowym (manage.py test) łańcuch
        # routerów bywa pusty i zapytanie bez .using() trafia do bazy 'default'.
        qs = ProductVariant.objects.using(_get_matterhorn1_db()).filter(q).select_related('product')
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

        qs = ProductVariant.objects.using(_get_matterhorn1_db()).filter(
            product_id=source_product_id
        ).select_related('product')
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
        """Ustawia mapped_product_uid i is_mapped w Matterhorn Product — pomija nadpisanie,
        jeśli produkt jest już zmapowany do INNEGO produktu MPD (przypadkowy duplikat EAN
        w danych źródłowych nie powinien po cichu przepinać istniejącego mapowania)."""
        from matterhorn1.models import Product

        mh_db = _get_matterhorn1_db()
        product = Product.objects.using(mh_db).filter(id=source_product_id).first()
        if product is None:
            return
        if product.mapped_product_uid is not None and product.mapped_product_uid != mpd_product_id:
            logger.warning(
                "Pomijam nadpisanie mapped_product_uid produktu matterhorn %s: już zmapowany "
                "do %s (próba przepięcia na %s przez dopasowanie EAN)",
                source_product_id, product.mapped_product_uid, mpd_product_id,
            )
            return
        Product.objects.using(mh_db).filter(id=source_product_id).update(
            mapped_product_uid=mpd_product_id,
            is_mapped=True,
        )

    def update_source_variant_mapped(
        self,
        source_product_id: int,
        source_variant_uid: Optional[str],
        mpd_variant_id: int,
    ) -> None:
        """Ustawia mapped_variant_uid w Matterhorn productvariant (po linkowaniu) — pomija
        nadpisanie, jeśli wariant jest już zmapowany do INNEGO wariantu MPD."""
        if not source_variant_uid or not str(source_variant_uid).strip():
            return
        from matterhorn1.models import ProductVariant

        mh_db = _get_matterhorn1_db()
        variant = ProductVariant.objects.using(mh_db).filter(
            product_id=source_product_id,
            variant_uid=str(source_variant_uid).strip(),
        ).first()
        if variant is None:
            return
        if variant.mapped_variant_uid is not None and variant.mapped_variant_uid != mpd_variant_id:
            logger.warning(
                "Pomijam nadpisanie mapped_variant_uid wariantu matterhorn %s: już zmapowany "
                "do %s (próba przepięcia na %s przez dopasowanie EAN)",
                variant.variant_uid, variant.mapped_variant_uid, mpd_variant_id,
            )
            return
        ProductVariant.objects.using(mh_db).filter(pk=variant.pk).update(
            mapped_variant_uid=mpd_variant_id, is_mapped=True,
        )
