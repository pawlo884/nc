"""
Budowanie i push produktów MPD do PrestaShop WebAPI.

Kolejność (twardy wymóg PrestaShop - obiekty muszą istnieć zanim się do nich
odwołasz): kategoria + kolory/rozmiary (mapping.py) -> produkt -> combinations
(po jednej na wariant) -> stock_available (ilość).

Ceny/kod producenta: te same reguły co apps/MPD/export_to_xml.py
(FullXMLExporter.generate_xml) - pierwsza cena z pierwszego wariantu,
code_producer w kolejności ean -> gtin14 -> gtin13 -> producer_code -> other.
"""
import logging
from xml.etree import ElementTree as ET

from django.utils.text import slugify

from MPD.models import (
    ProductPaths,
    ProductVariants,
    ProductVariantsRetailPrice,
    Products,
    ProductvariantsSources,
    StockAndPrices,
)

from .api_client import PrestaShopApiClient, PrestaShopApiError
from .mapping import ensure_category, ensure_color_value, ensure_size_value

logger = logging.getLogger(__name__)


def _variant_reference(variant: ProductVariants) -> str:
    """Kod producenta/EAN wariantu - fallback ean->gtin14->gtin13->producer_code->other,
    identycznie jak w export_to_xml.py (żeby oba kanały zgadzały się w SKU)."""
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


def _extract_id(xml_bytes: bytes, root_tag: str) -> int:
    root = ET.fromstring(xml_bytes)
    el = root.find(f'.//{root_tag}/id')
    if el is None or not el.text:
        raise PrestaShopApiError(
            f'Odpowiedź PrestaShop nie zawiera <{root_tag}><id>.')
    return int(el.text.strip())


def build_product_xml(
    product: Products, client: PrestaShopApiClient, dry_run: bool = False
) -> bytes:
    """Buduje XML produktu. Kategorie (i domyślna, i wszystkie przypisane)
    są zapewniane (ensure_category) PRZED zbudowaniem XML - PrestaShop
    odrzuci id_category_default, którego jeszcze nie ma. dry_run=True:
    ensure_category nic nie tworzy - kategorie jeszcze bez mapowania trafiają
    do podglądu jako placeholder "NOWA:<nazwa>", nie realny ID."""
    product_paths = list(ProductPaths.objects.using(
        'MPD').filter(product=product).select_related('path'))
    if not product_paths:
        raise PrestaShopApiError(
            f'Produkt MPD id={product.id} nie ma przypisanej żadnej ścieżki (Paths) - '
            f'PrestaShop wymaga id_category_default.'
        )
    category_ids = [
        ensure_category(pp.path, client, dry_run=dry_run) for pp in product_paths
    ]

    def _display(cid, path):
        return str(cid) if cid is not None else f'NOWA:{path.name}'

    id_category_default_display = _display(category_ids[0], product_paths[0].path)

    first_variant = ProductVariants.objects.using(
        'MPD').filter(product=product).first()
    price = ''
    if first_variant:
        retail = ProductVariantsRetailPrice.objects.using(
            'MPD').filter(variant=first_variant).first()
        if retail and retail.net_price is not None:
            price = str(retail.net_price)

    name = product.name or f'Produkt {product.id}'
    link_rewrite = slugify(name) or f'produkt-{product.id}'
    active = '1' if product.visibility else '0'
    description = product.description or ''
    description_short = product.short_description or ''

    categories_xml = ''.join(
        f'<category><id><![CDATA[{_display(cid, pp.path)}]]></id></category>'
        for cid, pp in zip(category_ids, product_paths)
    )
    # PrestaShop wymaga <id> w body przy PUT (update); przy POST (create) id
    # nie istnieje jeszcze i sam je nadaje - nie wolno go wtedy wysyłać.
    id_tag = (f'<id><![CDATA[{product.presta_product_id}]]></id>'
              if product.presta_product_id else '')

    return f'''<prestashop xmlns:xlink="http://www.w3.org/1999/xlink">
  <product>
    {id_tag}
    <id_category_default><![CDATA[{id_category_default_display}]]></id_category_default>
    <active><![CDATA[{active}]]></active>
    <price><![CDATA[{price or '0'}]]></price>
    <reference><![CDATA[{_variant_reference(first_variant) if first_variant else ''}]]></reference>
    <name>
      <language id="1"><![CDATA[{name}]]></language>
    </name>
    <link_rewrite>
      <language id="1"><![CDATA[{link_rewrite}]]></language>
    </link_rewrite>
    <description>
      <language id="1"><![CDATA[{description}]]></language>
    </description>
    <description_short>
      <language id="1"><![CDATA[{description_short}]]></language>
    </description_short>
    <associations>
      <categories>
        {categories_xml}
      </categories>
    </associations>
  </product>
</prestashop>'''.encode('utf-8')


def push_product(product: Products, client: PrestaShopApiClient = None) -> int:
    """Tworzy (POST) lub aktualizuje (PUT, gdy presta_product_id już ustawione)
    produkt w PrestaShop. Zwraca presta_product_id."""
    client = client or PrestaShopApiClient()
    xml_body = build_product_xml(product, client)

    if product.presta_product_id:
        client.update('products', product.presta_product_id, xml_body)
        logger.info('Zaktualizowano produkt PrestaShop %s (MPD id=%s)',
                    product.presta_product_id, product.id)
        return product.presta_product_id

    response = client.create('products', xml_body)
    new_id = _extract_id(response, 'product')
    product.presta_product_id = new_id
    product.save(using='MPD', update_fields=['presta_product_id'])
    logger.info('Utworzono produkt PrestaShop %s (MPD id=%s)',
                new_id, product.id)
    return new_id


def build_combination_xml(
    variant: ProductVariants, presta_product_id: int, client: PrestaShopApiClient,
    dry_run: bool = False, default_on: bool = False,
) -> bytes:
    """Buduje XML combination. Kolor/rozmiar są zapewniane (ensure_*) przed
    budową - combination odwołuje się do ich ID przez associations. dry_run=True:
    ensure_* nic nie tworzy, wartości bez mapowania trafiają do podglądu jako
    placeholder "NOWA:<nazwa>", nie realny ID."""
    values = []  # [(display_value, real_id_or_None)]
    if variant.color_id:
        cid = ensure_color_value(variant.color, client, dry_run=dry_run)
        values.append(cid if cid is not None else f'NOWA:{variant.color.name}')
    if variant.size_id:
        sid = ensure_size_value(variant.size, client, dry_run=dry_run)
        values.append(sid if sid is not None else f'NOWA:{variant.size.name}')
    if not values:
        raise PrestaShopApiError(
            f'Wariant MPD id={variant.variant_id} nie ma ani koloru, ani rozmiaru - '
            f'PrestaShop wymaga co najmniej jednej wartości atrybutu w combination.'
        )
    # Cena produktu (build_product_xml) to cena pierwszego wariantu - dla
    # pozostałych wariantów combination.price to RÓŻNICA względem tej ceny
    # bazowej ("price impact"), nie cena bezwzględna. MVP: 0 dla wszystkich
    # (każdy wariant kosztuje tyle co produkt bazowy) - realne różnicowanie
    # cen między wariantami to Faza 2.
    price_impact = '0'

    values_xml = ''.join(
        f'<product_option_value><id><![CDATA[{v}]]></id></product_option_value>'
        for v in values
    )
    # Jak w build_product_xml: <id> wymagane przy PUT, zabronione przy POST.
    id_tag = (f'<id><![CDATA[{variant.presta_combination_id}]]></id>'
              if variant.presta_combination_id else '')

    return f'''<prestashop xmlns:xlink="http://www.w3.org/1999/xlink">
  <combination>
    {id_tag}
    <id_product><![CDATA[{presta_product_id}]]></id_product>
    <reference><![CDATA[{_variant_reference(variant)}]]></reference>
    <price><![CDATA[{price_impact}]]></price>
    <minimal_quantity><![CDATA[1]]></minimal_quantity>
    <default_on><![CDATA[{1 if default_on else 0}]]></default_on>
    <associations>
      <product_option_values>
        {values_xml}
      </product_option_values>
    </associations>
  </combination>
</prestashop>'''.encode('utf-8')


def push_combination(
    variant: ProductVariants, presta_product_id: int, client: PrestaShopApiClient = None,
    default_on: bool = False,
) -> int:
    """Tworzy (POST) lub aktualizuje (PUT) combination. Zwraca presta_combination_id.
    default_on: dokładnie JEDEN combination per produkt może mieć default_on=1
    w PrestaShop - kolejne POST-y z default_on=1 dla tego samego produktu
    kończą się HTTP 500."""
    client = client or PrestaShopApiClient()
    xml_body = build_combination_xml(
        variant, presta_product_id, client, default_on=default_on)

    if variant.presta_combination_id:
        client.update('combinations', variant.presta_combination_id, xml_body)
        logger.info('Zaktualizowano combination PrestaShop %s (MPD variant_id=%s)',
                    variant.presta_combination_id, variant.variant_id)
        return variant.presta_combination_id

    response = client.create('combinations', xml_body)
    new_id = _extract_id(response, 'combination')
    variant.presta_combination_id = new_id
    variant.save(using='MPD', update_fields=['presta_combination_id'])
    logger.info('Utworzono combination PrestaShop %s (MPD variant_id=%s)',
                new_id, variant.variant_id)
    return new_id


def push_stock(variant: ProductVariants, presta_product_id: int,
               presta_combination_id: int, client: PrestaShopApiClient = None) -> None:
    """Ustawia stan magazynowy combination. PrestaShop tworzy stock_available
    automatycznie przy tworzeniu combination - trzeba go znaleźć (GET po
    id_product+id_product_attribute), nie tworzyć od nowa (POST by go zduplikował)."""
    client = client or PrestaShopApiClient()

    stock_row = StockAndPrices.objects.using(
        'MPD').filter(variant=variant).first()
    quantity = stock_row.stock if stock_row else 0

    raw = client.get('stock_availables', params={
        'filter[id_product]': presta_product_id,
        'filter[id_product_attribute]': presta_combination_id,
    })
    root = ET.fromstring(raw)
    ids = [el.get('id') for el in root.findall('.//stock_available')]
    if not ids:
        raise PrestaShopApiError(
            f'Brak stock_available dla product={presta_product_id}, '
            f'combination={presta_combination_id} - PrestaShop powinien go '
            f'utworzyć automatycznie przy tworzeniu combination.'
        )
    stock_available_id = int(ids[0])

    xml_body = f'''<prestashop xmlns:xlink="http://www.w3.org/1999/xlink">
  <stock_available>
    <id><![CDATA[{stock_available_id}]]></id>
    <id_product><![CDATA[{presta_product_id}]]></id_product>
    <id_product_attribute><![CDATA[{presta_combination_id}]]></id_product_attribute>
    <quantity><![CDATA[{quantity}]]></quantity>
    <depends_on_stock><![CDATA[0]]></depends_on_stock>
    <out_of_stock><![CDATA[2]]></out_of_stock>
  </stock_available>
</prestashop>'''.encode('utf-8')
    client.update('stock_availables', stock_available_id, xml_body)
    logger.info('Ustawiono stan %s dla combination %s (product %s)',
                quantity, presta_combination_id, presta_product_id)
