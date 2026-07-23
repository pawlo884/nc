"""
Testy serializerów Tabu - BrandSerializer, CategorySerializer, ApiSyncLogSerializer.
"""
from django.test import TestCase
from django.utils import timezone

from tabu.models import ApiSyncLog, Brand, Category
from tabu.serializers import ApiSyncLogSerializer, BrandSerializer, CategorySerializer


class BrandSerializerTest(TestCase):
    """Testy BrandSerializer"""

    def test_serialize_brand(self):
        brand = Brand.objects.create(brand_id='SER_BRAND_001', name='Marka testowa')
        data = BrandSerializer(brand).data
        self.assertEqual(data['brand_id'], 'SER_BRAND_001')
        self.assertEqual(data['name'], 'Marka testowa')
        self.assertIn('created_at', data)

    def test_deserialize_valid_brand(self):
        payload = {'brand_id': 'SER_BRAND_002', 'name': 'Nowa marka'}
        serializer = BrandSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        brand = serializer.save()
        self.assertEqual(brand.brand_id, 'SER_BRAND_002')

    def test_read_only_fields_ignored_on_input(self):
        payload = {
            'brand_id': 'SER_BRAND_003',
            'name': 'Marka RO',
            'created_at': '2020-01-01T00:00:00Z',
        }
        serializer = BrandSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('created_at', serializer.validated_data)

    def test_missing_required_field_invalid(self):
        serializer = BrandSerializer(data={'name': 'Bez brand_id'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('brand_id', serializer.errors)


class CategorySerializerTest(TestCase):
    """Testy CategorySerializer"""

    def test_serialize_category_with_parent(self):
        parent = Category.objects.create(category_id='SER_CAT_PARENT', name='Rodzic', path='/rodzic')
        child = Category.objects.create(
            category_id='SER_CAT_CHILD', name='Dziecko', path='/rodzic/dziecko', parent=parent,
        )
        data = CategorySerializer(child).data
        self.assertEqual(data['parent'], parent.pk)
        self.assertEqual(data['parent_name'], 'Rodzic')

    def test_serialize_category_without_parent(self):
        cat = Category.objects.create(category_id='SER_CAT_ROOT', name='Root', path='/root')
        data = CategorySerializer(cat).data
        self.assertIsNone(data['parent'])
        self.assertIsNone(data.get('parent_name'))

    def test_deserialize_valid_category(self):
        payload = {'category_id': 'SER_CAT_NEW', 'name': 'Nowa kategoria', 'path': '/nowa'}
        serializer = CategorySerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class ApiSyncLogSerializerTest(TestCase):
    """Testy ApiSyncLogSerializer"""

    def test_serialize_sync_log(self):
        log = ApiSyncLog.objects.create(
            sync_type='products',
            status='completed',
            completed_at=timezone.now(),
            products_processed=10,
            products_success=9,
            products_failed=1,
        )
        data = ApiSyncLogSerializer(log).data
        self.assertEqual(data['sync_type'], 'products')
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['products_processed'], 10)

    def test_started_at_is_read_only(self):
        payload = {
            'sync_type': 'products',
            'status': 'pending',
            'started_at': '2020-01-01T00:00:00Z',
        }
        serializer = ApiSyncLogSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('started_at', serializer.validated_data)
