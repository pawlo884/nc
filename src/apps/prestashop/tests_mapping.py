"""
Testy mapping.py (ensure_category/ensure_color_value/ensure_size_value).
Klient PrestaShop jest mockowany - żadne testy tutaj nie robią realnych
wywołań HTTP (na odróżnienie od test_prestashop_connection, które jest
narzędziem manualnym do sprawdzania żywego sklepu).
"""
from unittest.mock import MagicMock

from django.test import TestCase

from MPD.models import Colors, Paths, Sizes

from .api_client import PrestaShopApiError
from .mapping import ensure_category, ensure_color_value, ensure_size_value


def _create_response(root_tag: str, new_id: int) -> bytes:
    return f'<prestashop><{root_tag}><id>{new_id}</id></{root_tag}></prestashop>'.encode()


class EnsureColorValueTest(TestCase):
    databases = {'default', 'MPD'}

    def test_returns_existing_id_without_calling_api(self):
        color = Colors.objects.using('MPD').create(
            name='Czerwony', presta_option_value_id=42)
        client = MagicMock()

        result = ensure_color_value(color, client)

        self.assertEqual(result, 42)
        client.create.assert_not_called()

    def test_creates_and_persists_id_when_missing(self):
        color = Colors.objects.using('MPD').create(
            name='Niebieski', hex_code='#0000FF')
        client = MagicMock()
        client.create.return_value = _create_response('product_option_value', 99)

        result = ensure_color_value(color, client)

        self.assertEqual(result, 99)
        color.refresh_from_db(using='MPD')
        self.assertEqual(color.presta_option_value_id, 99)
        client.create.assert_called_once()
        resource, xml_body = client.create.call_args[0]
        self.assertEqual(resource, 'product_option_values')
        self.assertIn(b'Niebieski', xml_body)
        self.assertIn(b'#0000FF', xml_body)

    def test_dry_run_does_not_call_api_or_persist(self):
        color = Colors.objects.using('MPD').create(name='Zielony')
        client = MagicMock()

        result = ensure_color_value(color, client, dry_run=True)

        self.assertIsNone(result)
        client.create.assert_not_called()
        color.refresh_from_db(using='MPD')
        self.assertIsNone(color.presta_option_value_id)


class EnsureSizeValueTest(TestCase):
    databases = {'default', 'MPD'}

    def test_returns_existing_id_without_calling_api(self):
        size = Sizes.objects.using('MPD').create(
            name='M', presta_option_value_id=7)
        client = MagicMock()

        result = ensure_size_value(size, client)

        self.assertEqual(result, 7)
        client.create.assert_not_called()

    def test_creates_and_persists_id_when_missing(self):
        size = Sizes.objects.using('MPD').create(name='XL')
        client = MagicMock()
        client.create.return_value = _create_response('product_option_value', 55)

        result = ensure_size_value(size, client)

        self.assertEqual(result, 55)
        size.refresh_from_db(using='MPD')
        self.assertEqual(size.presta_option_value_id, 55)

    def test_dry_run_does_not_call_api_or_persist(self):
        size = Sizes.objects.using('MPD').create(name='S')
        client = MagicMock()

        result = ensure_size_value(size, client, dry_run=True)

        self.assertIsNone(result)
        client.create.assert_not_called()


class EnsureCategoryTest(TestCase):
    databases = {'default', 'MPD'}

    def test_returns_existing_id_without_calling_api(self):
        path = Paths.objects.using('MPD').create(
            name='Sukienki', presta_category_id=13)
        client = MagicMock()

        result = ensure_category(path, client)

        self.assertEqual(result, 13)
        client.create.assert_not_called()

    def test_creates_without_parent_under_shop_root(self):
        path = Paths.objects.using('MPD').create(name='Bielizna')
        client = MagicMock()
        client.create.return_value = _create_response('category', 20)

        result = ensure_category(path, client)

        self.assertEqual(result, 20)
        resource, xml_body = client.create.call_args[0]
        self.assertEqual(resource, 'categories')
        self.assertIn(b'<id_parent><![CDATA[2]]></id_parent>', xml_body)

    def test_creates_parent_recursively_when_missing(self):
        parent = Paths.objects.using('MPD').create(name='Bielizna')
        child = Paths.objects.using('MPD').create(
            name='Biustonosze', parent_id=parent.id)
        client = MagicMock()
        # Pierwsze wywołanie tworzy rodzica (id=20), drugie dziecko (id=21)
        client.create.side_effect = [
            _create_response('category', 20),
            _create_response('category', 21),
        ]

        result = ensure_category(child, client)

        self.assertEqual(result, 21)
        self.assertEqual(client.create.call_count, 2)
        parent.refresh_from_db(using='MPD')
        self.assertEqual(parent.presta_category_id, 20)
        # Drugie wywołanie (dziecko) powinno wskazywać na świeżo utworzonego rodzica
        _, child_xml = client.create.call_args_list[1][0]
        self.assertIn(b'<id_parent><![CDATA[20]]></id_parent>', child_xml)

    def test_dry_run_does_not_call_api_even_recursively(self):
        parent = Paths.objects.using('MPD').create(name='Bielizna')
        child = Paths.objects.using('MPD').create(
            name='Biustonosze', parent_id=parent.id)
        client = MagicMock()

        result = ensure_category(child, client, dry_run=True)

        self.assertIsNone(result)
        client.create.assert_not_called()

    def test_api_error_does_not_persist_id(self):
        path = Paths.objects.using('MPD').create(name='Buty')
        client = MagicMock()
        client.create.side_effect = PrestaShopApiError('boom')

        with self.assertRaises(PrestaShopApiError):
            ensure_category(path, client)

        path.refresh_from_db(using='MPD')
        self.assertIsNone(path.presta_category_id)
