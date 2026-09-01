"""
Testy funkcji-tools MCP server (run_mcp_server.py). Testujemy funkcje
bezpośrednio (nie owinięte w @mcp.tool()) - bez uruchamiania serwera MCP.
"""
from decimal import Decimal

from django.test import TestCase

from .management.commands.run_mcp_server import (
    _add_sync_tool,
    get_product,
    get_stock_by_ean,
    list_categories,
    search_products,
)
from .models import (
    Brands,
    Colors,
    Paths,
    ProductPaths,
    ProductVariants,
    ProductVariantsRetailPrice,
    Products,
    ProductvariantsSources,
    Sizes,
    Sources,
    StockAndPrices,
)


class SearchProductsTest(TestCase):
    databases = {'default', 'MPD'}

    def setUp(self):
        brand = Brands.objects.using('MPD').create(name='Marko')
        self.product = Products.objects.using('MPD').create(
            name='Kostium kąpielowy Ellen', brand=brand, visibility=True)
        ProductVariants.objects.using('MPD').create(product=self.product)
        ProductVariants.objects.using('MPD').create(product=self.product)

    def test_finds_by_partial_case_insensitive_name(self):
        results = search_products('ellen')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['product_id'], self.product.id)
        self.assertEqual(results[0]['brand'], 'Marko')
        self.assertEqual(results[0]['variant_count'], 2)

    def test_no_match_returns_empty_list(self):
        self.assertEqual(search_products('nieistniejacyprodukt'), [])

    def test_respects_limit(self):
        for i in range(5):
            Products.objects.using('MPD').create(name=f'Kostium test {i}')
        self.assertEqual(len(search_products('kostium', limit=2)), 2)


class GetProductTest(TestCase):
    databases = {'default', 'MPD', 'zzz_MPD'}

    def setUp(self):
        brand = Brands.objects.using('MPD').create(name='Marko')
        self.product = Products.objects.using('MPD').create(
            name='Figi Cobalt', brand=brand, description='Opis',
            short_description='Krótki opis')
        color = Colors.objects.using('MPD').create(name='Kobalt')
        size = Sizes.objects.using('MPD').create(name='M')
        self.variant = ProductVariants.objects.using('MPD').create(
            product=self.product, color=color, size=size)
        ProductvariantsSources.objects.using('MPD').create(
            variant=self.variant, ean='5900000000001')
        ProductVariantsRetailPrice.objects.using('MPD').create(
            variant=self.variant, retail_price=Decimal('99.99'),
            net_price=Decimal('81.29'), currency='PLN')
        source = Sources.objects.using('MPD').create(
            name='Magazyn', type='Magazyn główny')
        StockAndPrices.objects.using('MPD').create(
            variant=self.variant, source=source, stock=12,
            price=Decimal('81.29'), currency='PLN',
            last_updated='2026-01-01 00:00:00+00:00')
        path = Paths.objects.using('MPD').create(name='Figi')
        ProductPaths.objects.using('MPD').create(
            product=self.product, path=path)

    def test_returns_full_detail(self):
        detail = get_product(self.product.id)
        self.assertEqual(detail['name'], 'Figi Cobalt')
        self.assertEqual(detail['brand'], 'Marko')
        self.assertEqual(detail['categories'], ['Figi'])
        self.assertEqual(len(detail['variants']), 1)
        variant = detail['variants'][0]
        self.assertEqual(variant['color'], 'Kobalt')
        self.assertEqual(variant['size'], 'M')
        self.assertEqual(variant['code'], '5900000000001')
        self.assertEqual(variant['stock'], 12)
        self.assertEqual(variant['net_price'], '81.29')

    def test_missing_product_returns_error_dict(self):
        result = get_product(999999999)
        self.assertIn('error', result)


class GetStockByEanTest(TestCase):
    databases = {'default', 'MPD', 'zzz_MPD'}

    def setUp(self):
        self.product = Products.objects.using('MPD').create(name='Produkt')
        self.variant = ProductVariants.objects.using('MPD').create(
            product=self.product)
        ProductvariantsSources.objects.using('MPD').create(
            variant=self.variant, ean='1112223334445')
        source = Sources.objects.using('MPD').create(
            name='Magazyn', type='Magazyn główny')
        StockAndPrices.objects.using('MPD').create(
            variant=self.variant, source=source, stock=7,
            price=Decimal('10.00'), currency='PLN',
            last_updated='2026-01-01 00:00:00+00:00')

    def test_finds_by_ean(self):
        result = get_stock_by_ean('1112223334445')
        self.assertEqual(result['stock'], 7)
        self.assertEqual(result['product_id'], self.product.id)

    def test_unknown_ean_returns_error_dict(self):
        result = get_stock_by_ean('0000000000000')
        self.assertIn('error', result)


class ListCategoriesTest(TestCase):
    databases = {'default', 'MPD'}

    def test_returns_flat_list_with_parent_id(self):
        parent = Paths.objects.using('MPD').create(name='Bielizna')
        Paths.objects.using('MPD').create(
            name='Biustonosze', parent_id=parent.id)

        categories = list_categories()

        names = {c['name']: c for c in categories}
        self.assertIsNone(names['Bielizna']['parent_id'])
        self.assertEqual(names['Biustonosze']['parent_id'], parent.id)


class AddSyncToolTest(TestCase):
    """FastMCP wola narzedzia wprost w petli asyncio - synchroniczne funkcje
    uzywajace Django ORM (jak search_products/get_product) rzucaja tam
    SynchronousOnlyOperation, jesli nie sa owiniete w sync_to_async.
    _add_sync_tool to naprawia; te testy pilnuja zeby nie zniknelo przy
    kolejnej zmianie."""
    databases = {'default', 'MPD'}

    def setUp(self):
        Products.objects.using('MPD').create(name='Testowy Produkt MCP')

    async def test_wrapped_tool_is_awaitable_and_returns_same_result(self):
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('test-server')
        _add_sync_tool(mcp, search_products)

        tool = mcp._tool_manager.get_tool('search_products')
        result = await tool.fn('Testowy')

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'Testowy Produkt MCP')

    def test_wrapper_preserves_name_and_signature(self):
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('test-server')
        _add_sync_tool(mcp, get_stock_by_ean)

        tool = mcp._tool_manager._tools['get_stock_by_ean']
        self.assertEqual(tool.name, 'get_stock_by_ean')
        self.assertIn('ean', tool.parameters['properties'])
