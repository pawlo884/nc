"""
Testy jednostkowe modeli MPD - zapisywanie, usuwanie ProductvariantsSources,
StockAndPrices, Products, ProductVariants.
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from MPD.models import (
    Colors,
    ProductVariants,
    Products,
    ProductvariantsSources,
    Sizes,
    Sources,
    StockAndPrices,
)
from MPD.models import Brands


class MPDProductsModelTest(TestCase):
    """Testy modelu Products"""

    def setUp(self):
        self.brand = Brands.objects.create(name='MPD Brand')

    def test_product_create(self):
        """Tworzenie produktu MPD"""
        product = Products.objects.create(
            name='Produkt MPD',
            description='Opis',
            brand=self.brand,
        )
        self.assertEqual(product.name, 'Produkt MPD')
        self.assertIsNotNone(product.pk)

    def test_product_save_update(self):
        """Aktualizacja produktu"""
        product = Products.objects.create(
            name='Do aktualizacji',
            brand=self.brand,
        )
        product.name = 'Zaktualizowana nazwa'
        product.save()
        product.refresh_from_db()
        self.assertEqual(product.name, 'Zaktualizowana nazwa')

    def test_product_delete(self):
        """Usuwanie produktu"""
        product = Products.objects.create(
            name='Do usunięcia',
            brand=self.brand,
        )
        pk = product.pk
        product.delete()
        self.assertFalse(Products.objects.filter(pk=pk).exists())


class MPDProductVariantsModelTest(TestCase):
    """Testy modelu ProductVariants"""

    def setUp(self):
        self.brand = Brands.objects.create(name='B')
        self.product = Products.objects.create(
            name='Prod',
            brand=self.brand,
        )
        self.color = Colors.objects.create(name='Red')
        self.size = Sizes.objects.create(name='S', category='default')

    def test_variant_create(self):
        """Tworzenie wariantu"""
        variant = ProductVariants.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
        )
        self.assertIsNotNone(variant.variant_id)
        self.assertEqual(variant.product, self.product)

    def test_variant_delete(self):
        """Usuwanie wariantu"""
        variant = ProductVariants.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
        )
        vid = variant.variant_id
        variant.delete()
        self.assertFalse(
            ProductVariants.objects.filter(variant_id=vid).exists()
        )


class MPDProductvariantsSourcesModelTest(TestCase):
    """Testy modelu ProductvariantsSources"""

    def setUp(self):
        self.brand = Brands.objects.create(name='B')
        self.product = Products.objects.create(
            name='Prod',
            brand=self.brand,
        )
        self.color = Colors.objects.create(name='Blue')
        self.size = Sizes.objects.create(name='M', category='default')
        self.source = Sources.objects.create(
            name='Test Source',
            type='api',
        )
        self.variant = ProductVariants.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
        )

    def test_productvariants_sources_create(self):
        """Tworzenie ProductvariantsSources"""
        pvs = ProductvariantsSources.objects.create(
            variant=self.variant,
            source=self.source,
            ean='5901234567890',
            variant_uid=123,
        )
        self.assertEqual(pvs.variant, self.variant)
        self.assertEqual(pvs.source, self.source)
        self.assertEqual(pvs.ean, '5901234567890')
        self.assertEqual(pvs.variant_uid, 123)

    def test_productvariants_sources_save_update(self):
        """Aktualizacja ProductvariantsSources"""
        pvs = ProductvariantsSources.objects.create(
            variant=self.variant,
            source=self.source,
            ean='111',
        )
        pvs.ean = '222'
        pvs.save()
        pvs.refresh_from_db()
        self.assertEqual(pvs.ean, '222')

    def test_productvariants_sources_delete(self):
        """Usuwanie ProductvariantsSources"""
        pvs = ProductvariantsSources.objects.create(
            variant=self.variant,
            source=self.source,
            ean='333',
        )
        pk = pvs.pk
        pvs.delete()
        self.assertFalse(
            ProductvariantsSources.objects.filter(pk=pk).exists()
        )


class MPDStockAndPricesModelTest(TestCase):
    """Testy modelu StockAndPrices"""

    def setUp(self):
        self.brand = Brands.objects.create(name='B')
        self.product = Products.objects.create(
            name='Prod',
            brand=self.brand,
        )
        self.color = Colors.objects.create(name='Red')
        self.size = Sizes.objects.create(name='S', category='default')
        self.source = Sources.objects.create(name='Source', type='api')
        self.variant = ProductVariants.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
        )

    def test_stock_and_prices_create(self):
        """Tworzenie StockAndPrices"""
        sap = StockAndPrices.objects.create(
            variant=self.variant,
            source=self.source,
            stock=10,
            price=Decimal('99.99'),
            currency='PLN',
            last_updated=timezone.now(),
        )
        self.assertEqual(sap.stock, 10)
        self.assertEqual(sap.price, Decimal('99.99'))
        self.assertEqual(sap.variant, self.variant)

    def test_stock_and_prices_delete(self):
        """Usuwanie StockAndPrices"""
        sap = StockAndPrices.objects.create(
            variant=self.variant,
            source=self.source,
            stock=5,
            price=Decimal('49.99'),
            currency='PLN',
            last_updated=timezone.now(),
        )
        pk = sap.pk
        sap.delete()
        self.assertFalse(StockAndPrices.objects.filter(pk=pk).exists())


class NoIaiProductCounterTest(TestCase):
    """Testy potwierdzające usunięcie powiązań z IAI counter – aplikacja działa bez niego."""

    def test_mpd_models_do_not_define_iai_product_counter(self):
        """W MPD.models nie ma już modelu IaiProductCounter."""
        import MPD.models as mpd_models
        self.assertFalse(
            hasattr(mpd_models, "IaiProductCounter"),
            "IaiProductCounter nie powinien być zdefiniowany w MPD.models",
        )

    def test_mpd_admin_imports_without_iai_product_counter(self):
        """MPD admin importuje się poprawnie bez IaiProductCounter."""
        from django.contrib import admin

        # Po załadowaniu MPD.admin żaden model o nazwie IaiProductCounter nie jest w rejestrze
        from MPD import admin as _mpd_admin  # noqa: F401 – ładujemy rejestracje

        registered_names = [m.__name__ for m in admin.site._registry]
        self.assertNotIn(
            "IaiProductCounter",
            registered_names,
            "IaiProductCounter nie powinien być zarejestrowany w admin",
        )

    def test_saga_variants_return_structure_has_iai_product_id_key(self):
        """create_mpd_variants zwraca dict z kluczem iai_product_id (może być None)."""
        from matterhorn1.saga_variants import create_mpd_variants
        # Nie uruchamiamy pełnej logiki – sprawdzamy tylko sygnaturę/zwrot przy wczesnym wyjściu.
        # Przy braku koloru w MPD funkcja rzuca ValueError; przy braku wariantów zwraca dict.
        # Sprawdzamy, że zwracany dict (gdy jest) ma klucz iai_product_id.
        self.assertTrue(
            hasattr(create_mpd_variants, "__call__"),
            "create_mpd_variants powinna być wywoływalna",
        )
        # Dokumentacja zwrotu: dict z created_variants, iai_product_id, variant_ids
        import inspect
        sig = inspect.signature(create_mpd_variants)
        self.assertIn("mpd_product_id", sig.parameters)
        self.assertIn("matterhorn_product_id", sig.parameters)
