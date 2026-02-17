"""
Testy dla saga_variants - create_mpd_variants, delete_mpd_variants, sygnał linkowania
"""
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from matterhorn1.models import Product as MhProduct, ProductVariant as MhProductVariant
from matterhorn1.saga_variants import create_mpd_variants, delete_mpd_variants

from MPD.models import (
    Colors,
    ProductVariants,
    Products,
    ProductvariantsSources,
    Sizes,
    Sources,
    StockAndPrices,
)


def _mpd_db():
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def _mh_db():
    return 'zzz_matterhorn1' if 'zzz_matterhorn1' in settings.DATABASES else 'matterhorn1'


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class CreateMpdVariantsTest(TestCase):
    """Testy create_mpd_variants - ORM, ProductvariantsSources, sygnał"""

    databases = '__all__'

    def setUp(self):
        """Przygotowanie danych: produkt matterhorn1 + MPD (produkt, kolor, rozmiary, źródło)"""
        mpd_db, mh_db = _mpd_db(), _mh_db()

        # Matterhorn1 - produkt i warianty (jawnie .using() dla spójności z create_mpd_variants)
        self.mh_product = MhProduct.objects.using(mh_db).create(
            product_uid=99901,
            name='Test Product MH',
            color='Czerwony',
            prices={'PLN': 99.99},
        )
        self.mh_var1 = MhProductVariant.objects.using(mh_db).create(
            product=self.mh_product,
            variant_uid='100001',  # numeryczny - create_mpd_variants sprawdza duplikaty po variant_uid
            name='S',
            stock=5,
            ean='5901234567890',
        )
        self.mh_var2 = MhProductVariant.objects.using(mh_db).create(
            product=self.mh_product,
            variant_uid='100002',
            name='M',
            stock=10,
            ean='5901234567891',
        )

        # MPD - produkt, kolor, rozmiary, źródło Matterhorn
        self.mpd_product = Products.objects.using(mpd_db).create(
            name='Test Product MPD',
            description='Test',
        )
        self.mpd_color = Colors.objects.using(mpd_db).create(name='Czerwony', hex_code='#FF0000')
        self.mpd_size_s = Sizes.objects.using(mpd_db).create(name='S', category='test_category')
        self.mpd_size_m = Sizes.objects.using(mpd_db).create(name='M', category='test_category')
        self.mpd_source = Sources.objects.using(mpd_db).create(
            name='Matterhorn API',
            type='api',
            location='https://api.matterhorn.pl',
        )

    def test_create_mpd_variants_creates_variants(self):
        """create_mpd_variants tworzy warianty w MPD"""
        result = create_mpd_variants(
            mpd_product_id=self.mpd_product.id,
            matterhorn_product_id=self.mh_product.id,
            size_category='test_category',
            producer_code='PROD001',
        )
        self.assertEqual(result['created_variants'], 2)
        self.assertIn('variant_ids', result)
        self.assertEqual(len(result['variant_ids']), 2)
        self.assertIn('iai_product_id', result)

        pv_count = ProductVariants.objects.using(_mpd_db()).filter(
            product_id=self.mpd_product.id
        ).count()
        self.assertEqual(pv_count, 2)

    def test_create_mpd_variants_creates_productvariants_sources(self):
        """create_mpd_variants tworzy ProductvariantsSources (dzięki czemu sygnał uruchomi task)"""
        result = create_mpd_variants(
            mpd_product_id=self.mpd_product.id,
            matterhorn_product_id=self.mh_product.id,
            size_category='test_category',
        )
        self.assertEqual(result['created_variants'], 2)

        pvs_count = ProductvariantsSources.objects.using(_mpd_db()).filter(
            variant__product_id=self.mpd_product.id,
            source__name__icontains='matterhorn',
        ).count()
        self.assertEqual(pvs_count, 2)

    def test_create_mpd_variants_creates_stock_and_prices(self):
        """create_mpd_variants tworzy StockAndPrices"""
        result = create_mpd_variants(
            mpd_product_id=self.mpd_product.id,
            matterhorn_product_id=self.mh_product.id,
            size_category='test_category',
        )
        self.assertEqual(result['created_variants'], 2)

        sap_count = StockAndPrices.objects.using(_mpd_db()).filter(
            variant__product_id=self.mpd_product.id,
            source__name__icontains='matterhorn',
        ).count()
        self.assertEqual(sap_count, 2)

    def test_create_mpd_variants_updates_matterhorn_mapped_variant_uid(self):
        """create_mpd_variants aktualizuje mapped_variant_uid w matterhorn1"""
        result = create_mpd_variants(
            mpd_product_id=self.mpd_product.id,
            matterhorn_product_id=self.mh_product.id,
            size_category='test_category',
        )
        self.assertEqual(result['created_variants'], 2)

        self.mh_var1.refresh_from_db(using=_mh_db())
        self.mh_var2.refresh_from_db(using=_mh_db())
        self.assertIsNotNone(self.mh_var1.mapped_variant_uid)
        self.assertIsNotNone(self.mh_var2.mapped_variant_uid)
        self.assertTrue(self.mh_var1.is_mapped)
        self.assertTrue(self.mh_var2.is_mapped)

    def test_create_mpd_variants_empty_variants_returns_zero(self):
        """Gdy produkt nie ma wariantów, zwraca created_variants=0"""
        mh_db, mpd_db = _mh_db(), _mpd_db()
        mh_product_empty = MhProduct.objects.using(mh_db).create(
            product_uid=99902,
            name='Product bez wariantów',
            color='Niebieski',
        )
        Colors.objects.using(mpd_db).get_or_create(
            name='Niebieski', defaults={'hex_code': ''}
        )

        result = create_mpd_variants(
            mpd_product_id=self.mpd_product.id,
            matterhorn_product_id=mh_product_empty.id,
            size_category='test_category',
        )
        self.assertEqual(result['created_variants'], 0)
        self.assertEqual(result['variant_ids'], [])

    def test_create_mpd_variants_idempotent_skip_existing(self):
        """Drugie wywołanie dla tych samych wariantów pomija istniejące (variant_uid+source)"""
        create_mpd_variants(
            mpd_product_id=self.mpd_product.id,
            matterhorn_product_id=self.mh_product.id,
            size_category='test_category',
        )
        result2 = create_mpd_variants(
            mpd_product_id=self.mpd_product.id,
            matterhorn_product_id=self.mh_product.id,
            size_category='test_category',
        )
        self.assertEqual(result2['created_variants'], 0)

        pv_count = ProductVariants.objects.using(_mpd_db()).filter(
            product_id=self.mpd_product.id
        ).count()
        self.assertEqual(pv_count, 2)

    def test_create_mpd_variants_signal_triggers_link_task(self):
        """Sygnał post_save na ProductvariantsSources wywołuje task linkowania"""
        with patch('MPD.tasks.link_variants_from_other_sources_task') as mock_task:
            create_mpd_variants(
                mpd_product_id=self.mpd_product.id,
                matterhorn_product_id=self.mh_product.id,
                size_category='test_category',
            )
            self.assertGreaterEqual(
                mock_task.delay.call_count,
                1,
                "Task linkowania powinien być wywołany przy tworzeniu ProductvariantsSources",
            )


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class DeleteMpdVariantsTest(TestCase):
    """Testy delete_mpd_variants"""

    databases = '__all__'

    def setUp(self):
        # Patch task linkowania - przy tworzeniu ProductvariantsSources w setUp
        # sygnał wywołałby task, który mógłby potrzebować Redis
        self._task_patcher = patch('MPD.tasks.link_variants_from_other_sources_task')
        self._task_patcher.start()

        mpd_db = _mpd_db()
        self.mpd_product = Products.objects.using(mpd_db).create(
            name='Test Del', description=''
        )
        self.mpd_color = Colors.objects.using(mpd_db).create(name='Czerwony')
        self.mpd_size = Sizes.objects.using(mpd_db).create(name='S', category='cat')
        self.mpd_source = Sources.objects.using(mpd_db).create(
            name='Matterhorn API', type='api'
        )

        self.pv = ProductVariants.objects.using(mpd_db).create(
            product=self.mpd_product,
            color=self.mpd_color,
            size=self.mpd_size,
        )
        ProductvariantsSources.objects.using(mpd_db).create(
            variant=self.pv,
            source=self.mpd_source,
            ean='5901234567890',
        )
        StockAndPrices.objects.using(mpd_db).create(
            variant=self.pv,
            source=self.mpd_source,
            stock=5,
            price=99.99,
            currency='PLN',
            last_updated=timezone.now(),
        )

    def tearDown(self):
        super().tearDown()
        self._task_patcher.stop()

    def test_delete_mpd_variants_by_ids(self):
        """delete_mpd_variants usuwa warianty po variant_ids"""
        mpd_db = _mpd_db()
        delete_mpd_variants(
            mpd_product_id=self.mpd_product.id,
            variant_ids=[self.pv.variant_id],
        )
        self.assertFalse(
            ProductVariants.objects.using(mpd_db).filter(
                variant_id=self.pv.variant_id
            ).exists()
        )
        self.assertFalse(
            ProductvariantsSources.objects.using(mpd_db).filter(
                variant_id=self.pv.variant_id
            ).exists()
        )
        self.assertFalse(
            StockAndPrices.objects.using(mpd_db).filter(
                variant_id=self.pv.variant_id
            ).exists()
        )

    def test_delete_mpd_variants_by_product(self):
        """delete_mpd_variants bez variant_ids usuwa wszystkie warianty produktu"""
        mpd_db = _mpd_db()
        delete_mpd_variants(mpd_product_id=self.mpd_product.id)
        self.assertFalse(
            ProductVariants.objects.using(mpd_db).filter(
                product_id=self.mpd_product.id
            ).exists()
        )
