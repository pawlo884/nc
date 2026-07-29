"""
Testy jednostkowe modeli Mada - zapisywanie, usuwanie, relacje.
"""
from decimal import Decimal

from django.test import TestCase

from mada.models import Brand, Category, MadaProduct, MadaProductImage, MadaProductVariant


class BrandModelTest(TestCase):
    def test_brand_create(self):
        brand = Brand.objects.create(producer_id='110', name='Gatta')
        self.assertEqual(brand.producer_id, '110')
        self.assertIsNotNone(brand.pk)

    def test_brand_str(self):
        brand = Brand.objects.create(producer_id='43', name='Golden Lady')
        self.assertIn('Golden Lady', str(brand))
        self.assertIn('43', str(brand))

    def test_brand_producer_id_unique(self):
        Brand.objects.create(producer_id='1', name='A')
        with self.assertRaises(Exception):
            Brand.objects.create(producer_id='1', name='B')


class CategoryModelTest(TestCase):
    def test_category_parent_relation(self):
        parent = Category.objects.create(category_id='30', name='Rajstopy')
        child = Category.objects.create(category_id='30-63', name='Rajstopy / lycra', parent=parent)
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())


class MadaProductModelTest(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(producer_id='110', name='Gatta')
        self.category = Category.objects.create(category_id='30-63', name='Rajstopy / lycra')

    def test_product_create_with_defaults(self):
        product = MadaProduct.objects.create(
            api_id=161, name='Rajstopy Gatta Estella', brand=self.brand, category=self.category,
            price=Decimal('12.04'), vat=Decimal('23'),
        )
        self.assertTrue(product.is_active)
        self.assertIsNone(product.mapped_product_uid)
        self.assertEqual(product.raw_data, {})

    def test_product_str(self):
        product = MadaProduct.objects.create(api_id=161, name='Rajstopy', price=Decimal('1'))
        self.assertIn('Rajstopy', str(product))
        self.assertIn('161', str(product))

    def test_product_api_id_unique(self):
        MadaProduct.objects.create(api_id=1, name='A', price=Decimal('1'))
        with self.assertRaises(Exception):
            MadaProduct.objects.create(api_id=1, name='B', price=Decimal('1'))


class MadaProductVariantModelTest(TestCase):
    def setUp(self):
        self.product = MadaProduct.objects.create(api_id=161, name='Rajstopy', price=Decimal('12.04'))

    def test_variant_create_and_cascade_delete(self):
        variant = MadaProductVariant.objects.create(
            product=self.product, variant_key='000223000290',
            color='nero/czarny', size='2-S', ean='000223000290', stock=43,
        )
        self.assertEqual(variant.product, self.product)
        self.product.delete()
        self.assertFalse(MadaProductVariant.objects.filter(pk=variant.pk).exists())

    def test_variant_key_unique_per_product(self):
        MadaProductVariant.objects.create(product=self.product, variant_key='k1', stock=1)
        with self.assertRaises(Exception):
            MadaProductVariant.objects.create(product=self.product, variant_key='k1', stock=2)


class MadaProductImageModelTest(TestCase):
    def test_image_cascade_delete(self):
        product = MadaProduct.objects.create(api_id=1, name='A', price=Decimal('1'))
        image = MadaProductImage.objects.create(
            product=product, api_image_id='305045', image_url='https://www.mada.pl/img/1.jpg',
        )
        product.delete()
        self.assertFalse(MadaProductImage.objects.filter(pk=image.pk).exists())
