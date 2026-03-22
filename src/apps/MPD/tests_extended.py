"""
Rozszerzone testy jednostkowe dla aplikacji MPD.

Pokrywają modele, serializery i widoki niepokryte przez istniejące pliki testów:
- tests.py          → podstawowe testy modeli
- tests_models.py   → CRUD Products/Variants/Sources/StockAndPrices
- tests_api.py      → testy endpointów API (auth, statusy)
- tests_integration.py → propagacja sygnałów do Tabu/Matterhorn

Ten plik dodaje:
- Collection, Seasons, ProductSeries
- ProductVariantsRetailPrice, ProductImage (walidacja save)
- StockHistory, FabricComponent, ProductFabric
- ProductSet, ProductSetItem
- FullChangeFile, Units, Vat, Paths, ProductPaths, Categories
- ProductSerializer, ProductListSerializer
- Widoki: manage_product_paths, manage_product_fabric,
          manage_product_attributes, create_product
"""
import json
from decimal import Decimal

from django.test import TestCase, Client, override_settings

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

from .models import (
    Attributes,
    Brands,
    Categories,
    Collection,
    Colors,
    FabricComponent,
    FullChangeFile,
    Paths,
    ProductAttribute,
    ProductFabric,
    ProductImage,
    ProductPaths,
    ProductSeries,
    ProductSet,
    ProductSetItem,
    ProductVariants,
    ProductVariantsRetailPrice,
    Products,
    Seasons,
    Sizes,
    Sources,
    StockHistory,
    Units,
    Vat,
)
from .serializers import ProductListSerializer, ProductSerializer


DEBUG_TOOLBAR_OFF = {"SHOW_TOOLBAR_CALLBACK": lambda request: False}


# ==============================================================
# MODEL TESTS – Collection
# ==============================================================

class CollectionModelTest(TestCase):
    """Testy modelu Collection"""

    databases = {'default', 'MPD'}

    def setUp(self):
        self.brand = Brands.objects.create(name='Marka Testowa')

    def test_collection_creation(self):
        col = Collection.objects.create(brand=self.brand, name='Basic', sort_order=0)
        self.assertEqual(col.name, 'Basic')
        self.assertEqual(col.brand, self.brand)
        self.assertEqual(col.sort_order, 0)
        self.assertIsNotNone(col.pk)

    def test_collection_default_sort_order(self):
        col = Collection.objects.create(brand=self.brand, name='Default')
        self.assertEqual(col.sort_order, 0)

    def test_collection_str(self):
        col = Collection.objects.create(brand=self.brand, name='Wedding')
        self.assertEqual(str(col), 'Marka Testowa: Wedding')

    def test_collection_unique_together_raises(self):
        Collection.objects.create(brand=self.brand, name='Kolekcja A')
        with self.assertRaises(Exception):
            Collection.objects.create(brand=self.brand, name='Kolekcja A')

    def test_collection_same_name_different_brand_allowed(self):
        brand2 = Brands.objects.create(name='Marka 2')
        Collection.objects.create(brand=self.brand, name='Wspólna')
        col2 = Collection.objects.create(brand=brand2, name='Wspólna')
        self.assertIsNotNone(col2.pk)

    def test_collection_delete_cascades_on_brand_delete(self):
        brand = Brands.objects.create(name='Do usunięcia')
        col = Collection.objects.create(brand=brand, name='Kol')
        col_pk = col.pk
        brand.delete()
        self.assertFalse(Collection.objects.filter(pk=col_pk).exists())


# ==============================================================
# MODEL TESTS – Seasons
# ==============================================================

class SeasonsModelTest(TestCase):
    """Testy modelu Seasons"""

    databases = {'default', 'MPD'}

    def test_season_creation(self):
        season = Seasons.objects.create(name='Lato')
        self.assertEqual(season.name, 'Lato')
        self.assertIsNotNone(season.pk)

    def test_season_str(self):
        season = Seasons.objects.create(name='Zima')
        self.assertEqual(str(season), 'Zima')

    def test_season_unique_name_raises(self):
        Seasons.objects.create(name='Wiosna')
        with self.assertRaises(Exception):
            Seasons.objects.create(name='Wiosna')

    def test_season_product_relationship(self):
        """Produkt może mieć przypisany sezon"""
        brand = Brands.objects.create(name='B')
        season = Seasons.objects.create(name='Jesień')
        product = Products.objects.create(name='Produkt sezonowy', brand=brand, season=season)
        self.assertEqual(product.season, season)
        self.assertIn(product, season.products.all())


# ==============================================================
# MODEL TESTS – ProductSeries
# ==============================================================

class ProductSeriesModelTest(TestCase):
    """Testy modelu ProductSeries"""

    databases = {'default', 'MPD'}

    def setUp(self):
        self.brand = Brands.objects.create(name='Marka')

    def test_series_creation(self):
        series = ProductSeries.objects.create(brand=self.brand, name='Seria A')
        self.assertEqual(series.name, 'Seria A')
        self.assertEqual(series.brand, self.brand)

    def test_series_str_with_name(self):
        series = ProductSeries.objects.create(brand=self.brand, name='Classic')
        self.assertEqual(str(series), 'Classic')

    def test_series_str_no_name(self):
        series = ProductSeries.objects.create(brand=self.brand, name=None)
        self.assertIn('Seria', str(series))
        self.assertIn(str(series.id), str(series))

    def test_series_unique_together_raises(self):
        ProductSeries.objects.create(brand=self.brand, name='Duplikat')
        with self.assertRaises(Exception):
            ProductSeries.objects.create(brand=self.brand, name='Duplikat')

    def test_series_same_name_different_brand(self):
        brand2 = Brands.objects.create(name='Marka 2')
        ProductSeries.objects.create(brand=self.brand, name='Premium')
        s2 = ProductSeries.objects.create(brand=brand2, name='Premium')
        self.assertIsNotNone(s2.pk)


# ==============================================================
# MODEL TESTS – ProductVariantsRetailPrice
# ==============================================================

class ProductVariantsRetailPriceModelTest(TestCase):
    """Testy modelu ProductVariantsRetailPrice (OneToOne z wariantem)"""

    databases = {'default', 'MPD'}

    def setUp(self):
        brand = Brands.objects.create(name='B')
        product = Products.objects.create(name='Prod', brand=brand)
        color = Colors.objects.create(name='Red')
        size = Sizes.objects.create(name='S', category='default')
        self.variant = ProductVariants.objects.create(
            product=product, color=color, size=size
        )

    def test_retail_price_creation(self):
        rp = ProductVariantsRetailPrice.objects.create(
            variant=self.variant,
            retail_price=Decimal('199.99'),
            vat=Decimal('23.00'),
            currency='PLN',
            net_price=Decimal('162.27'),
        )
        self.assertEqual(rp.retail_price, Decimal('199.99'))
        self.assertEqual(rp.currency, 'PLN')
        self.assertEqual(rp.variant, self.variant)

    def test_retail_price_nullable_fields(self):
        rp = ProductVariantsRetailPrice.objects.create(
            variant=self.variant,
            currency='EUR',
        )
        self.assertIsNone(rp.retail_price)
        self.assertIsNone(rp.net_price)

    def test_retail_price_one_to_one_constraint(self):
        """Każdy wariant może mieć tylko jedną cenę detaliczną"""
        ProductVariantsRetailPrice.objects.create(
            variant=self.variant,
            retail_price=Decimal('100.00'),
            currency='PLN',
        )
        with self.assertRaises(Exception):
            ProductVariantsRetailPrice.objects.create(
                variant=self.variant,
                retail_price=Decimal('200.00'),
                currency='PLN',
            )

    def test_retail_price_update(self):
        rp = ProductVariantsRetailPrice.objects.create(
            variant=self.variant,
            retail_price=Decimal('100.00'),
            currency='PLN',
        )
        rp.retail_price = Decimal('120.00')
        rp.save()
        rp.refresh_from_db()
        self.assertEqual(rp.retail_price, Decimal('120.00'))

    def test_retail_price_deleted_when_variant_deleted(self):
        rp = ProductVariantsRetailPrice.objects.create(
            variant=self.variant,
            retail_price=Decimal('50.00'),
            currency='PLN',
        )
        rp_pk = self.variant.variant_id
        self.variant.delete()
        self.assertFalse(
            ProductVariantsRetailPrice.objects.filter(variant_id=rp_pk).exists()
        )


# ==============================================================
# MODEL TESTS – ProductImage
# ==============================================================

class ProductImageModelTest(TestCase):
    """Testy modelu ProductImage i jego metody save()"""

    # Sygnał post_delete Products odpytuje zzz_MPD (variant_ids) i zzz_matterhorn1/zzz_tabu
    databases = {'default', 'MPD', 'zzz_MPD', 'zzz_matterhorn1', 'zzz_tabu'}

    def setUp(self):
        # Używamy 'MPD' bezpośrednio, bo ProductImage.save() wymusza using='MPD'.
        # Gdybyśmy użyli routera (→ 'zzz_MPD'), FK check na 'MPD' connection
        # nie widziałby produktu (oddzielne transakcje na tej samej bazie fizycznej).
        brand = Brands.objects.using('MPD').create(name='B')
        self.product = Products.objects.using('MPD').create(name='Prod', brand=brand)

    def test_image_creation(self):
        img = ProductImage.objects.using('MPD').create(
            product=self.product,
            file_path='images/photo.jpg',
        )
        self.assertEqual(img.file_path, 'images/photo.jpg')
        self.assertEqual(img.product, self.product)
        self.assertIsNotNone(img.pk)

    def test_image_str(self):
        img = ProductImage.objects.using('MPD').create(
            product=self.product,
            file_path='images/photo.jpg',
        )
        result = str(img)
        self.assertIn(str(img.id), result)
        self.assertIn(str(self.product.id), result)

    def test_image_save_rejects_slash_path_as_product_id(self):
        """save() rzuca ValueError gdy product_id zawiera '/' (wygląda jak ścieżka)"""
        img = ProductImage(file_path='test.jpg')
        img.product_id = 'MPD_test/images/something.jpg'
        with self.assertRaises(ValueError):
            img.save()

    def test_image_save_rejects_mpd_path_string(self):
        img = ProductImage(file_path='test.jpg')
        img.product_id = 'MPD/product/123'
        with self.assertRaises(ValueError):
            img.save()

    def test_image_deleted_when_product_deleted(self):
        img = ProductImage.objects.using('MPD').create(
            product=self.product,
            file_path='images/to_delete.jpg',
        )
        img_pk = img.pk
        self.product.delete(using='MPD')
        self.assertFalse(ProductImage.objects.using('MPD').filter(pk=img_pk).exists())


# ==============================================================
# MODEL TESTS – StockHistory
# ==============================================================

class StockHistoryModelTest(TestCase):
    """Testy modelu StockHistory"""

    databases = {'default', 'MPD'}

    def test_stock_history_creation(self):
        sh = StockHistory.objects.create(
            stock_id=1,
            source_id=1,
            previous_stock=10,
            new_stock=5,
            previous_price=Decimal('99.99'),
            new_price=Decimal('89.99'),
        )
        self.assertEqual(sh.previous_stock, 10)
        self.assertEqual(sh.new_stock, 5)
        self.assertEqual(sh.previous_price, Decimal('99.99'))
        self.assertEqual(sh.new_price, Decimal('89.99'))
        self.assertIsNotNone(sh.change_date)

    def test_stock_history_default_prices(self):
        sh = StockHistory.objects.create(
            stock_id=2, source_id=2,
            previous_stock=0, new_stock=20,
        )
        self.assertEqual(sh.previous_price, Decimal('0.00'))
        self.assertEqual(sh.new_price, Decimal('0.00'))

    def test_stock_history_auto_timestamp(self):
        sh = StockHistory.objects.create(
            stock_id=3, source_id=None,
            previous_stock=5, new_stock=15,
        )
        self.assertIsNotNone(sh.change_date)

    def test_stock_history_nullable_source(self):
        sh = StockHistory.objects.create(
            stock_id=4, source_id=None,
            previous_stock=0, new_stock=1,
        )
        self.assertIsNone(sh.source_id)


# ==============================================================
# MODEL TESTS – FabricComponent & ProductFabric
# ==============================================================

class FabricComponentModelTest(TestCase):
    """Testy modelu FabricComponent"""

    databases = {'default', 'MPD'}

    def test_fabric_component_creation(self):
        fc = FabricComponent.objects.create(name='Bawełna')
        self.assertEqual(fc.name, 'Bawełna')
        self.assertIsNotNone(fc.pk)

    def test_fabric_component_str(self):
        fc = FabricComponent.objects.create(name='Poliester')
        self.assertEqual(str(fc), 'Poliester')

    def test_fabric_component_unique_name_raises(self):
        FabricComponent.objects.create(name='Jedwab')
        with self.assertRaises(Exception):
            FabricComponent.objects.create(name='Jedwab')


class ProductFabricModelTest(TestCase):
    """Testy modelu ProductFabric"""

    databases = {'default', 'MPD'}

    def setUp(self):
        brand = Brands.objects.create(name='B')
        self.product = Products.objects.create(name='Produkt', brand=brand)
        self.component = FabricComponent.objects.create(name='Wełna')

    def test_product_fabric_creation(self):
        pf = ProductFabric.objects.create(
            product=self.product,
            component=self.component,
            percentage=80,
        )
        self.assertEqual(pf.percentage, 80)
        self.assertEqual(pf.product, self.product)
        self.assertEqual(pf.component, self.component)

    def test_product_fabric_str(self):
        pf = ProductFabric.objects.create(
            product=self.product,
            component=self.component,
            percentage=60,
        )
        result = str(pf)
        self.assertIn('Wełna', result)
        self.assertIn('60%', result)

    def test_product_fabric_unique_together_raises(self):
        ProductFabric.objects.create(
            product=self.product, component=self.component, percentage=50
        )
        with self.assertRaises(Exception):
            ProductFabric.objects.create(
                product=self.product, component=self.component, percentage=30
            )

    def test_product_fabric_different_components_allowed(self):
        component2 = FabricComponent.objects.create(name='Poliamid')
        pf1 = ProductFabric.objects.create(
            product=self.product, component=self.component, percentage=70
        )
        pf2 = ProductFabric.objects.create(
            product=self.product, component=component2, percentage=30
        )
        self.assertIsNotNone(pf1.pk)
        self.assertIsNotNone(pf2.pk)

    def test_product_fabric_deleted_with_product(self):
        pf = ProductFabric.objects.create(
            product=self.product, component=self.component, percentage=100
        )
        pf_pk = pf.pk
        self.product.delete()
        self.assertFalse(ProductFabric.objects.filter(pk=pf_pk).exists())


# ==============================================================
# MODEL TESTS – ProductSet & ProductSetItem
# ==============================================================

class ProductSetModelTest(TestCase):
    """Testy modelu ProductSet"""

    databases = {'default', 'MPD'}

    def setUp(self):
        brand = Brands.objects.create(name='B')
        self.product = Products.objects.create(name='Produkt', brand=brand)

    def test_product_set_creation(self):
        ps = ProductSet.objects.create(
            mapped_product=self.product,
            name='Zestaw 1',
            description='Opis zestawu',
        )
        self.assertEqual(ps.name, 'Zestaw 1')
        self.assertEqual(ps.mapped_product, self.product)
        self.assertIsNotNone(ps.created_at)
        self.assertIsNotNone(ps.updated_at)

    def test_product_set_str(self):
        ps = ProductSet.objects.create(
            mapped_product=self.product,
            name='Mój Zestaw',
        )
        result = str(ps)
        self.assertIn('Mój Zestaw', result)
        self.assertIn(self.product.name, result)

    def test_product_set_optional_description(self):
        ps = ProductSet.objects.create(
            mapped_product=self.product,
            name='Bez opisu',
        )
        self.assertIsNone(ps.description)


class ProductSetItemModelTest(TestCase):
    """Testy modelu ProductSetItem"""

    databases = {'default', 'MPD'}

    def setUp(self):
        brand = Brands.objects.create(name='B')
        self.product = Products.objects.create(name='Produkt', brand=brand)
        self.ps = ProductSet.objects.create(
            mapped_product=self.product, name='Zestaw'
        )

    def test_product_set_item_creation(self):
        item = ProductSetItem.objects.create(
            product_set_id=self.ps.id,
            product_id=self.product.id,
            quantity=3,
            position=1,
        )
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.position, 1)
        self.assertEqual(item.product_set_id, self.ps.id)
        self.assertEqual(item.product_id, self.product.id)
        self.assertIsNotNone(item.created_at)

    def test_product_set_item_default_values(self):
        item = ProductSetItem.objects.create(
            product_set_id=self.ps.id,
            product_id=self.product.id,
        )
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.position, 0)

    def test_product_set_item_str(self):
        item = ProductSetItem.objects.create(
            product_set_id=self.ps.id,
            product_id=self.product.id,
        )
        result = str(item)
        self.assertIn(str(self.product.id), result)
        self.assertIn(str(self.ps.id), result)


# ==============================================================
# MODEL TESTS – FullChangeFile
# ==============================================================

class FullChangeFileModelTest(TestCase):
    """Testy modelu FullChangeFile"""

    databases = {'default', 'MPD'}

    def test_full_change_file_creation(self):
        fcf = FullChangeFile.objects.create(
            filename='full_change.xml',
            timestamp='2024-01-15T12-00-00',
            bucket_url='https://bucket.example.com/full_change.xml',
            file_size=1024,
        )
        self.assertEqual(fcf.filename, 'full_change.xml')
        self.assertEqual(fcf.file_size, 1024)
        self.assertIsNotNone(fcf.created_at)

    def test_full_change_file_str(self):
        fcf = FullChangeFile.objects.create(
            filename='test.xml',
            timestamp='2024-01-15T12-00-00',
            file_size=512,
        )
        result = str(fcf)
        self.assertIn('test.xml', result)
        self.assertIn('512 bytes', result)

    def test_full_change_file_default_file_size(self):
        fcf = FullChangeFile.objects.create(
            filename='empty.xml',
            timestamp='2024-01-01T00-00-00',
        )
        self.assertEqual(fcf.file_size, 0)

    def test_full_change_file_nullable_urls(self):
        fcf = FullChangeFile.objects.create(
            filename='local.xml',
            timestamp='2024-01-01T00-00-00',
        )
        self.assertIsNone(fcf.bucket_url)
        self.assertIsNone(fcf.local_path)

    def test_full_change_file_ordering_newest_first(self):
        """Pliki są sortowane malejąco po dacie utworzenia"""
        fcf1 = FullChangeFile.objects.create(
            filename='a.xml', timestamp='2024-01-01T00-00-00'
        )
        fcf2 = FullChangeFile.objects.create(
            filename='b.xml', timestamp='2024-01-02T00-00-00'
        )
        files = list(FullChangeFile.objects.all())
        # Ostatnio utworzony (pk większy) powinien być pierwszy
        self.assertGreater(files[0].pk, files[1].pk)


# ==============================================================
# MODEL TESTS – Units & Vat
# ==============================================================

class UnitsModelTest(TestCase):
    """Testy modelu Units"""

    databases = {'default', 'MPD'}

    def test_unit_creation(self):
        unit = Units.objects.create(unit_id=101, name='Sztuka')
        self.assertEqual(unit.name, 'Sztuka')
        self.assertEqual(unit.unit_id, 101)

    def test_unit_str_with_name(self):
        unit = Units.objects.create(unit_id=102, name='Para')
        self.assertEqual(str(unit), 'Para')

    def test_unit_str_no_name(self):
        unit = Units.objects.create(unit_id=103, name=None)
        self.assertIn('103', str(unit))

    def test_unit_unique_unit_id_raises(self):
        Units.objects.create(unit_id=200, name='X')
        with self.assertRaises(Exception):
            Units.objects.create(unit_id=200, name='Y')


class VatModelTest(TestCase):
    """Testy modelu Vat"""

    databases = {'default', 'MPD'}

    def test_vat_creation(self):
        vat = Vat.objects.create(vat_rate=Decimal('23.00'))
        self.assertEqual(vat.vat_rate, Decimal('23.00'))
        self.assertIsNotNone(vat.pk)

    def test_vat_nullable_rate(self):
        vat = Vat.objects.create(vat_rate=None)
        self.assertIsNone(vat.vat_rate)


# ==============================================================
# MODEL TESTS – Paths & ProductPaths
# ==============================================================

class PathsModelTest(TestCase):
    """Testy modelu Paths"""

    databases = {'default', 'MPD'}

    def test_path_creation(self):
        path = Paths.objects.create(
            name='Odzież',
            path='odzież',
            iai_category_id=100,
        )
        self.assertEqual(path.name, 'Odzież')
        self.assertEqual(path.iai_category_id, 100)
        self.assertIsNotNone(path.pk)

    def test_path_with_parent_id(self):
        parent = Paths.objects.create(name='Odzież', path='odzież')
        child = Paths.objects.create(
            name='Bluzy', path='odzież/bluzy', parent_id=parent.id
        )
        self.assertEqual(child.parent_id, parent.id)

    def test_path_nullable_fields(self):
        path = Paths.objects.create()
        self.assertIsNone(path.name)
        self.assertIsNone(path.path)
        self.assertIsNone(path.parent_id)
        self.assertIsNone(path.iai_category_id)


class ProductPathsModelTest(TestCase):
    """Testy modelu ProductPaths"""

    databases = {'default', 'MPD'}

    def setUp(self):
        brand = Brands.objects.create(name='B')
        self.product = Products.objects.create(name='Prod', brand=brand)
        self.path = Paths.objects.create(name='Kat', path='kat')

    def test_product_path_creation(self):
        pp = ProductPaths.objects.create(
            product_id=self.product.id,
            path_id=self.path.id,
        )
        self.assertEqual(pp.product_id, self.product.id)
        self.assertEqual(pp.path_id, self.path.id)
        self.assertIsNotNone(pp.pk)

    def test_product_path_unique_together_raises(self):
        ProductPaths.objects.create(
            product_id=self.product.id, path_id=self.path.id
        )
        with self.assertRaises(Exception):
            ProductPaths.objects.create(
                product_id=self.product.id, path_id=self.path.id
            )

    def test_product_can_have_multiple_paths(self):
        path2 = Paths.objects.create(name='Kat2', path='kat2')
        pp1 = ProductPaths.objects.create(
            product_id=self.product.id, path_id=self.path.id
        )
        pp2 = ProductPaths.objects.create(
            product_id=self.product.id, path_id=path2.id
        )
        self.assertIsNotNone(pp1.pk)
        self.assertIsNotNone(pp2.pk)


# ==============================================================
# MODEL TESTS – Categories
# ==============================================================

class CategoriesModelTest(TestCase):
    """Testy modelu Categories"""

    databases = {'default', 'MPD'}

    def test_category_creation(self):
        cat = Categories.objects.create(
            name='Odzież', path='odzież'
        )
        self.assertEqual(cat.name, 'Odzież')
        self.assertEqual(cat.path, 'odzież')
        self.assertIsNotNone(cat.pk)

    def test_category_with_parent(self):
        parent = Categories.objects.create(name='Odzież', path='odzież')
        child = Categories.objects.create(
            name='Bluzy', path='odzież/bluzy', parent_id=parent.id
        )
        self.assertEqual(child.parent_id, parent.id)

    def test_category_nullable_fields(self):
        cat = Categories.objects.create()
        self.assertIsNone(cat.name)
        self.assertIsNone(cat.path)
        self.assertIsNone(cat.parent_id)


# ==============================================================
# SERIALIZER TESTS
# ==============================================================

class ProductSerializerTest(TestCase):
    """Testy ProductSerializer"""

    databases = {'default', 'MPD'}

    def setUp(self):
        brand = Brands.objects.create(name='Brand')
        self.product = Products.objects.create(
            name='Test Produkt', description='Opis testowy', brand=brand
        )

    def test_serializer_contains_expected_fields(self):
        serializer = ProductSerializer(instance=self.product)
        self.assertEqual(set(serializer.data.keys()), {'id', 'name', 'description'})

    def test_serializer_values(self):
        serializer = ProductSerializer(instance=self.product)
        self.assertEqual(serializer.data['name'], 'Test Produkt')
        self.assertEqual(serializer.data['description'], 'Opis testowy')
        self.assertEqual(serializer.data['id'], self.product.id)

    def test_serializer_no_brand_field(self):
        """ProductSerializer nie eksponuje pola brand (tylko id, name, description)"""
        serializer = ProductSerializer(instance=self.product)
        self.assertNotIn('brand', serializer.data)

    def test_serializer_null_description(self):
        product = Products.objects.create(name='Bez opisu')
        serializer = ProductSerializer(instance=product)
        self.assertIsNone(serializer.data['description'])


class ProductListSerializerTest(TestCase):
    """Testy ProductListSerializer"""

    databases = {'default', 'MPD'}

    def setUp(self):
        self.brand = Brands.objects.create(name='Moja Marka')
        self.product = Products.objects.create(
            name='Produkt Testowy',
            brand=self.brand,
            visibility=True,
        )

    def test_serializer_contains_expected_fields(self):
        serializer = ProductListSerializer(instance=self.product)
        expected = {'id', 'name', 'brand_name', 'visibility', 'created_at', 'updated_at'}
        self.assertEqual(set(serializer.data.keys()), expected)

    def test_serializer_brand_name_computed(self):
        serializer = ProductListSerializer(instance=self.product)
        self.assertEqual(serializer.data['brand_name'], 'Moja Marka')

    def test_serializer_no_brand_is_null_or_absent(self):
        """Gdy brak marki, brand_name jest None/pusty lub pole jest pomijane przez DRF"""
        product_no_brand = Products.objects.create(name='Bez marki')
        serializer = ProductListSerializer(instance=product_no_brand)
        # DRF CharField z source='brand.name' może pominąć pole (SkipField)
        # lub zwrócić None gdy brand=None — obie sytuacje są akceptowalne
        brand_name = serializer.data.get('brand_name', None)
        self.assertFalse(bool(brand_name))  # None lub pusty string → falsy

    def test_serializer_visibility_true(self):
        serializer = ProductListSerializer(instance=self.product)
        self.assertTrue(serializer.data['visibility'])

    def test_serializer_visibility_false(self):
        product_hidden = Products.objects.create(
            name='Ukryty', brand=self.brand, visibility=False
        )
        serializer = ProductListSerializer(instance=product_hidden)
        self.assertFalse(serializer.data['visibility'])

    def test_serializer_timestamps_not_none(self):
        serializer = ProductListSerializer(instance=self.product)
        self.assertIsNotNone(serializer.data['created_at'])
        self.assertIsNotNone(serializer.data['updated_at'])


# ==============================================================
# VIEW TESTS – manage_product_paths
# ==============================================================

@override_settings(DEBUG_TOOLBAR_CONFIG=DEBUG_TOOLBAR_OFF)
class ManageProductPathsViewTest(TestCase):
    """Testy widoku manage_product_paths"""

    databases = {'default', 'MPD'}

    def setUp(self):
        self.client = Client()
        brand = Brands.objects.using('MPD').create(name='B')
        self.product = Products.objects.using('MPD').create(name='Produkt', brand=brand)
        self.path = Paths.objects.using('MPD').create(name='Kat', path='kat')

    def _post(self, data):
        return self.client.post(
            '/mpd/manage-product-paths/',
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_assign_creates_product_path(self):
        response = self._post({
            'product_id': self.product.id,
            'path_id': self.path.id,
            'action': 'assign',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(
            ProductPaths.objects.using('MPD').filter(
                product_id=self.product.id, path_id=self.path.id
            ).exists()
        )

    def test_assign_idempotent_no_error(self):
        """Podwójne przypisanie nie rzuca błędu — get_or_create jest idempotentne"""
        self._post({'product_id': self.product.id, 'path_id': self.path.id, 'action': 'assign'})
        response = self._post({'product_id': self.product.id, 'path_id': self.path.id, 'action': 'assign'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ProductPaths.objects.using('MPD').filter(
                product_id=self.product.id, path_id=self.path.id
            ).count(),
            1,
        )

    def test_unassign_removes_product_path(self):
        ProductPaths.objects.using('MPD').create(
            product_id=self.product.id, path_id=self.path.id
        )
        response = self._post({
            'product_id': self.product.id,
            'path_id': self.path.id,
            'action': 'unassign',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ProductPaths.objects.using('MPD').filter(
                product_id=self.product.id, path_id=self.path.id
            ).exists()
        )

    def test_unassign_nonexistent_path_still_200(self):
        """Usunięcie nieistniejącego przypisania zwraca 200 (brak rekordu)"""
        response = self._post({
            'product_id': self.product.id,
            'path_id': self.path.id,
            'action': 'unassign',
        })
        self.assertEqual(response.status_code, 200)

    def test_missing_product_id_returns_400(self):
        response = self._post({'path_id': self.path.id, 'action': 'assign'})
        self.assertEqual(response.status_code, 400)

    def test_missing_path_id_returns_400(self):
        response = self._post({'product_id': self.product.id, 'action': 'assign'})
        self.assertEqual(response.status_code, 400)

    def test_missing_action_returns_400(self):
        response = self._post({
            'product_id': self.product.id,
            'path_id': self.path.id,
        })
        self.assertEqual(response.status_code, 400)

    def test_invalid_action_returns_400(self):
        response = self._post({
            'product_id': self.product.id,
            'path_id': self.path.id,
            'action': 'delete',
        })
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_product_returns_404(self):
        response = self._post({
            'product_id': 999999,
            'path_id': self.path.id,
            'action': 'assign',
        })
        self.assertEqual(response.status_code, 404)

    def test_get_method_returns_405(self):
        response = self.client.get('/mpd/manage-product-paths/')
        self.assertEqual(response.status_code, 405)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            '/mpd/manage-product-paths/',
            data='nie-json{',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_response_contains_product_id_and_path_id(self):
        response = self._post({
            'product_id': self.product.id,
            'path_id': self.path.id,
            'action': 'assign',
        })
        data = response.json()
        self.assertEqual(data['product_id'], self.product.id)
        self.assertEqual(data['path_id'], self.path.id)
        self.assertEqual(data['action'], 'assign')


# ==============================================================
# VIEW TESTS – manage_product_fabric
# ==============================================================

@override_settings(DEBUG_TOOLBAR_CONFIG=DEBUG_TOOLBAR_OFF)
class ManageProductFabricViewTest(TestCase):
    """Testy widoku manage_product_fabric"""

    databases = {'default', 'MPD'}

    def setUp(self):
        self.client = Client()
        brand = Brands.objects.using('MPD').create(name='B')
        self.product = Products.objects.using('MPD').create(name='Produkt', brand=brand)
        self.component = FabricComponent.objects.using('MPD').create(name='Bawełna')

    def _post(self, data):
        return self.client.post(
            '/mpd/manage-product-fabric/',
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_add_fabric_component(self):
        response = self._post({
            'product_id': self.product.id,
            'action': 'add',
            'component_id': self.component.id,
            'percentage': 80,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(
            ProductFabric.objects.using('MPD').filter(
                product_id=self.product.id, component_id=self.component.id
            ).exists()
        )

    def test_add_fabric_duplicate_returns_400(self):
        ProductFabric.objects.using('MPD').create(
            product=self.product, component=self.component, percentage=50
        )
        response = self._post({
            'product_id': self.product.id,
            'action': 'add',
            'component_id': self.component.id,
            'percentage': 30,
        })
        self.assertEqual(response.status_code, 400)

    def test_remove_fabric_component(self):
        ProductFabric.objects.using('MPD').create(
            product=self.product, component=self.component, percentage=50
        )
        response = self._post({
            'product_id': self.product.id,
            'action': 'remove',
            'component_id': self.component.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ProductFabric.objects.using('MPD').filter(
                product_id=self.product.id, component_id=self.component.id
            ).exists()
        )

    def test_remove_nonexistent_fabric_still_200(self):
        """Usunięcie nieistniejącego składnika zwraca 200 ze status success"""
        response = self._post({
            'product_id': self.product.id,
            'action': 'remove',
            'component_id': self.component.id,
        })
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_product_returns_404(self):
        response = self._post({
            'product_id': 999999,
            'action': 'add',
            'component_id': self.component.id,
            'percentage': 50,
        })
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_component_returns_404(self):
        response = self._post({
            'product_id': self.product.id,
            'action': 'add',
            'component_id': 999999,
            'percentage': 50,
        })
        self.assertEqual(response.status_code, 404)

    def test_missing_product_id_returns_400(self):
        response = self._post({'action': 'add', 'component_id': self.component.id, 'percentage': 50})
        self.assertEqual(response.status_code, 400)

    def test_missing_action_returns_400(self):
        response = self._post({'product_id': self.product.id})
        self.assertEqual(response.status_code, 400)

    def test_invalid_action_returns_400(self):
        response = self._post({
            'product_id': self.product.id,
            'action': 'update',
        })
        self.assertEqual(response.status_code, 400)

    def test_add_missing_percentage_returns_400(self):
        response = self._post({
            'product_id': self.product.id,
            'action': 'add',
            'component_id': self.component.id,
        })
        self.assertEqual(response.status_code, 400)

    def test_get_method_returns_405(self):
        response = self.client.get('/mpd/manage-product-fabric/')
        self.assertEqual(response.status_code, 405)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            '/mpd/manage-product-fabric/',
            data='nie-json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


# ==============================================================
# VIEW TESTS – manage_product_attributes
# ==============================================================

@override_settings(DEBUG_TOOLBAR_CONFIG=DEBUG_TOOLBAR_OFF)
class ManageProductAttributesViewTest(TestCase):
    """Testy widoku manage_product_attributes"""

    databases = {'default', 'MPD'}

    def setUp(self):
        self.client = Client()
        brand = Brands.objects.using('MPD').create(name='B')
        self.product = Products.objects.using('MPD').create(name='Produkt', brand=brand)
        self.attr = Attributes.objects.using('MPD').create(name='Kolor')

    def _post(self, data):
        return self.client.post(
            '/mpd/manage-product-attributes/',
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_add_attribute_creates_relation(self):
        response = self._post({
            'product_id': self.product.id,
            'action': 'add',
            'attribute_ids': [self.attr.id],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(
            ProductAttribute.objects.using('MPD').filter(
                product_id=self.product.id, attribute_id=self.attr.id
            ).exists()
        )

    def test_add_multiple_attributes(self):
        attr2 = Attributes.objects.using('MPD').create(name='Materiał')
        response = self._post({
            'product_id': self.product.id,
            'action': 'add',
            'attribute_ids': [self.attr.id, attr2.id],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ProductAttribute.objects.using('MPD').filter(
                product_id=self.product.id
            ).count(),
            2,
        )

    def test_add_attribute_idempotent(self):
        """Dodanie już istniejącego atrybutu nie tworzy duplikatu (get_or_create)"""
        self._post({
            'product_id': self.product.id,
            'action': 'add',
            'attribute_ids': [self.attr.id],
        })
        response = self._post({
            'product_id': self.product.id,
            'action': 'add',
            'attribute_ids': [self.attr.id],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ProductAttribute.objects.using('MPD').filter(
                product_id=self.product.id, attribute_id=self.attr.id
            ).count(),
            1,
        )

    def test_remove_attribute_deletes_relation(self):
        ProductAttribute.objects.using('MPD').create(
            product=self.product, attribute=self.attr
        )
        response = self._post({
            'product_id': self.product.id,
            'action': 'remove',
            'attribute_id': self.attr.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ProductAttribute.objects.using('MPD').filter(
                product_id=self.product.id, attribute_id=self.attr.id
            ).exists()
        )

    def test_remove_nonexistent_attribute_returns_404(self):
        """Usunięcie atrybutu niepowiązanego z produktem zwraca 404"""
        response = self._post({
            'product_id': self.product.id,
            'action': 'remove',
            'attribute_id': self.attr.id,
        })
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_product_returns_404(self):
        response = self._post({
            'product_id': 999999,
            'action': 'add',
            'attribute_ids': [self.attr.id],
        })
        self.assertEqual(response.status_code, 404)

    def test_missing_product_id_returns_400(self):
        response = self._post({'action': 'add', 'attribute_ids': [self.attr.id]})
        self.assertEqual(response.status_code, 400)

    def test_missing_action_returns_400(self):
        response = self._post({'product_id': self.product.id})
        self.assertEqual(response.status_code, 400)

    def test_invalid_action_returns_400(self):
        response = self._post({
            'product_id': self.product.id,
            'action': 'update',
        })
        self.assertEqual(response.status_code, 400)

    def test_add_empty_attribute_ids_returns_400(self):
        response = self._post({
            'product_id': self.product.id,
            'action': 'add',
            'attribute_ids': [],
        })
        self.assertEqual(response.status_code, 400)

    def test_get_method_returns_405(self):
        response = self.client.get('/mpd/manage-product-attributes/')
        self.assertEqual(response.status_code, 405)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            '/mpd/manage-product-attributes/',
            data='nieprawidlowy-json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


# ==============================================================
# VIEW TESTS – create_product
# ==============================================================

@override_settings(DEBUG_TOOLBAR_CONFIG=DEBUG_TOOLBAR_OFF)
class CreateProductViewTest(TestCase):
    """Testy widoku create_product"""

    databases = {'default', 'MPD'}

    def setUp(self):
        self.client = Client()
        self.brand = Brands.objects.using('MPD').create(name='Brand Testowy')

    def _post(self, data):
        return self.client.post(
            '/mpd/products/create/',
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_create_product_minimal(self):
        response = self._post({'name': 'Nowy produkt'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('product_id', data)
        self.assertTrue(
            Products.objects.using('MPD').filter(id=data['product_id']).exists()
        )

    def test_create_product_with_brand(self):
        response = self._post({
            'name': 'Produkt z marką',
            'brand_id': self.brand.id,
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        product = Products.objects.using('MPD').get(id=data['product_id'])
        self.assertEqual(product.brand_id, self.brand.id)

    def test_create_product_full_fields(self):
        response = self._post({
            'name': 'Pełny produkt',
            'description': 'Szczegółowy opis',
            'short_description': 'Krótki',
            'brand_id': self.brand.id,
            'visibility': False,
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        product = Products.objects.using('MPD').get(id=data['product_id'])
        self.assertEqual(product.name, 'Pełny produkt')
        self.assertEqual(product.description, 'Szczegółowy opis')
        self.assertFalse(product.visibility)

    def test_create_product_missing_name_returns_400(self):
        response = self._post({'description': 'Opis bez nazwy'})
        self.assertEqual(response.status_code, 400)

    def test_create_product_empty_name_returns_400(self):
        response = self._post({'name': ''})
        self.assertEqual(response.status_code, 400)

    def test_create_product_get_returns_405(self):
        response = self.client.get('/mpd/products/create/')
        self.assertEqual(response.status_code, 405)

    def test_create_product_invalid_json_returns_400(self):
        response = self.client.post(
            '/mpd/products/create/',
            data='to-nie-jest-json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_create_product_response_contains_name(self):
        response = self._post({'name': 'Produkt XYZ'})
        data = response.json()
        self.assertEqual(data['product_name'], 'Produkt XYZ')

    def test_create_product_with_variants(self):
        color = Colors.objects.using('MPD').create(name='Czerwony')
        size = Sizes.objects.using('MPD').create(name='M', category='default')
        response = self._post({
            'name': 'Produkt z wariantami',
            'variants': [
                {'color_id': color.id, 'size_id': size.id},
                {'color_id': color.id, 'size_id': None},
            ],
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['variants_created'], 2)
        self.assertEqual(len(data['variants']), 2)

    def test_create_product_with_variant_and_price(self):
        color = Colors.objects.using('MPD').create(name='Niebieski')
        size = Sizes.objects.using('MPD').create(name='L', category='default')
        response = self._post({
            'name': 'Produkt z ceną',
            'variants': [
                {
                    'color_id': color.id,
                    'size_id': size.id,
                    'price': '149.99',
                    'vat': 23.0,
                    'currency': 'PLN',
                }
            ],
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        variant_id = data['variants'][0]
        self.assertTrue(
            ProductVariantsRetailPrice.objects.using('MPD').filter(
                variant_id=variant_id
            ).exists()
        )

    def test_create_product_with_path_ids(self):
        path = Paths.objects.using('MPD').create(name='Kat', path='kat')
        response = self._post({
            'name': 'Produkt ze ścieżką',
            'path_ids': [path.id],
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(
            ProductPaths.objects.using('MPD').filter(
                product_id=data['product_id'], path_id=path.id
            ).exists()
        )

    def test_create_product_with_attribute_ids(self):
        attr = Attributes.objects.using('MPD').create(name='Kolor')
        response = self._post({
            'name': 'Produkt z atrybutem',
            'attribute_ids': [attr.id],
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(
            ProductAttribute.objects.using('MPD').filter(
                product_id=data['product_id'], attribute_id=attr.id
            ).exists()
        )

    def test_create_product_default_visibility_true(self):
        """Domyślna widoczność produktu to True"""
        response = self._post({'name': 'Domyślna widoczność'})
        data = response.json()
        product = Products.objects.using('MPD').get(id=data['product_id'])
        self.assertTrue(product.visibility)
