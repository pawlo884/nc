"""
Testy serializerów ProductSet / ProductSetItem (nieobjęte przez tests_extended.py).
"""
from django.test import TestCase

from .models import Brands, ProductSet, ProductSetItem, Products
from .serializers import ProductSetItemSerializer, ProductSetSerializer


class ProductSetSerializerTest(TestCase):
    """Testy ProductSetSerializer"""

    databases = {'default', 'MPD'}

    def setUp(self):
        self.brand = Brands.objects.create(name='Marka Zestawu')
        self.mapped_product = Products.objects.create(name='Produkt główny', brand=self.brand)
        self.product_set = ProductSet.objects.create(
            mapped_product=self.mapped_product,
            name='Zestaw testowy',
            description='Opis zestawu',
        )

    def test_serializer_contains_expected_fields(self):
        serializer = ProductSetSerializer(instance=self.product_set)
        expected = {
            'id', 'mapped_product', 'name', 'description', 'items', 'created_at', 'updated_at',
        }
        self.assertEqual(set(serializer.data.keys()), expected)

    def test_serializer_values(self):
        serializer = ProductSetSerializer(instance=self.product_set)
        self.assertEqual(serializer.data['name'], 'Zestaw testowy')
        self.assertEqual(serializer.data['mapped_product'], self.mapped_product.id)
        self.assertEqual(serializer.data['items'], [])

    def test_serializer_with_items(self):
        item_product = Products.objects.create(name='Element zestawu', brand=self.brand)
        ProductSetItem.objects.create(
            product_set=self.product_set, product=item_product, quantity=3,
        )
        serializer = ProductSetSerializer(instance=self.product_set)
        self.assertEqual(len(serializer.data['items']), 1)
        self.assertEqual(serializer.data['items'][0]['quantity'], 3)
        self.assertEqual(serializer.data['items'][0]['product']['name'], 'Element zestawu')


class ProductSetItemSerializerTest(TestCase):
    """Testy ProductSetItemSerializer"""

    databases = {'default', 'MPD'}

    def setUp(self):
        self.brand = Brands.objects.create(name='Marka Item')
        self.mapped_product = Products.objects.create(name='Produkt główny', brand=self.brand)
        self.product_set = ProductSet.objects.create(
            mapped_product=self.mapped_product, name='Zestaw',
        )
        self.item_product = Products.objects.create(name='Produkt w zestawie', brand=self.brand)
        self.item = ProductSetItem.objects.create(
            product_set=self.product_set, product=self.item_product, quantity=2,
        )

    def test_serializer_contains_expected_fields(self):
        serializer = ProductSetItemSerializer(instance=self.item)
        self.assertEqual(
            set(serializer.data.keys()), {'id', 'product', 'quantity', 'created_at'}
        )

    def test_serializer_nested_product(self):
        serializer = ProductSetItemSerializer(instance=self.item)
        self.assertEqual(serializer.data['product']['id'], self.item_product.id)
        self.assertEqual(serializer.data['product']['name'], 'Produkt w zestawie')

    def test_serializer_quantity(self):
        serializer = ProductSetItemSerializer(instance=self.item)
        self.assertEqual(serializer.data['quantity'], 2)
