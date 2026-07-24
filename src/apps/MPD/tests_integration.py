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

    def test_link_creates_new_mpd_variant_for_extra_size_from_other_source(self):
        """
        Rozmiar 'M' istnieje tylko w Tabu (inny EAN, nieznany jeszcze w MPD) — linking
        powinien dla niego utworzyć NOWY wariant w MPD (backfill "pozostałych" wariantów),
        a nie tylko dopiąć się do istniejącego wariantu 'S'.
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

        variants_after = list(
            ProductVariants.objects.using(mpd_db)
            .filter(product=self.mpd_product)
            .values_list('variant_id', flat=True)
        )
        new_variant_ids = set(variants_after) - variants_before
        self.assertEqual(
            len(new_variant_ids), 1,
            "Powinien powstać dokładnie jeden nowy wariant MPD dla rozmiaru 'M' z Tabu",
        )
        new_variant_id = new_variant_ids.pop()
        pvs = ProductvariantsSources.objects.using(mpd_db).get(
            variant_id=new_variant_id, source=self.tabu_source,
        )
        self.assertEqual(pvs.ean, self.tabu_variant_extra.ean)
