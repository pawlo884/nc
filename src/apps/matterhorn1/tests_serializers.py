"""
Testy serializerów matterhorn1 - walidacja i konwersje pól, których nie
pokrywają istniejące testy widoków API (tests.py).
"""
from django.test import TestCase

from .serializers import (
    BrandSerializer,
    BulkBrandSerializer,
    BulkCategorySerializer,
    BulkVariantSerializer,
    BulkVariantUpdateSerializer,
    CategorySerializer,
    ProductSerializer,
    ProductVariantSerializer,
)


class BrandSerializerTest(TestCase):
    """Testy BrandSerializer - walidacja pól"""

    def test_valid_brand(self):
        serializer = BrandSerializer(data={'brand_id': 'B001', 'name': 'Marka'})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_brand_id_invalid(self):
        serializer = BrandSerializer(data={'brand_id': '', 'name': 'Marka'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('brand_id', serializer.errors)

    def test_blank_name_stripped_and_validated(self):
        serializer = BrandSerializer(data={'brand_id': 'B002', 'name': '   '})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_name_is_stripped(self):
        serializer = BrandSerializer(data={'brand_id': 'B003', 'name': '  Marka  '})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['name'], 'Marka')


class CategorySerializerTest(TestCase):
    """Testy CategorySerializer - walidacja pól"""

    def test_valid_category(self):
        serializer = CategorySerializer(
            data={'category_id': 'C001', 'name': 'Kategoria', 'path': '/kat'}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_category_id_invalid(self):
        serializer = CategorySerializer(data={'category_id': '', 'name': 'Kategoria', 'path': '/'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('category_id', serializer.errors)

    def test_blank_name_invalid(self):
        serializer = CategorySerializer(data={'category_id': 'C002', 'name': '  ', 'path': '/'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)


class ProductVariantSerializerTest(TestCase):
    """Testy ProductVariantSerializer - walidacja pól"""

    def test_valid_variant(self):
        serializer = ProductVariantSerializer(
            data={'variant_uid': 'V001', 'name': 'M', 'stock': 5, 'max_processing_time': 2}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_variant_uid_invalid(self):
        serializer = ProductVariantSerializer(
            data={'variant_uid': '', 'name': 'M', 'stock': 5}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('variant_uid', serializer.errors)

    def test_negative_stock_invalid(self):
        serializer = ProductVariantSerializer(
            data={'variant_uid': 'V002', 'name': 'M', 'stock': -1}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('stock', serializer.errors)

    def test_negative_max_processing_time_invalid(self):
        serializer = ProductVariantSerializer(
            data={'variant_uid': 'V003', 'name': 'M', 'stock': 1, 'max_processing_time': -5}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('max_processing_time', serializer.errors)

    def test_name_optional_for_partial_bulk_update(self):
        """name jest required=False, bo bulk update wysyła czasem tylko stock/ean"""
        serializer = ProductVariantSerializer(
            data={'variant_uid': 'V004', 'stock': 3}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class ProductSerializerValidationTest(TestCase):
    """Testy walidacji/konwersji pól w ProductSerializer"""

    def _base_payload(self, **overrides):
        payload = {
            'product_id': 1001,
            'name': 'Produkt testowy',
            'active': True,
        }
        payload.update(overrides)
        return payload

    def test_valid_minimal_product(self):
        serializer = ProductSerializer(data=self._base_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['product_uid'], 1001)

    def test_blank_name_invalid(self):
        serializer = ProductSerializer(data=self._base_payload(name='   '))
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_creation_date_iso_format(self):
        serializer = ProductSerializer(
            data=self._base_payload(creation_date='2024-01-15T10:30:00')
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_creation_date_space_format(self):
        serializer = ProductSerializer(
            data=self._base_payload(creation_date='2024-01-15 10:30:00')
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_creation_date_invalid_format(self):
        serializer = ProductSerializer(
            data=self._base_payload(creation_date='not-a-date')
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('creation_date', serializer.errors)

    def test_active_string_true_variants(self):
        for val in ('true', '1', 'yes', 'y', 'TRUE'):
            serializer = ProductSerializer(data=self._base_payload(active=val))
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertTrue(serializer.validated_data['active'])

    def test_active_string_false(self):
        serializer = ProductSerializer(data=self._base_payload(active='no'))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertFalse(serializer.validated_data['active'])

    def test_new_collection_string_conversion(self):
        serializer = ProductSerializer(data=self._base_payload(new_collection='Y'))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertTrue(serializer.validated_data['new_collection'])

    def test_products_in_set_valid_json_string(self):
        serializer = ProductSerializer(
            data=self._base_payload(products_in_set='[1, 2, 3]')
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['products_in_set'], [1, 2, 3])

    def test_products_in_set_invalid_json_string(self):
        serializer = ProductSerializer(
            data=self._base_payload(products_in_set='not-json')
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('products_in_set', serializer.errors)

    def test_other_colors_invalid_json_string(self):
        serializer = ProductSerializer(
            data=self._base_payload(other_colors='not-json')
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('other_colors', serializer.errors)

    def test_prices_invalid_json_string(self):
        serializer = ProductSerializer(
            data=self._base_payload(prices='not-json')
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('prices', serializer.errors)

    def test_url_without_scheme_invalid(self):
        serializer = ProductSerializer(
            data=self._base_payload(url='example.com/product')
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('url', serializer.errors)

    def test_url_with_scheme_valid(self):
        serializer = ProductSerializer(
            data=self._base_payload(url='https://example.com/product')
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_create_resolves_brand_and_category_by_id(self):
        serializer = ProductSerializer(
            data=self._base_payload(brand_id='BR100', category_id='CAT100')
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()
        self.assertEqual(product.brand.brand_id, 'BR100')
        self.assertEqual(product.category.category_id, 'CAT100')

    def test_create_with_nested_variants_and_images(self):
        payload = self._base_payload(
            product_id=1002,
            images=[{'image_url': 'https://example.com/img.jpg', 'order': 1}],
            variants=[{'variant_uid': 'V100', 'name': 'M', 'stock': 5}],
        )
        serializer = ProductSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()
        self.assertEqual(product.images.count(), 1)
        self.assertEqual(product.variants.count(), 1)


class BulkBrandSerializerTest(TestCase):
    """Testy BulkBrandSerializer - walidacja duplikatów"""

    def test_empty_list_invalid(self):
        serializer = BulkBrandSerializer(data={'brands': []})
        self.assertFalse(serializer.is_valid())

    def test_duplicate_brand_id_invalid(self):
        serializer = BulkBrandSerializer(data={
            'brands': [
                {'brand_id': 'DUP1', 'name': 'A'},
                {'brand_id': 'DUP1', 'name': 'B'},
            ]
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('brands', serializer.errors)

    def test_unique_brand_ids_valid(self):
        serializer = BulkBrandSerializer(data={
            'brands': [
                {'brand_id': 'UNQ1', 'name': 'A'},
                {'brand_id': 'UNQ2', 'name': 'B'},
            ]
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)


class BulkCategorySerializerTest(TestCase):
    """Testy BulkCategorySerializer - walidacja duplikatów"""

    def test_duplicate_category_id_invalid(self):
        serializer = BulkCategorySerializer(data={
            'categories': [
                {'category_id': 'DUPC', 'name': 'A', 'path': '/a'},
                {'category_id': 'DUPC', 'name': 'B', 'path': '/b'},
            ]
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('categories', serializer.errors)


class BulkVariantSerializerTest(TestCase):
    """Testy BulkVariantSerializer - walidacja duplikatów"""

    def test_duplicate_variant_uid_invalid(self):
        serializer = BulkVariantSerializer(data={
            'variants': [
                {'variant_uid': 'DUPV', 'name': 'M', 'stock': 1},
                {'variant_uid': 'DUPV', 'name': 'L', 'stock': 2},
            ]
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('variants', serializer.errors)

    def test_empty_list_invalid(self):
        serializer = BulkVariantSerializer(data={'variants': []})
        self.assertFalse(serializer.is_valid())


class BulkVariantUpdateSerializerTest(TestCase):
    """Testy BulkVariantUpdateSerializer - lekka walidacja bez UniqueValidator"""

    def test_partial_fields_allowed(self):
        """bulk update pozwala wysłać tylko variant_uid + stock (bez name)"""
        serializer = BulkVariantUpdateSerializer(data={
            'variants': [{'variant_uid': 'EXIST1', 'stock': 7}]
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_duplicate_variant_uid_invalid(self):
        serializer = BulkVariantUpdateSerializer(data={
            'variants': [
                {'variant_uid': 'DUPU', 'stock': 1},
                {'variant_uid': 'DUPU', 'stock': 2},
            ]
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('variants', serializer.errors)

    def test_negative_stock_invalid(self):
        serializer = BulkVariantUpdateSerializer(data={
            'variants': [{'variant_uid': 'NEGU', 'stock': -3}]
        })
        self.assertFalse(serializer.is_valid())
