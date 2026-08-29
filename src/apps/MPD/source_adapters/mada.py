"""
Adapter dla hurtowni Mada.

Mapowanie na product_variants_sources:
- variant_uid = variant_key z mada_product_variant (EAN gdy dostępny, w przeciwnym
  razie "color|size" - feed Mada nie nadaje wariantom osobnego numerycznego id)
- producer_code = brak jednoznacznego odpowiednika w feedzie Mada, zostaje None
"""
import logging
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q

from core.db_routers import _get_mada_db
from .base import SourceAdapter, VariantMatch, normalize_ean

logger = logging.getLogger(__name__)


class MadaAdapter(SourceAdapter):
    source_name = 'Mada API'

    def get_variants_by_eans(
        self,
        ean_list: List[str],
        mpd_product_id: Optional[int] = None,
    ) -> List[VariantMatch]:
        """Pobiera warianty Mada po EAN (case-insensitive)."""
        from mada.models import MadaProductVariant

        ean_set = {normalize_ean(e) for e in ean_list if e and str(e).strip()}
        if not ean_set:
            return []

        q = Q()
        for e in ean_set:
            q |= Q(ean__iexact=e)
        qs = MadaProductVariant.objects.using(_get_mada_db()).filter(q).select_related('product')
        if mpd_product_id:
            qs = qs.filter(product__mapped_product_uid=mpd_product_id)

        result = []
        for v in qs:
            ean_norm = normalize_ean(v.ean)
            if ean_norm in ean_set:
                result.append(VariantMatch(
                    ean=ean_norm,
                    variant_uid=v.variant_key,
                    stock=v.stock or 0,
                    price=v.product.price if v.product_id else Decimal('0'),
                    currency='PLN',
                    size=v.size or '',
                    color=v.color or '',
                    source_product_id=v.product_id if v.product_id else None,
                    producer_code=None,
                ))
        return result

    def get_all_variants_for_product(
        self,
        source_product_id: int,
    ) -> List[VariantMatch]:
        """Wszystkie warianty produktu Mada (do dopinania pozostałych rozmiarów)."""
        from mada.models import MadaProductVariant

        qs = MadaProductVariant.objects.using(_get_mada_db()).filter(
            product_id=source_product_id
        ).select_related('product')
        result = []
        for v in qs:
            ean_norm = normalize_ean(v.ean) if v.ean else ''
            result.append(VariantMatch(
                ean=ean_norm,
                variant_uid=v.variant_key,
                stock=v.stock or 0,
                price=v.product.price if v.product_id else Decimal('0'),
                currency='PLN',
                size=v.size or '',
                color=v.color or '',
                source_product_id=v.product_id if v.product_id else None,
                producer_code=None,
            ))
        return result

    def get_unmapped_variants_for_mpd_product(
        self,
        mpd_product_id: int,
    ) -> List[VariantMatch]:
        """Warianty Mada z produktów zmapowanych do tego MPD, bez przypisania do wariantu MPD."""
        from mada.models import MadaProductVariant

        qs = MadaProductVariant.objects.using(_get_mada_db()).filter(
            product__mapped_product_uid=mpd_product_id,
            mapped_variant_uid__isnull=True,
        ).select_related('product')
        result = []
        for v in qs:
            result.append(VariantMatch(
                ean=normalize_ean(v.ean) if v.ean else '',
                variant_uid=v.variant_key,
                stock=v.stock or 0,
                price=v.product.price if v.product_id else Decimal('0'),
                currency='PLN',
                size=v.size or '',
                color=v.color or '',
                source_product_id=v.product_id if v.product_id else None,
                producer_code=None,
            ))
        return result

    def get_gallery_images_for_mpd_product(self, mpd_product_id: int) -> List[dict]:
        """Zdjęcia produktów Mada zmapowanych do tego MPD."""
        from mada.models import MadaProduct, MadaProductImage

        product_ids = list(
            MadaProduct.objects.using(_get_mada_db())
            .filter(mapped_product_uid=mpd_product_id)
            .values_list('id', flat=True)
        )
        if not product_ids:
            return []

        images: List[dict] = []
        seen = set()
        for mi in MadaProductImage.objects.using(_get_mada_db()).filter(
            product_id__in=product_ids
        ).order_by('order', 'api_image_id'):
            if mi.image_url and mi.image_url not in seen:
                seen.add(mi.image_url)
                images.append({
                    'url': mi.image_url,
                    'is_main': mi.order == 0,
                    'order': mi.order or 0,
                })
        return images

    def update_source_product_mapped(
        self,
        source_product_id: int,
        mpd_product_id: int,
    ) -> None:
        """Ustawia mapped_product_uid w Mada MadaProduct — pomija nadpisanie, jeśli produkt
        jest już zmapowany do INNEGO produktu MPD."""
        from mada.models import MadaProduct

        mada_db = _get_mada_db()
        product = MadaProduct.objects.using(mada_db).filter(id=source_product_id).first()
        if product is None:
            return
        if product.mapped_product_uid is not None and product.mapped_product_uid != mpd_product_id:
            logger.warning(
                "Pomijam nadpisanie mapped_product_uid produktu mada %s: już zmapowany "
                "do %s (próba przepięcia na %s przez dopasowanie EAN)",
                source_product_id, product.mapped_product_uid, mpd_product_id,
            )
            return
        MadaProduct.objects.using(mada_db).filter(id=source_product_id).update(
            mapped_product_uid=mpd_product_id,
        )

    def update_source_variant_mapped(
        self,
        source_product_id: int,
        source_variant_uid: Optional[str],
        mpd_variant_id: int,
    ) -> None:
        """Ustawia mapped_variant_uid i is_mapped w Mada MadaProductVariant — pomija
        nadpisanie, jeśli wariant jest już zmapowany do INNEGO wariantu MPD."""
        if not source_variant_uid or not str(source_variant_uid).strip():
            return
        from mada.models import MadaProductVariant

        mada_db = _get_mada_db()
        variant = MadaProductVariant.objects.using(mada_db).filter(
            product_id=source_product_id,
            variant_key=source_variant_uid.strip(),
        ).first()
        if variant is None:
            return
        if variant.mapped_variant_uid is not None and variant.mapped_variant_uid != mpd_variant_id:
            logger.warning(
                "Pomijam nadpisanie mapped_variant_uid wariantu mada %s: już zmapowany "
                "do %s (próba przepięcia na %s przez dopasowanie EAN)",
                source_variant_uid, variant.mapped_variant_uid, mpd_variant_id,
            )
            return
        MadaProductVariant.objects.using(mada_db).filter(pk=variant.pk).update(
            mapped_variant_uid=mpd_variant_id, is_mapped=True,
        )
