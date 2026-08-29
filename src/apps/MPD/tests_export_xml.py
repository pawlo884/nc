"""
Testy dla eksportera XML (format IOF) w apps.MPD.export_to_xml.

Pokrywają treść generowanego XML (nie tylko status HTTP endpointów, jak w tests.py):
- ProducersXMLExporter, StocksXMLExporter, UnitsXMLExporter,
  CategoriesXMLExporter, SizesXMLExporter, LightXMLExporter, GatewayXMLExporter
- FullXMLExporter (pełna struktura oferty)
- Funkcje pomocnicze napędzające eksport przyrostowy (exported_to_iai)
- BaseXMLExporter.save_local
"""
import os
import xml.etree.ElementTree as ET
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from matterhorn1.defs_db import BUCKET_PUBLIC_BASE_URL

from .models import (
    Brands, Colors, Products, ProductVariants, Sizes, Sources,
    StockAndPrices, ProductVariantsRetailPrice, ProductvariantsSources,
    Paths, Units, FullChangeFile, Vat,
)
from .export_to_xml import (
    ProducersXMLExporter, StocksXMLExporter, UnitsXMLExporter,
    CategoriesXMLExporter, SizesXMLExporter, LightXMLExporter,
    FullXMLExporter, FullChangeXMLExporter, GatewayXMLExporter,
    get_last_full_xml_date, get_last_full_change_xml_date,
    get_products_exported_in_full_xml, mark_existing_variants_as_exported,
)


class ProducersXMLExporterTest(TestCase):
    databases = {'default', 'MPD'}

    def test_generate_xml_includes_only_brands_with_iai_id(self):
        Brands.objects.using('MPD').create(name='Nike', iai_brand_id=101)
        Brands.objects.using('MPD').create(name='Bez ID', iai_brand_id=None)

        root = ET.fromstring(ProducersXMLExporter().generate_xml())

        self.assertEqual(root.tag, 'producers')
        self.assertEqual(root.get('file_format'), 'IOF')
        self.assertEqual(root.get('version'), '3.0')

        producers = root.findall('producer')
        self.assertEqual(len(producers), 1)
        self.assertEqual(producers[0].get('id'), '101')
        self.assertEqual(producers[0].get('name'), 'Nike')

    def test_generate_xml_escapes_special_characters_in_name(self):
        Brands.objects.using('MPD').create(
            name='M&M\'s <Test>', iai_brand_id=202)

        root = ET.fromstring(ProducersXMLExporter().generate_xml())

        self.assertEqual(root.find('producer').get('name'), "M&M's <Test>")


class StocksXMLExporterTest(TestCase):
    # Sygnał post_save(Sources) próbuje uruchomić task dopinania wariantów przez zzz_MPD.
    databases = {'default', 'MPD', 'zzz_MPD'}

    def test_generate_xml_lists_stock_per_variant(self):
        source = Sources.objects.using('MPD').create(
            name='Magazyn', type='Magazyn główny')
        product = Products.objects.using('MPD').create(name='Buty testowe')
        variant = ProductVariants.objects.using('MPD').create(product=product)
        StockAndPrices.objects.using('MPD').create(
            variant=variant, source=source, stock=10, price=99.99,
            currency='PLN', last_updated=timezone.now(),
        )

        root = ET.fromstring(StocksXMLExporter().generate_xml())

        self.assertEqual(root.tag, 'stocks')
        stocks = root.findall('stock')
        self.assertEqual(len(stocks), 1)
        self.assertEqual(stocks[0].get('id'), str(variant.variant_id))
        self.assertEqual(stocks[0].get('name'), 'Buty testowe')


class UnitsXMLExporterTest(TestCase):
    databases = {'default', 'MPD'}

    def test_generate_xml_lists_all_units(self):
        Units.objects.using('MPD').create(unit_id=1, name='szt.')
        Units.objects.using('MPD').create(unit_id=2, name='para')

        root = ET.fromstring(UnitsXMLExporter().generate_xml())

        self.assertEqual(root.tag, 'units')
        units = {(u.get('id'), u.get('name')) for u in root.findall('unit')}
        self.assertEqual(units, {('1', 'szt.'), ('2', 'para')})


class CategoriesXMLExporterTest(TestCase):
    databases = {'default', 'MPD'}

    def test_generate_xml_builds_nested_category_tree(self):
        root_path = Paths.objects.using('MPD').create(
            name='Moda damska', path='Moda damska', parent_id=None,
            iai_category_id=500)
        Paths.objects.using('MPD').create(
            name='Bielizna', path='Moda damska\\Bielizna',
            parent_id=root_path.id, iai_category_id=501)

        root = ET.fromstring(CategoriesXMLExporter().generate_xml())

        self.assertEqual(root.tag, 'categories')
        top_category = root.find('category')
        self.assertEqual(top_category.get('id'), '500')
        self.assertEqual(top_category.find('name').text, 'Moda damska')

        nested_category = top_category.find('category')
        self.assertEqual(nested_category.get('id'), '501')
        self.assertEqual(nested_category.find('name').text, 'Bielizna')

    def test_generate_xml_falls_back_to_pk_without_iai_category_id(self):
        path = Paths.objects.using('MPD').create(
            name='Bez ID', path='Bez ID', parent_id=None,
            iai_category_id=None)

        root = ET.fromstring(CategoriesXMLExporter().generate_xml())

        self.assertEqual(root.find('category').get('id'), str(path.id))


class SizesXMLExporterTest(TestCase):
    databases = {'default', 'MPD'}

    def test_generate_xml_groups_sizes_by_category(self):
        Sizes.objects.using('MPD').create(
            name='S', category='Ubrania', iai_size_id='10')
        Sizes.objects.using('MPD').create(
            name='M', category='Ubrania', iai_size_id='11')
        Sizes.objects.using('MPD').create(
            name='40', category='Buty', iai_size_id='20')
        # Rozmiar bez kategorii - wykluczony przez filtr category__isnull=False
        Sizes.objects.using('MPD').create(name='Bez kategorii', category=None)

        root = ET.fromstring(SizesXMLExporter().generate_xml())

        self.assertEqual(root.tag, 'sizes')
        groups = root.findall('group')
        self.assertEqual({g.get('name') for g in groups}, {'Ubrania', 'Buty'})

        ubrania_group = next(g for g in groups if g.get('name') == 'Ubrania')
        self.assertEqual(
            {s.get('id') for s in ubrania_group.findall('size')},
            {'10', '11'},
        )


class LightXMLExporterTest(TestCase):
    """light.xml eksportuje tylko produkty ze zmienionymi cenami/stanami z ostatniej godziny."""

    # Sygnał post_save(Sources) próbuje uruchomić task dopinania wariantów przez zzz_MPD.
    databases = {'default', 'MPD', 'zzz_MPD'}

    def _create_product_with_stock(self, last_updated):
        brand = Brands.objects.using('MPD').create(name='Marka', iai_brand_id=1)
        product = Products.objects.using('MPD').create(
            name='Produkt testowy', brand=brand)
        size = Sizes.objects.using('MPD').create(
            name='M', category='Ubrania', iai_size_id='11')
        variant = ProductVariants.objects.using('MPD').create(
            product=product, size=size)
        source = Sources.objects.using('MPD').create(
            name='Magazyn', type='Magazyn główny')
        StockAndPrices.objects.using('MPD').create(
            variant=variant, source=source, stock=7, price=50,
            currency='PLN', last_updated=last_updated,
        )
        return product, variant

    def test_generate_xml_includes_recently_changed_stock(self):
        product, variant = self._create_product_with_stock(timezone.now())

        root = ET.fromstring(LightXMLExporter().generate_xml())

        self.assertEqual(root.tag, 'offer')
        product_el = root.find('.//product')
        self.assertIsNotNone(product_el)
        self.assertEqual(product_el.get('id'), str(product.id))

        size_el = product_el.find('.//size')
        self.assertEqual(size_el.get('id'), '11')
        stock_el = size_el.find('stock')
        self.assertEqual(stock_el.get('quantity'), '7')
        self.assertEqual(stock_el.get('id'), '1')  # Magazyn główny -> id=1

    def test_generate_xml_excludes_products_without_recent_changes(self):
        self._create_product_with_stock(timezone.now() - timedelta(hours=5))

        root = ET.fromstring(LightXMLExporter().generate_xml())

        self.assertEqual(root.findall('.//product'), [])


class GatewayXMLExporterTest(TestCase):
    # Sygnał post_save(Sources) próbuje uruchomić task dopinania wariantów przez zzz_MPD.
    databases = {'default', 'MPD', 'zzz_MPD'}

    def test_constructor_requires_matterhorn_source(self):
        with self.assertRaises(ValueError):
            GatewayXMLExporter()

    def test_generate_xml_links_to_other_iof_files(self):
        # GatewayXMLExporter.__init__ czyta Sources bez .using('MPD') (alias 'default':
        # w testach to osobna transakcja niż 'MPD', mimo że mirroruje tę samą fizyczną bazę),
        # więc tworzymy rekord przez ten sam alias, żeby był widoczny przy odczycie.
        Sources.objects.create(id=2, name='Matterhorn', type='api')

        root = ET.fromstring(GatewayXMLExporter().generate_xml())

        self.assertEqual(root.tag, 'provider_description')
        for tag in ('full', 'light', 'categories', 'sizes', 'producers'):
            self.assertIsNotNone(
                root.find(tag), f'brak węzła <{tag}> w gateway.xml')
        self.assertTrue(
            root.find('full').get('url').endswith('/mpd/generate-full-xml/'))

    def test_generate_xml_skips_changes_hosted_on_decommissioned_bucket(self):
        """
        FullChangeFile.bucket_url zapisuje URL bucketa z chwili wgrania pliku. Po migracji
        storage (np. DigitalOcean Spaces -> MinIO) stare rekordy nadal mają stary,
        martwy URL - gateway.xml nie powinien go reklamować w <changes>.
        """
        Sources.objects.create(id=2, name='Matterhorn', type='api')
        FullChangeFile.objects.using('MPD').create(
            filename='full_change2026-01-01T00-00-00.xml',
            timestamp='2026-01-01T00-00-00',
            bucket_url=f'{BUCKET_PUBLIC_BASE_URL}/MPD_test/xml/full_change2026-01-01T00-00-00.xml',
        )
        FullChangeFile.objects.using('MPD').create(
            filename='full_change2025-01-01T00-00-00.xml',
            timestamp='2025-01-01T00-00-00',
            bucket_url='https://mojbucket.fra1.digitaloceanspaces.com/MPD_test/xml/full_change2025-01-01T00-00-00.xml',
        )

        root = ET.fromstring(GatewayXMLExporter().generate_xml())

        change_urls = {
            c.get('url') for c in root.findall('.//full/changes/change')}
        self.assertTrue(
            any(BUCKET_PUBLIC_BASE_URL in url for url in change_urls))
        self.assertFalse(
            any('digitaloceanspaces.com' in url for url in change_urls))


class ExportHelperFunctionsTest(TestCase):
    """Logika eksportu przyrostowego (flaga exported_to_iai i daty ostatnich plików)."""

    databases = {'default', 'MPD'}

    def test_get_last_full_xml_date_returns_none_without_history(self):
        self.assertIsNone(get_last_full_xml_date())

    def test_get_last_full_xml_date_returns_latest_full_xml_timestamp(self):
        FullChangeFile.objects.using('MPD').create(
            filename='full.xml', timestamp='2026-01-01T00-00-00')
        newest = FullChangeFile.objects.using('MPD').create(
            filename='full.xml', timestamp='2026-01-02T00-00-00')
        FullChangeFile.objects.using('MPD').create(
            filename='light.xml', timestamp='2026-01-03T00-00-00')

        self.assertEqual(get_last_full_xml_date(), newest.created_at)

    def test_get_last_full_change_xml_date_matches_prefixed_files_only(self):
        FullChangeFile.objects.using('MPD').create(
            filename='full.xml', timestamp='2026-01-01T00-00-00')
        change = FullChangeFile.objects.using('MPD').create(
            filename='full_change2026-01-02T00-00-00.xml',
            timestamp='2026-01-02T00-00-00')

        self.assertEqual(get_last_full_change_xml_date(), change.created_at)

    def test_get_products_exported_in_full_xml(self):
        product = Products.objects.using('MPD').create(name='Produkt')
        other_product = Products.objects.using('MPD').create(name='Inny')
        ProductVariants.objects.using('MPD').create(
            product=product, exported_to_iai=True)
        ProductVariants.objects.using('MPD').create(
            product=other_product, exported_to_iai=False)

        self.assertEqual(get_products_exported_in_full_xml(), {product.id})

    def test_mark_existing_variants_as_exported(self):
        product = Products.objects.using('MPD').create(name='Produkt')
        v1 = ProductVariants.objects.using('MPD').create(
            product=product, exported_to_iai=False)
        v2 = ProductVariants.objects.using('MPD').create(
            product=product, exported_to_iai=True)

        updated_count = mark_existing_variants_as_exported()

        self.assertEqual(updated_count, 1)
        v1.refresh_from_db(using='MPD')
        v2.refresh_from_db(using='MPD')
        self.assertTrue(v1.exported_to_iai)
        self.assertTrue(v2.exported_to_iai)


class BaseXMLExporterSaveLocalTest(TestCase):
    def test_save_local_writes_file_to_disk(self):
        exporter = ProducersXMLExporter()
        exporter.filename = 'test_save_local_tmp.xml'
        local_path = exporter.save_local('<producers></producers>')
        try:
            self.assertTrue(os.path.exists(local_path))
            with open(local_path, encoding='utf-8') as f:
                self.assertEqual(f.read(), '<producers></producers>')
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)


class FullXMLExporterTest(TestCase):
    """full.xml to najważniejszy plik oferty - pełne dane produktu, rozmiary, ceny, stany."""

    # Sygnał post_save(Sources) próbuje uruchomić task dopinania wariantów przez zzz_MPD.
    databases = {'default', 'MPD', 'zzz_MPD'}

    def setUp(self):
        self.brand = Brands.objects.using('MPD').create(
            name='Marka', iai_brand_id=1)
        self.product = Products.objects.using('MPD').create(
            name='Sukienka', brand=self.brand, description='Opis',
            short_description='Krótki opis')
        self.color = Colors.objects.using('MPD').create(
            name='Czerwony', iai_colors_id=5)
        self.size = Sizes.objects.using('MPD').create(
            name='M', category='Sukienki', iai_size_id='11')
        self.variant = ProductVariants.objects.using('MPD').create(
            product=self.product, color=self.color, size=self.size)
        ProductvariantsSources.objects.using('MPD').create(
            variant=self.variant, ean='5901234123457')
        self.source = Sources.objects.using('MPD').create(
            name='Magazyn', type='Magazyn główny')
        StockAndPrices.objects.using('MPD').create(
            variant=self.variant, source=self.source, stock=4, price=100,
            currency='PLN', last_updated=timezone.now(),
        )
        # pvrp.vat przechowuje id wiersza w tabeli Vat, nie samą stawkę
        vat = Vat.objects.using('MPD').create(vat_rate=23)
        ProductVariantsRetailPrice.objects.using('MPD').create(
            variant=self.variant, retail_price=123, net_price=100,
            vat=vat.id, currency='PLN',
        )

    def test_generate_xml_full_offer_structure(self):
        xml_content, exported_variant_ids = FullXMLExporter().generate_xml(
            incremental=False)
        root = ET.fromstring(xml_content)

        self.assertEqual(root.tag, 'offer')
        self.assertEqual(root.get('file_format'), 'IOF')

        product_el = root.find('.//product')
        self.assertIsNotNone(product_el)
        self.assertEqual(product_el.get('id'), str(self.product.id))
        self.assertEqual(product_el.get('vat'), '23.00')
        self.assertEqual(product_el.find('producer').get('id'), '1')
        self.assertEqual(
            product_el.find('description/name').text, 'Sukienka')
        self.assertIn(self.variant.variant_id, exported_variant_ids)

        size_el = product_el.find('.//size')
        self.assertEqual(size_el.get('code_producer'), '5901234123457')
        self.assertEqual(size_el.find('stock').get('quantity'), '4')

    def test_generate_xml_incremental_includes_variant_with_null_updated_at(self):
        # Wariant wstawiony z pominięciem ORM (np. bezpośrednim SQL-em z importu) ma
        # updated_at=NULL - auto_now nigdy go nie ustawiło. NULL >= data jest zawsze
        # fałszywe w SQL, więc bez jawnego dopuszczenia NULL taki wariant nigdy by się
        # nie pojawił w przyrostowym full.xml.
        FullChangeFile.objects.using('MPD').create(
            filename='full.xml', timestamp='2026-01-01T00-00-00')
        ProductVariants.objects.using('MPD').filter(
            variant_id=self.variant.variant_id
        ).update(updated_at=None)

        xml_content, exported_variant_ids = FullXMLExporter().generate_xml(
            incremental=True)

        self.assertIn(self.variant.variant_id, exported_variant_ids)
        root = ET.fromstring(xml_content)
        self.assertIsNotNone(root.find('.//product'))


class FullChangeXMLExporterTest(TestCase):
    """full_change.xml - plik różnicowy z opisami/parametrami zmienionych produktów."""

    databases = {'default', 'MPD', 'zzz_MPD'}

    def setUp(self):
        self.brand = Brands.objects.using('MPD').create(
            name='Marka', iai_brand_id=1)
        self.product = Products.objects.using('MPD').create(
            name='Kurtka', brand=self.brand)
        self.size = Sizes.objects.using('MPD').create(
            name='M', category='Kurtki', iai_size_id='11')
        self.variant = ProductVariants.objects.using('MPD').create(
            product=self.product, size=self.size)
        ProductvariantsSources.objects.using('MPD').create(
            variant=self.variant, ean='5901234123457')
        source = Sources.objects.using('MPD').create(
            name='Magazyn', type='Magazyn główny')
        StockAndPrices.objects.using('MPD').create(
            variant=self.variant, source=source, stock=2, price=100,
            currency='PLN', last_updated=timezone.now(),
        )

    def test_generate_xml_full_offer_structure(self):
        # incremental=False omija has_products_to_export()/śledzenie ostatniego
        # full_change.xml i eksportuje wszystkie warianty wprost - to samo grupowanie
        # po iai_product_id, w którym był AttributeError (usunięte pole modelu).
        xml_content = FullChangeXMLExporter().generate_xml(incremental=False)
        root = ET.fromstring(xml_content)

        self.assertEqual(root.tag, 'offer')
        product_el = root.find('.//product')
        self.assertIsNotNone(product_el)
        self.assertEqual(product_el.get('id'), str(self.product.id))

        size_el = product_el.find('.//size')
        self.assertEqual(size_el.get('code_producer'), '5901234123457')
        self.assertEqual(size_el.find('stock').get('quantity'), '2')
