"""
Testy exporter.py (build_product_xml/push_product/build_combination_xml/
push_combination/push_stock). Klient PrestaShop jest mockowany - zero
realnych wywołań HTTP.
"""
from decimal import Decimal
from unittest.mock import MagicMock

from django.test import TestCase

from MPD.models import (
    Brands,
    Colors,
    Paths,
    ProductPaths,
    ProductVariants,
    ProductVariantsRetailPrice,
    Products,
    ProductvariantsSources,
    Sizes,
    StockAndPrices,
    Sources,
)

from .api_client import PrestaShopApiError
from .exporter import (
    build_combination_xml,
    build_product_xml,
    push_combination,
    push_product,
    push_stock,
)


def _create_response(root_tag: str, new_id: int) -> bytes:
    return f'<prestashop><{root_tag}><id>{new_id}</id></{root_tag}></prestashop>'.encode()


class BuildProductXmlTest(TestCase):
    databases = {'default', 'MPD'}

    def setUp(self):
        self.brand = Brands.objects.using('MPD').create(name='Marka')
        self.product = Products.objects.using('MPD').create(
            name='Sukienka Test', brand=self.brand, visibility=True,
            description='Opis', short_description='Krótki opis')
        self.path = Paths.objects.using('MPD').create(
            name='Sukienki', presta_category_id=13)
        ProductPaths.objects.using('MPD').create(
            product=self.product, path=self.path)
        self.color = Colors.objects.using('MPD').create(name='Czerwony')
        self.size = Sizes.objects.using('MPD').create(name='M')
        self.variant = ProductVariants.objects.using('MPD').create(
            product=self.product, color=self.color, size=self.size)
        ProductVariantsRetailPrice.objects.using('MPD').create(
            variant=self.variant, net_price=Decimal('99.99'), currency='PLN')
        ProductvariantsSources.objects.using('MPD').create(
            variant=self.variant, ean='1234567890123')
        self.client = MagicMock()

    def test_raises_when_no_category_assigned(self):
        product_no_path = Products.objects.using('MPD').create(name='Bez ścieżki')
        with self.assertRaises(PrestaShopApiError):
            build_product_xml(product_no_path, self.client)

    def test_builds_expected_fields(self):
        xml_body = build_product_xml(self.product, self.client)

        self.assertIn(b'<id_category_default><![CDATA[13]]>', xml_body)
        self.assertIn(b'<active><![CDATA[1]]>', xml_body)
        self.assertIn(b'<price><![CDATA[99.99]]>', xml_body)
        self.assertIn(b'1234567890123', xml_body)
        self.assertIn('Sukienka Test'.encode(), xml_body)
        # Nowy produkt (brak presta_product_id) - nie wolno wysyłać <id> na
        # poziomie <product> (odróżnij od <id> w <associations><categories>,
        # które są zawsze obecne).
        self.assertNotIn(b'<product>\n    <id>', xml_body)

    def test_active_reflects_visibility_false(self):
        self.product.visibility = False
        xml_body = build_product_xml(self.product, self.client)
        self.assertIn(b'<active><![CDATA[0]]>', xml_body)

    def test_includes_id_when_already_pushed(self):
        self.product.presta_product_id = 21
        xml_body = build_product_xml(self.product, self.client)
        self.assertIn(b'<id><![CDATA[21]]></id>', xml_body)

    def test_dry_run_shows_placeholder_for_unmapped_category_without_api_calls(self):
        unmapped_path = Paths.objects.using('MPD').create(name='Nowa kategoria')
        ProductPaths.objects.using('MPD').create(
            product=self.product, path=unmapped_path)
        # Usuń pierwotne przypisanie, żeby jedyną ścieżką była ta niezmapowana
        ProductPaths.objects.using('MPD').filter(path=self.path).delete()

        xml_body = build_product_xml(self.product, self.client, dry_run=True)

        self.assertIn(b'NOWA:Nowa kategoria', xml_body)
        self.client.create.assert_not_called()


class PushProductTest(TestCase):
    databases = {'default', 'MPD'}

    def setUp(self):
        self.brand = Brands.objects.using('MPD').create(name='Marka')
        self.product = Products.objects.using('MPD').create(
            name='Produkt', brand=self.brand)
        self.path = Paths.objects.using('MPD').create(
            name='Kat', presta_category_id=5)
        ProductPaths.objects.using('MPD').create(
            product=self.product, path=self.path)

    def test_create_calls_post_and_persists_id(self):
        client = MagicMock()
        client.create.return_value = _create_response('product', 21)

        result = push_product(self.product, client)

        self.assertEqual(result, 21)
        client.create.assert_called_once()
        client.update.assert_not_called()
        self.product.refresh_from_db(using='MPD')
        self.assertEqual(self.product.presta_product_id, 21)

    def test_update_calls_put_when_already_pushed(self):
        self.product.presta_product_id = 21
        self.product.save(using='MPD', update_fields=['presta_product_id'])
        client = MagicMock()

        result = push_product(self.product, client)

        self.assertEqual(result, 21)
        client.update.assert_called_once()
        client.create.assert_not_called()
        args, _ = client.update.call_args
        self.assertEqual(args[0], 'products')
        self.assertEqual(args[1], 21)


class CombinationDefaultOnTest(TestCase):
    """Dokładnie jeden combination per produkt może mieć default_on=1
    w PrestaShop (drugi POST z default_on=1 kończy się HTTP 500 na żywym
    sklepie - patrz komentarz w exporter.py)."""
    databases = {'default', 'MPD'}

    def setUp(self):
        brand = Brands.objects.using('MPD').create(name='Marka')
        product = Products.objects.using('MPD').create(name='Produkt', brand=brand)
        color = Colors.objects.using('MPD').create(
            name='Czerwony', presta_option_value_id=1)
        size = Sizes.objects.using('MPD').create(
            name='M', presta_option_value_id=2)
        self.variant = ProductVariants.objects.using('MPD').create(
            product=product, color=color, size=size)
        self.client = MagicMock()

    def test_default_on_true_sets_flag_to_1(self):
        xml_body = build_combination_xml(
            self.variant, presta_product_id=21, client=self.client, default_on=True)
        self.assertIn(b'<default_on><![CDATA[1]]></default_on>', xml_body)

    def test_default_on_false_by_default(self):
        xml_body = build_combination_xml(
            self.variant, presta_product_id=21, client=self.client)
        self.assertIn(b'<default_on><![CDATA[0]]></default_on>', xml_body)

    def test_raises_without_color_or_size(self):
        bare_variant = ProductVariants.objects.using('MPD').create(
            product=self.variant.product)
        with self.assertRaises(PrestaShopApiError):
            build_combination_xml(bare_variant, 21, self.client)

    def test_push_combination_create_calls_post_and_persists_id(self):
        self.client.create.return_value = _create_response('combination', 96)

        result = push_combination(self.variant, presta_product_id=21,
                                   client=self.client, default_on=True)

        self.assertEqual(result, 96)
        self.client.create.assert_called_once()
        self.variant.refresh_from_db(using='MPD')
        self.assertEqual(self.variant.presta_combination_id, 96)

    def test_push_combination_update_calls_put_when_already_pushed(self):
        self.variant.presta_combination_id = 96
        self.variant.save(using='MPD', update_fields=['presta_combination_id'])

        result = push_combination(self.variant, presta_product_id=21, client=self.client)

        self.assertEqual(result, 96)
        self.client.update.assert_called_once()
        self.client.create.assert_not_called()


class PushStockTest(TestCase):
    databases = {'default', 'MPD', 'zzz_MPD'}

    def setUp(self):
        brand = Brands.objects.using('MPD').create(name='Marka')
        product = Products.objects.using('MPD').create(name='Produkt', brand=brand)
        color = Colors.objects.using('MPD').create(name='Czerwony')
        self.variant = ProductVariants.objects.using('MPD').create(
            product=product, color=color)
        source = Sources.objects.using('MPD').create(
            name='Magazyn', type='Magazyn główny')
        StockAndPrices.objects.using('MPD').create(
            variant=self.variant, source=source, stock=17,
            price=Decimal('10.00'), currency='PLN',
            last_updated='2026-01-01 00:00:00+00:00')

    def test_finds_existing_stock_available_and_updates_quantity(self):
        client = MagicMock()
        client.get.return_value = (
            b'<prestashop><stock_availables>'
            b'<stock_available id="117"/>'
            b'</stock_availables></prestashop>'
        )

        push_stock(
            self.variant, presta_product_id=21, presta_combination_id=96, client=client
        )

        client.update.assert_called_once()
        resource, stock_id, xml_body = client.update.call_args[0]
        self.assertEqual(resource, 'stock_availables')
        self.assertEqual(stock_id, 117)
        self.assertIn(b'<quantity><![CDATA[17]]></quantity>', xml_body)

    def test_raises_when_prestashop_did_not_auto_create_stock_available(self):
        client = MagicMock()
        client.get.return_value = b'<prestashop><stock_availables/></prestashop>'

        with self.assertRaises(PrestaShopApiError):
            push_stock(
                self.variant, presta_product_id=21,
                presta_combination_id=96, client=client,
            )
