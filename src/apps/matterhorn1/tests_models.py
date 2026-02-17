"""
Testy jednostkowe modeli Matterhorn1 - zapisywanie, usuwanie, relacje.
"""
from django.test import TestCase

from matterhorn1.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
)


class MatterhornBrandModelTest(TestCase):
    """Testy modelu Brand"""

    def test_brand_create(self):
        """Tworzenie marki"""
        brand = Brand.objects.create(
            brand_id='MH_BRAND_001',
            name='Test Brand MH',
        )
        self.assertEqual(brand.brand_id, 'MH_BRAND_001')
        self.assertIsNotNone(brand.pk)

    def test_brand_save_update(self):
        """Aktualizacja marki"""
        brand = Brand.objects.create(brand_id='MH_B002', name='Old')
        brand.name = 'Updated'
        brand.save()
        brand.refresh_from_db()
        self.assertEqual(brand.name, 'Updated')

    def test_brand_delete(self):
        """Usuwanie marki"""
        brand = Brand.objects.create(brand_id='MH_B003', name='Del')
        pk = brand.pk
        brand.delete()
        self.assertFalse(Brand.objects.filter(pk=pk).exists())


class MatterhornProductModelTest(TestCase):
    """Testy modelu Product"""

    def setUp(self):
        self.brand = Brand.objects.create(
            brand_id='MH_PROD_BRAND',
            name='Brand',
        )
        self.category = Category.objects.create(
            category_id='MH_PROD_CAT',
            name='Cat',
            path='/cat',
        )

    def test_product_create(self):
        """Tworzenie produktu"""
        product = Product.objects.create(
            product_uid=88801,
            name='Produkt MH',
            brand=self.brand,
            category=self.category,
        )
        self.assertEqual(product.product_uid, 88801)
        self.assertIsNone(product.mapped_product_uid)
        self.assertFalse(product.is_mapped)

    def test_product_save_mapped_product_uid(self):
        """Zapis mapped_product_uid i is_mapped"""
        product = Product.objects.create(
            product_uid=88802,
            name='Mapowanie',
            brand=self.brand,
        )
        product.mapped_product_uid = 456
        product.is_mapped = True
        product.save()
        product.refresh_from_db()
        self.assertEqual(product.mapped_product_uid, 456)
        self.assertTrue(product.is_mapped)

    def test_product_delete(self):
        """Usuwanie produktu"""
        product = Product.objects.create(
            product_uid=88803,
            name='Do usunięcia',
            brand=self.brand,
        )
        pk = product.pk
        product.delete()
        self.assertFalse(Product.objects.filter(pk=pk).exists())

    def test_product_stock_total(self):
        """stock_total z wariantów"""
        product = Product.objects.create(
            product_uid=88804,
            name='Ze stanem',
            brand=self.brand,
        )
        ProductVariant.objects.create(
            product=product,
            variant_uid='V001',
            name='S',
            stock=5,
        )
        ProductVariant.objects.create(
            product=product,
            variant_uid='V002',
            name='M',
            stock=10,
        )
        self.assertEqual(product.stock_total, 15)


class MatterhornProductVariantModelTest(TestCase):
    """Testy modelu ProductVariant"""

    def setUp(self):
        self.brand = Brand.objects.create(brand_id='MH_VAR_BR', name='B')
        self.product = Product.objects.create(
            product_uid=77701,
            name='Produkt',
            brand=self.brand,
        )

    def test_variant_create(self):
        """Tworzenie wariantu"""
        var = ProductVariant.objects.create(
            product=self.product,
            variant_uid='MH_VAR_001',
            name='S',
            stock=3,
            ean='5901234567890',
        )
        self.assertEqual(var.variant_uid, 'MH_VAR_001')
        self.assertIsNone(var.mapped_variant_uid)

    def test_variant_save_mapped_variant_uid(self):
        """Zapis mapped_variant_uid"""
        var = ProductVariant.objects.create(
            product=self.product,
            variant_uid='MH_VAR_002',
            name='M',
            stock=0,
        )
        var.mapped_variant_uid = 999
        var.is_mapped = True
        var.save()
        var.refresh_from_db()
        self.assertEqual(var.mapped_variant_uid, 999)
        self.assertTrue(var.is_mapped)

    def test_variant_delete(self):
        """Usuwanie wariantu"""
        var = ProductVariant.objects.create(
            product=self.product,
            variant_uid='MH_VAR_003',
            name='L',
            stock=0,
        )
        pk = var.pk
        var.delete()
        self.assertFalse(ProductVariant.objects.filter(pk=pk).exists())
