"""
Testy jednostkowe modeli Tabu - zapisywanie, usuwanie, relacje.
"""
from django.test import TestCase
from django.utils import timezone

from tabu.models import Brand, Category, TabuProduct


class TabuBrandModelTest(TestCase):
    """Testy modelu Brand"""

    def test_brand_create(self):
        """Tworzenie marki"""
        brand = Brand.objects.create(
            brand_id='TABU_BRAND_001',
            name='Test Brand Tabu',
        )
        self.assertEqual(brand.brand_id, 'TABU_BRAND_001')
        self.assertEqual(brand.name, 'Test Brand Tabu')
        self.assertIsNotNone(brand.pk)
        self.assertIsNotNone(brand.created_at)

    def test_brand_save_update(self):
        """Aktualizacja marki"""
        brand = Brand.objects.create(brand_id='B002', name='Old Name')
        brand.name = 'Updated Name'
        brand.save()
        brand.refresh_from_db()
        self.assertEqual(brand.name, 'Updated Name')

    def test_brand_delete(self):
        """Usuwanie marki"""
        brand = Brand.objects.create(brand_id='B003', name='To Delete')
        pk = brand.pk
        brand.delete()
        self.assertFalse(Brand.objects.filter(pk=pk).exists())

    def test_brand_str(self):
        """__str__ marki"""
        brand = Brand.objects.create(brand_id='B004', name='Str Test')
        self.assertIn('Str Test', str(brand))
        self.assertIn('B004', str(brand))


class TabuCategoryModelTest(TestCase):
    """Testy modelu Category"""

    def test_category_create(self):
        """Tworzenie kategorii"""
        cat = Category.objects.create(
            category_id='TABU_CAT_001',
            name='Test Kategoria',
            path='Test/Path',
        )
        self.assertEqual(cat.category_id, 'TABU_CAT_001')
        self.assertEqual(cat.name, 'Test Kategoria')
        self.assertIsNotNone(cat.pk)

    def test_category_save_update(self):
        """Aktualizacja kategorii"""
        cat = Category.objects.create(
            category_id='C002', name='Cat', path='/'
        )
        cat.name = 'Updated Cat'
        cat.save()
        cat.refresh_from_db()
        self.assertEqual(cat.name, 'Updated Cat')

    def test_category_delete(self):
        """Usuwanie kategorii"""
        cat = Category.objects.create(
            category_id='C003', name='Del', path='/'
        )
        pk = cat.pk
        cat.delete()
        self.assertFalse(Category.objects.filter(pk=pk).exists())


class TabuProductModelTest(TestCase):
    """Testy modelu TabuProduct"""

    def setUp(self):
        self.brand = Brand.objects.create(
            brand_id='TABU_PROD_BRAND',
            name='Brand dla produktu',
        )
        self.category = Category.objects.create(
            category_id='TABU_PROD_CAT',
            name='Kategoria',
            path='/kat',
        )

    def test_tabu_product_create(self):
        """Tworzenie produktu Tabu"""
        product = TabuProduct.objects.create(
            api_id=99901,
            symbol='SYM-001',
            name='Produkt testowy',
            last_update=timezone.now(),
        )
        self.assertEqual(product.api_id, 99901)
        self.assertEqual(product.name, 'Produkt testowy')
        self.assertIsNone(product.mapped_product_uid)

    def test_tabu_product_create_with_brand_category(self):
        """Tworzenie produktu z marką i kategorią"""
        product = TabuProduct.objects.create(
            api_id=99902,
            symbol='SYM-002',
            name='Produkt z relacjami',
            brand=self.brand,
            category=self.category,
            last_update=timezone.now(),
        )
        self.assertEqual(product.brand, self.brand)
        self.assertEqual(product.category, self.category)

    def test_tabu_product_save_mapped_product_uid(self):
        """Zapis mapped_product_uid"""
        product = TabuProduct.objects.create(
            api_id=99903,
            symbol='SYM-003',
            name='Do mapowania',
            last_update=timezone.now(),
        )
        product.mapped_product_uid = 123
        product.save()
        product.refresh_from_db()
        self.assertEqual(product.mapped_product_uid, 123)

    def test_tabu_product_delete(self):
        """Usuwanie produktu"""
        product = TabuProduct.objects.create(
            api_id=99904,
            symbol='SYM-004',
            name='Do usunięcia',
            last_update=timezone.now(),
        )
        pk = product.pk
        product.delete()
        self.assertFalse(TabuProduct.objects.filter(pk=pk).exists())

    def test_tabu_product_str(self):
        """__str__ produktu"""
        product = TabuProduct.objects.create(
            api_id=99905,
            symbol='SYM-005',
            name='Nazwa produktu',
            last_update=timezone.now(),
        )
        self.assertIn('Nazwa produktu', str(product))
        self.assertIn('99905', str(product))
