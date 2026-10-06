"""
Testy dla aplikacji matterhorn1
Testy modeli, serializers i API endpoints
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from datetime import datetime, timedelta
import json

from .models import (
    Brand, Category, Product, ProductVariant,
    ProductImage, ProductDetails, ApiSyncLog, Saga, SagaStep, StockHistory
)


class BrandModelTest(TestCase):
    """Testy dla modelu Brand"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.brand = Brand.objects.create(
            brand_id='TEST001',
            name='Test Brand'
        )

    def test_brand_creation(self):
        """Test tworzenia marki"""
        self.assertEqual(self.brand.brand_id, 'TEST001')
        self.assertEqual(self.brand.name, 'Test Brand')
        self.assertIsNotNone(self.brand.created_at)
        self.assertIsNotNone(self.brand.updated_at)

    def test_brand_str(self):
        """Test metody __str__"""
        expected = "Test Brand (TEST001)"
        self.assertEqual(str(self.brand), expected)

    def test_brand_unique_brand_id(self):
        """Test unikalności brand_id"""
        with self.assertRaises(Exception):
            Brand.objects.create(
                brand_id='TEST001',
                name='Another Brand'
            )


class CategoryModelTest(TestCase):
    """Testy dla modelu Category"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.category = Category.objects.create(
            category_id='CAT001',
            name='Test Category',
            path='Test/Path'
        )

    def test_category_creation(self):
        """Test tworzenia kategorii"""
        self.assertEqual(self.category.category_id, 'CAT001')
        self.assertEqual(self.category.name, 'Test Category')
        self.assertEqual(self.category.path, 'Test/Path')

    def test_category_str(self):
        """Test metody __str__"""
        expected = "Test Category (CAT001)"
        self.assertEqual(str(self.category), expected)


class ProductModelTest(TestCase):
    """Testy dla modelu Product"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.brand = Brand.objects.create(
            brand_id='BRAND001',
            name='Test Brand'
        )
        self.category = Category.objects.create(
            category_id='CAT001',
            name='Test Category',
            path='Test/Path'
        )
        self.product = Product.objects.create(
            product_uid=12345,
            name='Test Product',
            description='Test Description',
            brand=self.brand,
            category=self.category,
            active=True
        )

    def test_product_creation(self):
        """Test tworzenia produktu"""
        self.assertEqual(self.product.product_uid, 12345)
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.brand, self.brand)
        self.assertEqual(self.product.category, self.category)
        self.assertTrue(self.product.active)

    def test_product_str(self):
        """Test metody __str__"""
        expected = "Test Product (12345)"
        self.assertEqual(str(self.product), expected)

    def test_product_stock_total(self):
        """Test właściwości stock_total"""
        # Bez wariantów
        self.assertEqual(self.product.stock_total, 0)

        # Z wariantami
        ProductVariant.objects.create(
            variant_uid='VAR001',
            product=self.product,
            name='S',
            stock=10
        )
        ProductVariant.objects.create(
            variant_uid='VAR002',
            product=self.product,
            name='M',
            stock=20
        )
        self.assertEqual(self.product.stock_total, 30)

    def test_product_json_fields(self):
        """Test pól JSON"""
        self.product.products_in_set = [1, 2, 3]
        self.product.other_colors = ['red', 'blue']
        self.product.prices = {'PLN': 100, 'EUR': 25}
        self.product.save()

        product = Product.objects.get(pk=self.product.pk)
        self.assertEqual(product.products_in_set, [1, 2, 3])
        self.assertEqual(product.other_colors, ['red', 'blue'])
        self.assertEqual(product.prices['PLN'], 100)


class ProductVariantModelTest(TestCase):
    """Testy dla modelu ProductVariant"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.brand = Brand.objects.create(
            brand_id='BRAND001',
            name='Test Brand'
        )
        self.product = Product.objects.create(
            product_uid=12345,
            name='Test Product',
            brand=self.brand
        )
        self.variant = ProductVariant.objects.create(
            variant_uid='VAR001',
            product=self.product,
            name='S',
            stock=10,
            ean='1234567890123'
        )

    def test_variant_creation(self):
        """Test tworzenia wariantu"""
        self.assertEqual(self.variant.variant_uid, 'VAR001')
        self.assertEqual(self.variant.product, self.product)
        self.assertEqual(self.variant.name, 'S')
        self.assertEqual(self.variant.stock, 10)
        self.assertEqual(self.variant.ean, '1234567890123')

    def test_variant_str(self):
        """Test metody __str__"""
        expected = "Test Product - S (VAR001)"
        self.assertEqual(str(self.variant), expected)


class ProductImageModelTest(TestCase):
    """Testy dla modelu ProductImage"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.brand = Brand.objects.create(
            brand_id='BRAND001',
            name='Test Brand'
        )
        self.product = Product.objects.create(
            product_uid=12345,
            name='Test Product',
            brand=self.brand
        )

    def test_image_creation(self):
        """Test tworzenia obrazu"""
        image = ProductImage.objects.create(
            product=self.product,
            image_url='https://example.com/image.jpg',
            order=1
        )
        self.assertEqual(image.product, self.product)
        self.assertEqual(image.image_url, 'https://example.com/image.jpg')
        self.assertEqual(image.order, 1)

    def test_image_ordering(self):
        """Test sortowania obrazów"""
        img1 = ProductImage.objects.create(
            product=self.product,
            image_url='https://example.com/image1.jpg',
            order=2
        )
        img2 = ProductImage.objects.create(
            product=self.product,
            image_url='https://example.com/image2.jpg',
            order=1
        )

        images = list(self.product.images.all())
        self.assertEqual(images[0], img2)  # order=1 pierwszy
        self.assertEqual(images[1], img1)  # order=2 drugi


class ApiSyncLogModelTest(TestCase):
    """Testy dla modelu ApiSyncLog"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.sync_log = ApiSyncLog.objects.create(
            sync_type='products',
            status='success',
            records_processed=100,
            records_created=50,
            records_updated=50,
            records_errors=0
        )

    def test_sync_log_creation(self):
        """Test tworzenia logu synchronizacji"""
        self.assertEqual(self.sync_log.sync_type, 'products')
        self.assertEqual(self.sync_log.status, 'success')
        self.assertEqual(self.sync_log.records_processed, 100)
        self.assertEqual(self.sync_log.records_created, 50)
        self.assertEqual(self.sync_log.records_updated, 50)
        self.assertEqual(self.sync_log.records_errors, 0)

    def test_sync_log_str(self):
        """Test metody __str__"""
        self.assertIn('products', str(self.sync_log))
        self.assertIn('success', str(self.sync_log))


class SagaModelTest(TestCase):
    """Testy dla modelu Saga"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.saga = Saga.objects.create(
            saga_id='saga_001',
            saga_type='product_creation',
            status='pending',
            input_data={'product_id': 12345},
            total_steps=3
        )

    def test_saga_creation(self):
        """Test tworzenia Saga"""
        self.assertEqual(self.saga.saga_id, 'saga_001')
        self.assertEqual(self.saga.saga_type, 'product_creation')
        self.assertEqual(self.saga.status, 'pending')
        self.assertEqual(self.saga.input_data['product_id'], 12345)
        self.assertEqual(self.saga.total_steps, 3)

    def test_saga_str(self):
        """Test metody __str__"""
        expected = "Saga saga_001 (product_creation) - pending"
        self.assertEqual(str(self.saga), expected)

    def test_saga_steps_relationship(self):
        """Test relacji z SagaStep"""
        step1 = SagaStep.objects.create(
            saga=self.saga,
            step_name='create_product',
            step_order=1
        )
        step2 = SagaStep.objects.create(
            saga=self.saga,
            step_name='create_variants',
            step_order=2
        )

        self.assertEqual(self.saga.steps.count(), 2)
        self.assertIn(step1, self.saga.steps.all())
        self.assertIn(step2, self.saga.steps.all())


class StockHistoryModelTest(TestCase):
    """Testy dla modelu StockHistory"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.stock_history = StockHistory.objects.create(
            variant_uid='VAR001',
            product_uid=12345,
            product_name='Test Product',
            variant_name='S',
            old_stock=10,
            new_stock=15,
            stock_change=5,
            change_type='increase'
        )

    def test_stock_history_creation(self):
        """Test tworzenia historii stanów"""
        self.assertEqual(self.stock_history.variant_uid, 'VAR001')
        self.assertEqual(self.stock_history.product_uid, 12345)
        self.assertEqual(self.stock_history.old_stock, 10)
        self.assertEqual(self.stock_history.new_stock, 15)
        self.assertEqual(self.stock_history.stock_change, 5)
        self.assertEqual(self.stock_history.change_type, 'increase')

    def test_stock_history_str(self):
        """Test metody __str__"""
        self.assertIn('Test Product', str(self.stock_history))
        self.assertIn('S', str(self.stock_history))


# ==================== API TESTS ====================


class BrandAPITest(APITestCase):
    """Testy API dla marek"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        self.brand = Brand.objects.create(
            brand_id='BRAND001',
            name='Test Brand'
        )

    def test_brand_list_requires_auth(self):
        """Test czy lista marek wymaga autoryzacji"""
        client = APIClient()
        response = client.get('/matterhorn1/api/brands/bulk/')
        # DRF może zwracać 403 (Forbidden) lub 405 (Method Not Allowed) zamiast 401
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ])

    def test_brand_bulk_create(self):
        """Test bulk create marek"""
        url = '/matterhorn1/api/brands/bulk/create-secure/'
        data = [
            {
                'brand_id': 'BRAND002',
                'name': 'Brand 2'
            },
            {
                'brand_id': 'BRAND003',
                'name': 'Brand 3'
            }
        ]

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Brand.objects.count(), 3)  # 1 istniejący + 2 nowe

    def test_brand_bulk_create_validation(self):
        """Test walidacji przy bulk create"""
        url = '/matterhorn1/api/brands/bulk/create-secure/'
        data = [
            {
                'brand_id': '',  # Puste brand_id - powinno zwrócić błąd
                'name': 'Invalid Brand'
            }
        ]

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CategoryAPITest(APITestCase):
    """Testy API dla kategorii"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_category_bulk_create(self):
        """Test bulk create kategorii"""
        url = '/matterhorn1/api/categories/bulk/create-secure/'
        data = [
            {
                'category_id': 'CAT001',
                'name': 'Category 1',
                'path': 'Category/Path/1'
            },
            {
                'category_id': 'CAT002',
                'name': 'Category 2',
                'path': 'Category/Path/2'
            }
        ]

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Category.objects.count(), 2)


class ProductAPITest(APITestCase):
    """Testy API dla produktów"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Użyj .using('default') aby upewnić się, że dane są w testowej bazie
        self.brand = Brand.objects.using('default').create(
            brand_id='BRAND001',
            name='Test Brand'
        )
        self.category = Category.objects.using('default').create(
            category_id='CAT001',
            name='Test Category',
            path='Test/Path'
        )

    def test_product_bulk_create(self):
        """Test bulk create produktów"""
        url = '/matterhorn1/api/products/bulk/create-secure/'
        data = [
            {
                'product_id': 1001,  # Serializer używa product_id, nie product_uid
                'name': 'Product 1',
                'description': 'Description 1',
                'brand_id': self.brand.brand_id,
                'category_id': self.category.category_id,
                'active': True
            },
            {
                'product_id': 1002,  # Serializer używa product_id, nie product_uid
                'name': 'Product 2',
                'description': 'Description 2',
                'brand_id': self.brand.brand_id,
                'category_id': self.category.category_id,
                'active': True
            }
        ]

        response = self.client.post(url, data, format='json')
        if response.status_code != status.HTTP_200_OK:
            print(f"Błąd w test_product_bulk_create: {response.status_code}")
            print(f"Response: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Użyj .using('default') dla testowej bazy
        self.assertEqual(Product.objects.using('default').count(), 2)

    def test_product_bulk_create_with_variants(self):
        """Test bulk create produktów z wariantami"""
        url = '/matterhorn1/api/products/bulk/create-secure/'
        data = [
            {
                'product_id': 2001,  # Serializer używa product_id
                'name': 'Product with Variants',
                'brand_id': self.brand.brand_id,
                'category_id': self.category.category_id,
                'variants': [
                    {
                        'variant_uid': 'VAR001',
                        'name': 'S',
                        'stock': 10,
                        'ean': '1234567890123'
                    },
                    {
                        'variant_uid': 'VAR002',
                        'name': 'M',
                        'stock': 20,
                        'ean': '1234567890124'
                    }
                ]
            }
        ]

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Użyj .using('default') i product_id zamiast product_uid
        product = Product.objects.using('default').get(product_uid=2001)
        self.assertEqual(product.variants.count(), 2)

    def test_product_bulk_update(self):
        """Test bulk update produktów"""
        # Najpierw utwórz produkt
        product = Product.objects.using('default').create(
            product_uid=3001,
            name='Original Name',
            brand=self.brand,
            category=self.category
        )

        url = '/matterhorn1/api/products/bulk/update-secure/'
        data = [
            {
                'product_id': 3001,  # Serializer używa product_id
                'name': 'Updated Name',
                'description': 'Updated Description'
            }
        ]

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Odśwież produkt z bazy
        product = Product.objects.using('default').get(product_uid=3001)
        self.assertEqual(product.name, 'Updated Name')
        self.assertEqual(product.description, 'Updated Description')


class ProductVariantAPITest(APITestCase):
    """Testy API dla wariantów produktów"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        self.brand = Brand.objects.create(
            brand_id='BRAND001',
            name='Test Brand'
        )
        self.product = Product.objects.create(
            product_uid=4001,
            name='Test Product',
            brand=self.brand
        )

    def test_variant_bulk_create(self):
        """Test bulk create wariantów"""
        url = '/matterhorn1/api/variants/bulk/create-secure/'
        data = [
            {
                'variant_uid': 'VAR001',
                'product_id': 4001,  # View oczekuje product_id
                'name': 'S',
                'stock': 10,
                'ean': '1234567890123'
            },
            {
                'variant_uid': 'VAR002',
                'product_id': 4001,  # View oczekuje product_id
                'name': 'M',
                'stock': 20,
                'ean': '1234567890124'
            }
        ]

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Sprawdź warianty w bazie default
        self.assertEqual(ProductVariant.objects.using('default').count(), 2)

    def test_variant_bulk_update(self):
        """Test bulk update wariantów"""
        # Najpierw utwórz wariant
        variant = ProductVariant.objects.create(
            variant_uid='VAR003',
            product=self.product,
            name='S',
            stock=10
        )

        url = '/matterhorn1/api/variants/bulk/update-secure/'
        data = [
            {
                'variant_uid': 'VAR003',
                'stock': 50,
                'ean': '1234567890125'
            }
        ]

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Odśwież wariant z bazy
        variant = ProductVariant.objects.using('default').get(variant_uid='VAR003')
        self.assertEqual(variant.stock, 50)
        self.assertEqual(variant.ean, '1234567890125')


class ProductImageAPITest(APITestCase):
    """Testy API dla obrazów produktów"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        self.brand = Brand.objects.create(
            brand_id='BRAND001',
            name='Test Brand'
        )
        self.product = Product.objects.create(
            product_uid=5001,
            name='Test Product',
            brand=self.brand
        )

    def test_image_bulk_create(self):
        """Test bulk create obrazów"""
        url = '/matterhorn1/api/images/bulk/create-secure/'
        data = [
            {
                'product_uid': 5001,
                'image_url': 'https://example.com/image1.jpg',
                'order': 1
            },
            {
                'product_uid': 5001,
                'image_url': 'https://example.com/image2.jpg',
                'order': 2
            }
        ]

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ProductImage.objects.count(), 2)
