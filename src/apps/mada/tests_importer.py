"""
Testy logiki importu (mada/importer.py) - upsert produktu/wariantów i historia stanów.
"""
from django.test import TestCase

from mada.importer import import_product_dict, sync_brands
from mada.models import Brand, Category, MadaProduct, MadaProductVariant, StockHistory

PRODUCT_DICT = {
    'api_id': 161,
    'name': 'Rajstopy Gatta Estella',
    'desc': 'Opis',
    'producer_id': '110',
    'price': '12.04',
    'old_price': None,
    'vat': '23',
    'categories': [{'c1': '30', 'c2': '63', 'name': 'Rajstopy / lycra'}],
    'variants': [
        {'color': 'nero/czarny', 'size': '2-S', 'ean': '000223000290', 'stock': 43,
         'variant_key': '000223000290'},
    ],
    'images': [{'api_image_id': '305045', 'url': 'https://www.mada.pl/img/1.jpg', 'order': 0}],
    'raw_data': {'similar_products': []},
}


class ImportProductDictTest(TestCase):
    def test_creates_product_with_category_and_variant(self):
        Brand.objects.create(producer_id='110', name='Gatta')
        cache = {}
        created = import_product_dict('default', PRODUCT_DICT, cache)
        self.assertTrue(created)

        product = MadaProduct.objects.get(api_id=161)
        self.assertEqual(product.brand.producer_id, '110')
        self.assertEqual(product.category.category_id, '30-63')
        self.assertEqual(product.variants.count(), 1)
        self.assertEqual(product.images.count(), 1)

        # kategoria nadrzędna (c1) tworzona automatycznie
        self.assertEqual(Category.objects.filter(category_id='30').count(), 1)

    def test_second_import_updates_stock_and_records_history(self):
        cache = {}
        import_product_dict('default', PRODUCT_DICT, cache)
        self.assertEqual(StockHistory.objects.count(), 1)  # utworzenie wariantu = "increase" od 0

        changed = dict(PRODUCT_DICT)
        changed['variants'] = [{**PRODUCT_DICT['variants'][0], 'stock': 10}]
        import_product_dict('default', changed, cache)

        variant = MadaProductVariant.objects.get(product__api_id=161, variant_key='000223000290')
        self.assertEqual(variant.stock, 10)
        self.assertEqual(StockHistory.objects.count(), 2)
        last = StockHistory.objects.order_by('-timestamp').first()
        self.assertEqual(last.old_stock, 43)
        self.assertEqual(last.new_stock, 10)
        self.assertEqual(last.change_type, 'decrease')

    def test_reimport_without_changes_is_idempotent(self):
        cache = {}
        import_product_dict('default', PRODUCT_DICT, cache)
        created_again = import_product_dict('default', PRODUCT_DICT, cache)
        self.assertFalse(created_again)
        self.assertEqual(MadaProduct.objects.count(), 1)
        self.assertEqual(MadaProductVariant.objects.count(), 1)


class SyncBrandsTest(TestCase):
    def test_creates_and_updates_brands(self):
        sync_brands('default', {'110': 'Gatta'})
        self.assertEqual(Brand.objects.get(producer_id='110').name, 'Gatta')

        sync_brands('default', {'110': 'Gatta Rebrand'})
        self.assertEqual(Brand.objects.get(producer_id='110').name, 'Gatta Rebrand')
