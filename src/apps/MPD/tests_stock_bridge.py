"""
Most stanów magazynowych hurtownia -> MPD (#270): `stock_bridge.sync_stock_bridge`
+ taski `update_stock_from_tabu` / `update_stock_from_mada`.

`update_stock_from_matterhorn1` NIE jest tu testowany - to celowo nietknięta,
starsza implementacja (patrz komentarz w MPD/tasks.py).
"""
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.test import TestCase

from mada.models import Brand as MadaBrand, MadaProduct, MadaProductVariant
from MPD.models import (
    Brands,
    Colors,
    ProductVariants,
    Products,
    ProductvariantsSources,
    Sizes,
    Sources,
    StockAndPrices,
    StockHistory,
)
from MPD.stock_bridge import sync_stock_bridge
from MPD.tasks import update_stock_from_mada, update_stock_from_tabu
from tabu.models import Brand as TabuBrand, TabuProduct, TabuProductVariant


def _mpd_db():
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def _tabu_db():
    return 'zzz_tabu' if 'zzz_tabu' in settings.DATABASES else 'tabu'


def _mada_db():
    return 'zzz_mada' if 'zzz_mada' in settings.DATABASES else 'mada'


class _MPDVariantMixin:
    """Tworzy minimalny produkt MPD z jednym wariantem + wpisem ProductvariantsSources."""

    def _make_mpd_variant(self, source, variant_uid):
        mpd_db = _mpd_db()
        brand = Brands.objects.using(mpd_db).create(name='Test Brand')
        color = Colors.objects.using(mpd_db).create(name='Czerwony')
        size = Sizes.objects.using(mpd_db).create(name='M')
        product = Products.objects.using(mpd_db).create(name='Produkt testowy', brand=brand)
        variant = ProductVariants.objects.using(mpd_db).create(
            product=product, color=color, size=size,
        )
        ProductvariantsSources.objects.using(mpd_db).create(
            variant=variant, source=source, variant_uid=variant_uid,
        )
        return variant


class SyncStockBridgeTest(_MPDVariantMixin, TestCase):
    databases = '__all__'

    def setUp(self):
        self.mpd_db = _mpd_db()
        self.source = Sources.objects.using(self.mpd_db).create(
            name='Test API', type='api', location='https://test.example',
        )
        self.variant = self._make_mpd_variant(self.source, variant_uid=1001)

    def test_nowy_wpis_tworzy_stock_and_prices_i_historie(self):
        stats = sync_stock_bridge(
            [(self.variant.variant_id, 7)],
            source_name='Test API', source_type_default='api',
            source_location_default='https://test.example', mpd_db=self.mpd_db,
        )

        sap = StockAndPrices.objects.using(self.mpd_db).get(variant=self.variant, source=self.source)
        self.assertEqual(sap.stock, 7)
        self.assertEqual(stats['created'], 1)
        self.assertEqual(stats['checked'], 1)
        history = StockHistory.objects.using(self.mpd_db).get(stock_id=sap.id)
        self.assertEqual(history.previous_stock, 0)
        self.assertEqual(history.new_stock, 7)

    def test_zmieniony_stan_aktualizuje_i_loguje_historie(self):
        StockAndPrices.objects.using(self.mpd_db).create(
            variant=self.variant, source=self.source, stock=5,
            price=Decimal('0.00'), currency='PLN', last_updated=datetime.now(),
        )

        stats = sync_stock_bridge(
            [(self.variant.variant_id, 12)],
            source_name='Test API', source_type_default='api',
            source_location_default='https://test.example', mpd_db=self.mpd_db,
        )

        sap = StockAndPrices.objects.using(self.mpd_db).get(variant=self.variant, source=self.source)
        self.assertEqual(sap.stock, 12)
        self.assertEqual(stats['updated'], 1)
        history = StockHistory.objects.using(self.mpd_db).get(stock_id=sap.id)
        self.assertEqual(history.previous_stock, 5)
        self.assertEqual(history.new_stock, 12)

    def test_niezmieniony_stan_nic_nie_zapisuje(self):
        """Idempotencja: re-run z tym samym stanem nie tworzy nowego wpisu StockHistory."""
        StockAndPrices.objects.using(self.mpd_db).create(
            variant=self.variant, source=self.source, stock=9,
            price=Decimal('0.00'), currency='PLN', last_updated=datetime.now(),
        )

        stats = sync_stock_bridge(
            [(self.variant.variant_id, 9)],
            source_name='Test API', source_type_default='api',
            source_location_default='https://test.example', mpd_db=self.mpd_db,
        )

        self.assertEqual(stats['unchanged'], 1)
        self.assertEqual(stats['updated'], 0)
        self.assertFalse(StockHistory.objects.using(self.mpd_db).exists())

    def test_brak_productvariantssources_liczony_jako_blad(self):
        stats = sync_stock_bridge(
            [(999999, 3)],
            source_name='Test API', source_type_default='api',
            source_location_default='https://test.example', mpd_db=self.mpd_db,
        )

        self.assertEqual(stats['errors'], 1)
        self.assertIn('999999', stats['error_details'][0])

    def test_brak_zrodla_tworzy_je(self):
        Sources.objects.using(self.mpd_db).filter(name='Nowe API').delete()

        stats = sync_stock_bridge(
            [], source_name='Nowe API', source_type_default='api',
            source_location_default='https://nowe.example', mpd_db=self.mpd_db,
        )

        self.assertEqual(stats['checked'], 0)
        self.assertTrue(
            Sources.objects.using(self.mpd_db).filter(name='Nowe API').exists()
        )


class UpdateStockFromTabuTaskTest(_MPDVariantMixin, TestCase):
    databases = '__all__'

    def setUp(self):
        self.mpd_db = _mpd_db()
        self.tabu_db = _tabu_db()
        self.source = Sources.objects.using(self.mpd_db).create(
            name='Tabu API', type='api', location='https://b2b.tabu.com.pl',
        )
        self.variant = self._make_mpd_variant(self.source, variant_uid=555)

        brand = TabuBrand.objects.using(self.tabu_db).create(brand_id='1', name='Marka Tabu')
        product = TabuProduct.objects.using(self.tabu_db).create(
            api_id=555, symbol='SYM', name='Produkt Tabu', brand=brand, last_update=datetime.now(),
        )
        self.tabu_variant = TabuProductVariant.objects.using(self.tabu_db).create(
            api_id=555, product=product, symbol='SYM-1', store=42,
            mapped_variant_uid=self.variant.variant_id, is_mapped=True,
        )

    def test_zmapowany_wariant_aktualizuje_stock_and_prices(self):
        result = update_stock_from_tabu.apply().get()

        sap = StockAndPrices.objects.using(self.mpd_db).get(variant=self.variant, source=self.source)
        self.assertEqual(sap.stock, 42)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['stats']['checked'], 1)

    def test_niezmapowany_wariant_pomijany(self):
        self.tabu_variant.is_mapped = False
        self.tabu_variant.mapped_variant_uid = None
        self.tabu_variant.save()

        result = update_stock_from_tabu.apply().get()

        self.assertEqual(result['stats']['checked'], 0)
        self.assertFalse(
            StockAndPrices.objects.using(self.mpd_db).filter(variant=self.variant, source=self.source).exists()
        )


class UpdateStockFromMadaTaskTest(_MPDVariantMixin, TestCase):
    databases = '__all__'

    def setUp(self):
        self.mpd_db = _mpd_db()
        self.mada_db = _mada_db()
        self.source = Sources.objects.using(self.mpd_db).create(
            name='Mada API', type='api', location='https://www.mada.pl',
        )
        self.variant = self._make_mpd_variant(self.source, variant_uid=777)

        brand = MadaBrand.objects.using(self.mada_db).create(producer_id='1', name='Marka Mada')
        product = MadaProduct.objects.using(self.mada_db).create(
            api_id=777, name='Produkt Mada', brand=brand,
        )
        self.mada_variant = MadaProductVariant.objects.using(self.mada_db).create(
            product=product, variant_key='EAN777', stock=17,
            mapped_variant_uid=self.variant.variant_id, is_mapped=True,
        )

    def test_zmapowany_wariant_aktualizuje_stock_and_prices(self):
        result = update_stock_from_mada.apply().get()

        sap = StockAndPrices.objects.using(self.mpd_db).get(variant=self.variant, source=self.source)
        self.assertEqual(sap.stock, 17)
        self.assertEqual(result['status'], 'success')

    def test_niezmapowany_wariant_pomijany(self):
        self.mada_variant.is_mapped = False
        self.mada_variant.mapped_variant_uid = None
        self.mada_variant.save()

        result = update_stock_from_mada.apply().get()

        self.assertEqual(result['stats']['checked'], 0)
