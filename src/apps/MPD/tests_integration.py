"""
Testy integracyjne - zapis do MPD i propagacja do Tabu/Matterhorn.

Weryfikują że:
- Przy usunięciu produktu MPD sygnał czyści mapped_product_uid w Tabu i Matterhorn
- Przy dopinaniu wariantów (linkowanie) mapped_product_uid jest ustawiany w hurtowniach
"""
from datetime import datetime

from django.conf import settings
from django.test import TestCase, override_settings

from MPD.models import (
    Brands,
    Colors,
    ProductVariants,
    Products,
    ProductvariantsSources,
    Sizes,
    Sources,
)
from matterhorn1.models import Product as MhProduct
from tabu.models import TabuProduct, TabuProductVariant, Brand as TabuBrand


def _mpd_db():
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def _mh_db():
    return 'zzz_matterhorn1' if 'zzz_matterhorn1' in settings.DATABASES else 'matterhorn1'


def _tabu_db():
    return 'zzz_tabu' if 'zzz_tabu' in settings.DATABASES else 'tabu'


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class MPDDeletePropagatesToHurtownieTest(TestCase):
    """
    Usunięcie produktu MPD -> sygnał czyści mapped_product_uid w Matterhorn i Tabu.
    """

    databases = '__all__'

    def setUp(self):
        mpd_db = _mpd_db()
        mh_db = _mh_db()
        tabu_db = _tabu_db()

        # Produkt MPD
        brand = Brands.objects.using(mpd_db).create(name='Test Brand')
        self.mpd_product = Products.objects.using(mpd_db).create(
            name='Produkt do usunięcia',
            brand=brand,
        )

        # Produkt Matterhorn z mapowaniem
        from matterhorn1.models import Brand as MhBrand
        mh_brand_obj = MhBrand.objects.using(mh_db).create(
            brand_id='MH_INT_BRAND',
            name='MH Brand',
        )
        self.mh_product = MhProduct.objects.using(mh_db).create(
            product_uid=50001,
            name='MH Product',
            brand=mh_brand_obj,
            mapped_product_uid=self.mpd_product.id,
            is_mapped=True,
        )

        # Produkt Tabu z mapowaniem
        TabuBrand.objects.using(tabu_db).create(
            brand_id='TABU_INT_BR',
            name='Tabu Brand',
        )
        self.tabu_product = TabuProduct.objects.using(tabu_db).create(
            api_id=60001,
            symbol='INT-001',
            name='Tabu Product',
            last_update=datetime.now(),
            mapped_product_uid=self.mpd_product.id,
        )

    def test_delete_mpd_product_clears_matterhorn_mapping(self):
        """Usunięcie produktu MPD czyści mapped_product_uid w Matterhorn"""
        mpd_db = _mpd_db()
        mh_db = _mh_db()

        self.mpd_product.delete(using=mpd_db)

        self.mh_product.refresh_from_db(using=mh_db)
        self.assertIsNone(self.mh_product.mapped_product_uid)
        self.assertFalse(self.mh_product.is_mapped)

    def test_delete_mpd_product_clears_tabu_mapping(self):
        """Usunięcie produktu MPD czyści mapped_product_uid w Tabu"""
        mpd_db = _mpd_db()
        tabu_db = _tabu_db()

        self.mpd_product.delete(using=mpd_db)

        self.tabu_product.refresh_from_db(using=tabu_db)
        self.assertIsNone(self.tabu_product.mapped_product_uid)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class MPDSavePropagatesLinkTest(TestCase):
    """
    Zapis ProductvariantsSources w MPD -> task linkowania dopina warianty
    z innych hurtowni (Tabu/Matterhorn) i ustawia mapped_product_uid.

    Wymaga adapterów - mockujemy lub używamy prawdziwych z pełnymi danymi.
    """

    databases = '__all__'

    def setUp(self):
        mpd_db = _mpd_db()
        tabu_db = _tabu_db()

        # Źródła MPD
        self.mh_source = Sources.objects.using(mpd_db).create(
            name='Matterhorn API',
            type='api',
        )
        self.tabu_source = Sources.objects.using(mpd_db).create(
            name='Tabu API',
            type='api',
        )

        # Produkt MPD + wariant
        brand = Brands.objects.using(mpd_db).create(name='B')
        self.mpd_product = Products.objects.using(mpd_db).create(
            name='MPD Link Test',
            brand=brand,
        )
        color = Colors.objects.using(mpd_db).create(name='Red')
        size = Sizes.objects.using(mpd_db).create(name='S', category='default')
        self.mpd_variant = ProductVariants.objects.using(mpd_db).create(
            product=self.mpd_product,
            color=color,
            size=size,
        )
        self.ean = '5901234567899'

        # ProductvariantsSources z Matterhorn (mamy już jeden źródło)
        ProductvariantsSources.objects.using(mpd_db).create(
            variant=self.mpd_variant,
            source=self.mh_source,
            ean=self.ean,
            variant_uid=70001,
        )

        # Produkt Tabu z wariantem o tym samym EAN (żeby link mógł dopiąć — adapter Tabu
        # dopasowuje po EAN WARIANTU, nie produktu, więc TabuProductVariant jest tu konieczny)
        TabuBrand.objects.using(tabu_db).create(
            brand_id='TABU_LINK',
            name='Tabu Link',
        )
        self.tabu_product = TabuProduct.objects.using(tabu_db).create(
            api_id=70001,
            symbol='LINK-001',
            name='Tabu do linkowania',
            last_update=datetime.now(),
        )
        self.tabu_variant = TabuProductVariant.objects.using(tabu_db).create(
            api_id=70001,
            product=self.tabu_product,
            symbol='LINK-001-S',
            ean=self.ean,
            size='S',
            store=5,
        )
        # Dodatkowy rozmiar w Tabu, którego MPD jeszcze nie zna (inny EAN) — test
        # ścieżki "pozostałe warianty" (backfill nowego wariantu w MPD)
        self.tabu_variant_extra = TabuProductVariant.objects.using(tabu_db).create(
            api_id=70002,
            product=self.tabu_product,
            symbol='LINK-001-M',
            ean='5901234567900',
            size='M',
            store=3,
        )

    def test_link_sets_mapped_product_uid_in_tabu(self):
        """
        link_variants_from_other_sources - gdy Tabu ma wariant z tym EAN,
        dopina go do istniejącego wariantu MPD i ustawia mapped_product_uid.
        Adapter Tabu zwraca VariantMatch z source_product_id.
        """
        from MPD.source_adapters.linking import link_variants_from_other_sources
        from MPD.models import ProductvariantsSources

        result = link_variants_from_other_sources(
            mpd_product_id=self.mpd_product.id,
            current_source_id=self.mh_source.id,
        )

        self.assertEqual(result['errors'], [])
        self.assertGreater(
            result['linked_count'], 0,
            "linking powinien dopiąć przynajmniej jeden wariant Tabu po EAN",
        )

        self.tabu_product.refresh_from_db(using=_tabu_db())
        self.assertEqual(
            self.tabu_product.mapped_product_uid,
            self.mpd_product.id,
            "mapped_product_uid powinien być ustawiony po linkowaniu",
        )
        self.assertTrue(
            ProductvariantsSources.objects.using(_mpd_db()).filter(
                variant=self.mpd_variant, source=self.tabu_source,
            ).exists(),
            "Powinien powstać wiersz ProductvariantsSources dla wariantu MPD ze źródłem Tabu",
        )

    def test_link_does_not_create_mpd_variant_for_unmatched_ean(self):
        """
        Rozmiar 'M' istnieje tylko w Tabu (inny EAN, nieznany w MPD). Linking dopina
        WYŁĄCZNIE po EAN — nie tworzy nowych wariantów MPD dla nietrafionych EAN-ów
        (hurtownia potrafi trzymać kilka kolorów pod jednym produktem, a nazwy kolorów
        bywają rozjechane). Takie warianty trafiają do panelu „nieprzypisane".
        """
        from MPD.source_adapters.linking import link_variants_from_other_sources
        from MPD.models import ProductvariantsSources

        mpd_db = _mpd_db()
        variants_before = set(
            ProductVariants.objects.using(mpd_db)
            .filter(product=self.mpd_product)
            .values_list('variant_id', flat=True)
        )

        link_variants_from_other_sources(
            mpd_product_id=self.mpd_product.id,
            current_source_id=self.mh_source.id,
        )

        variants_after = set(
            ProductVariants.objects.using(mpd_db)
            .filter(product=self.mpd_product)
            .values_list('variant_id', flat=True)
        )
        self.assertEqual(
            variants_after, variants_before,
            "Linking nie powinien tworzyć nowych wariantów MPD dla nietrafionych EAN-ów",
        )
        # Rozmiar 'S' (ten sam EAN) nadal dopięty do istniejącego wariantu
        self.assertTrue(
            ProductvariantsSources.objects.using(mpd_db).filter(
                variant=self.mpd_variant, source=self.tabu_source,
            ).exists()
        )
        # Rozmiar 'M' (inny EAN) NIE został nigdzie dopięty
        self.assertFalse(
            ProductvariantsSources.objects.using(mpd_db).filter(
                source=self.tabu_source, ean=self.tabu_variant_extra.ean,
            ).exists()
        )

    def test_get_unmapped_variants_returns_orphaned_tabu_variant(self):
        """
        Po zlinkowaniu po EAN wariant 'M' z Tabu (nietrafiony EAN, ten sam produkt
        źródłowy zmapowany po 'S') jest zwracany jako „nieprzypisany" (orphaned).
        """
        from MPD.source_adapters.linking import link_variants_from_other_sources
        from MPD.source_adapters.registry import get_adapter_for_source

        link_variants_from_other_sources(
            mpd_product_id=self.mpd_product.id,
            current_source_id=self.mh_source.id,
        )

        adapter = get_adapter_for_source(self.tabu_source.id)
        orphans = adapter.get_unmapped_variants_for_mpd_product(self.mpd_product.id)
        orphan_eans = {o.ean for o in orphans}
        self.assertIn(self.tabu_variant_extra.ean, orphan_eans)
        self.assertNotIn(self.ean, orphan_eans)


class VariantUidIntTest(TestCase):
    """`_variant_uid_int` chroni kolumnę PG integer (32-bit) przed przepełnieniem —
    identyfikatory hurtowni oparte na EAN (np. Mada variant_key = 13 cyfr) → null."""

    def test_clamps_values_outside_pg_integer_range(self):
        from MPD.source_adapters.linking import _variant_uid_int

        class M:
            def __init__(self, uid):
                self.variant_uid = uid

        self.assertEqual(_variant_uid_int(M('19410')), 19410)
        self.assertIsNone(_variant_uid_int(M('5902771173479')))  # 13-cyfrowy EAN
        self.assertIsNone(_variant_uid_int(M('GOS-BIU-105B')))
        self.assertIsNone(_variant_uid_int(M(None)))
