"""
MCP server (stdio) udostepniajacy katalog MPD DO ODCZYTU dla klientow MCP
(Claude Desktop/Code). Zero .save()/.create()/.update()/.delete() w tym
pliku - to jedyna warstwa ochrony przed przypadkowa modyfikacja danych przez
narzedzie AI, wiec pilnowac tego przy kazdej zmianie.

Funkcje tools sa zwyklymi funkcjami modulu (nieowiniete w @mcp.tool()) i
rejestrowane recznie w handle() przez mcp.add_tool(fn) - dzieki temu da sie
je testowac bezposrednio (tests_mcp_server.py) bez uruchamiania serwera MCP.

Uzycie (lokalnie, bez Dockera - patrz docs/MCP_SERVER.md):
  .venv/Scripts/python.exe src/manage.py run_mcp_server --settings=core.settings.dev
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from MPD.models import (
    Paths,
    ProductPaths,
    ProductVariants,
    ProductVariantsRetailPrice,
    Products,
    ProductvariantsSources,
    StockAndPrices,
)


def _decimal_str(value):
    return str(value) if isinstance(value, Decimal) else value


def _variant_code(variant: ProductVariants) -> str:
    """Kod producenta/EAN wariantu - ta sama kolejnosc fallbacku co
    apps/prestashop/exporter.py::_variant_reference i
    apps/MPD/export_to_xml.py, zeby odpowiedzi z MCP zgadzaly sie z tym co
    faktycznie idzie do IdoSell/PrestaShop."""
    source = ProductvariantsSources.objects.using(
        'MPD').filter(variant=variant).first()
    if not source:
        return ''
    for field in ('ean', 'gtin14', 'gtin13'):
        value = getattr(source, field, None)
        if value:
            return value
    if getattr(source, 'producer_code', None):
        return source.producer_code
    return source.other or ''


def _variant_dict(variant: ProductVariants) -> dict:
    stock_row = StockAndPrices.objects.using(
        'MPD').filter(variant=variant).first()
    price_row = ProductVariantsRetailPrice.objects.using(
        'MPD').filter(variant=variant).first()
    return {
        'variant_id': variant.variant_id,
        'color': variant.color.name if variant.color else None,
        'size': variant.size.name if variant.size else None,
        'code': _variant_code(variant),
        'stock': stock_row.stock if stock_row else None,
        'retail_price': _decimal_str(price_row.retail_price) if price_row else None,
        'net_price': _decimal_str(price_row.net_price) if price_row else None,
        'currency': price_row.currency if price_row else None,
    }


def search_products(query: str, limit: int = 20) -> list[dict]:
    """Szukaj produktow MPD po nazwie (dopasowanie czesciowe, bez rozroznienia
    wielkosci liter). Zwraca podstawowe informacje - do pelnego szczegolu
    (warianty/ceny/stany) uzyj get_product z product_id ze zwroconej listy."""
    products = Products.objects.using('MPD').filter(
        name__icontains=query).select_related('brand')[:limit]
    return [
        {
            'product_id': p.id,
            'name': p.name,
            'brand': p.brand.name if p.brand else None,
            'visibility': bool(p.visibility),
            'variant_count': ProductVariants.objects.using('MPD').filter(product=p).count(),
        }
        for p in products
    ]


def get_product(product_id: int) -> dict:
    """Pelny szczegol produktu MPD: podstawowe dane, wszystkie warianty
    (kolor/rozmiar/kod/stan/cena) i przypisane kategorie."""
    try:
        product = Products.objects.using('MPD').select_related(
            'brand').get(id=product_id)
    except Products.DoesNotExist:
        return {'error': f'Brak produktu MPD id={product_id}'}

    variants = ProductVariants.objects.using('MPD').filter(
        product=product).select_related('color', 'size')
    categories = [
        pp.path.name for pp in ProductPaths.objects.using('MPD')
        .filter(product=product).select_related('path')
    ]

    return {
        'product_id': product.id,
        'name': product.name,
        'brand': product.brand.name if product.brand else None,
        'description': product.description,
        'short_description': product.short_description,
        'visibility': bool(product.visibility),
        'categories': categories,
        'variants': [_variant_dict(v) for v in variants],
    }


def get_stock_by_ean(ean: str) -> dict:
    """Szybki lookup stanu magazynowego i ceny po kodzie EAN wariantu."""
    source = ProductvariantsSources.objects.using(
        'MPD').filter(ean=ean).select_related('variant__product', 'variant__color', 'variant__size').first()
    if not source:
        return {'error': f'Brak wariantu z EAN={ean}'}

    variant = source.variant
    result = _variant_dict(variant)
    result['product_id'] = variant.product_id
    result['product_name'] = variant.product.name
    return result


def list_categories() -> list[dict]:
    """Wszystkie kategorie (Paths) w MPD, splaszczone - id/name/parent_id.
    Zbuduj drzewo po stronie klienta grupujac po parent_id."""
    return [
        {'id': p.id, 'name': p.name, 'parent_id': p.parent_id}
        for p in Paths.objects.using('MPD').all()
    ]


class Command(BaseCommand):
    help = 'Uruchamia MCP server (stdio, read-only) udostepniajacy katalog MPD.'
    requires_system_checks = []

    def handle(self, *args, **options):
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP(
            'nc-mpd-catalog',
            instructions=(
                'Katalog produktow MPD (nc_project) - TYLKO ODCZYT. '
                'Uzyj search_products zeby znalezc produkt po nazwie, '
                'get_product po ID dla pelnego szczegolu (warianty/ceny/stany), '
                'get_stock_by_ean do szybkiego sprawdzenia po kodzie kreskowym, '
                'list_categories do zobaczenia drzewa kategorii.'
            ),
        )
        mcp.add_tool(search_products)
        mcp.add_tool(get_product)
        mcp.add_tool(get_stock_by_ean)
        mcp.add_tool(list_categories)

        mcp.run(transport='stdio')
