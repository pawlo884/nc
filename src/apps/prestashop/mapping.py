"""
"Ensure exists" logika: kategorie/kolory/rozmiary MUSZĄ istnieć w PrestaShop
PRZED wysłaniem produktu/combination, które się do nich odwołują (WebAPI nie
tworzy ich automatycznie "przy okazji" - inaczej niż np. przy tworzeniu
wariantów w matterhorn1/tabu podczas importu).

Idempotentne: jeśli obiekt MPD ma już zapisane presta_*_id, tylko go zwraca
(bez ponownego POST-a). W przeciwnym razie tworzy w PrestaShop i zapisuje ID
na modelu MPD - ten sam wzorzec co iai_colors_id/iai_size_id/iai_category_id
dla IdoSell (apps/MPD/export_to_xml.py).
"""
import logging

from django.utils.text import slugify

from MPD.models import Colors, Paths, Sizes

from .api_client import PrestaShopApiClient, PrestaShopApiError

logger = logging.getLogger(__name__)

# id_attribute_group w PrestaShop dla tego sklepu (shop.sowa.ch) - potwierdzone
# na żywo: 1 = "Rozmiar", 2 = "Kolor". Nie odkrywamy tego dynamicznie po nazwie,
# żeby uniknąć przypadkowego utworzenia drugiej grupy o tej samej nazwie, gdyby
# ktoś w międzyczasie zmienił nazwę w PrestaShop.
SIZE_ATTRIBUTE_GROUP_ID = 1
COLOR_ATTRIBUTE_GROUP_ID = 2

# id_category shopu (PrestaShop "shops" -> id_category=2 dla shop.sowa.ch,
# id_shop=1) - root, pod który wieszamy kategorie MPD bez rodzica.
SHOP_ROOT_CATEGORY_ID = 2


def _option_value_xml(id_attribute_group: int, name: str, color_hex: str = '') -> bytes:
    color_tag = f'<color><![CDATA[{color_hex}]]></color>' if color_hex else '<color></color>'
    return f'''<prestashop xmlns:xlink="http://www.w3.org/1999/xlink">
  <product_option_value>
    <id_attribute_group><![CDATA[{id_attribute_group}]]></id_attribute_group>
    {color_tag}
    <name>
      <language id="1"><![CDATA[{name}]]></language>
    </name>
  </product_option_value>
</prestashop>'''.encode('utf-8')


def _extract_id(xml_bytes: bytes, root_tag: str) -> int:
    from xml.etree import ElementTree as ET
    root = ET.fromstring(xml_bytes)
    el = root.find(f'.//{root_tag}/id')
    if el is None or not el.text:
        raise PrestaShopApiError(
            f'Odpowiedź PrestaShop nie zawiera <{root_tag}><id> - nie mogę odczytać utworzonego ID.')
    return int(el.text.strip())


def ensure_color_value(
    color: Colors, client: PrestaShopApiClient = None, dry_run: bool = False
) -> int:
    """Zwraca presta_option_value_id dla koloru MPD, tworząc go w grupie
    "Kolor" jeśli jeszcze nie istnieje. dry_run=True: zwraca None zamiast
    tworzyć cokolwiek w PrestaShop, gdy jeszcze nie ma mapowania."""
    if color.presta_option_value_id:
        return color.presta_option_value_id
    if dry_run:
        return None

    client = client or PrestaShopApiClient()
    xml_body = _option_value_xml(
        COLOR_ATTRIBUTE_GROUP_ID, color.name or f'Kolor {color.id}',
        color.hex_code or '')
    response = client.create('product_option_values', xml_body)
    new_id = _extract_id(response, 'product_option_value')

    color.presta_option_value_id = new_id
    color.save(using='MPD', update_fields=['presta_option_value_id'])
    logger.info('Utworzono product_option_value %s dla koloru "%s" (MPD id=%s)',
                new_id, color.name, color.id)
    return new_id


def ensure_size_value(
    size: Sizes, client: PrestaShopApiClient = None, dry_run: bool = False
) -> int:
    """Zwraca presta_option_value_id dla rozmiaru MPD, tworząc go w grupie
    "Rozmiar" jeśli jeszcze nie istnieje. dry_run=True: zwraca None zamiast
    tworzyć cokolwiek w PrestaShop, gdy jeszcze nie ma mapowania."""
    if size.presta_option_value_id:
        return size.presta_option_value_id
    if dry_run:
        return None

    client = client or PrestaShopApiClient()
    xml_body = _option_value_xml(
        SIZE_ATTRIBUTE_GROUP_ID, size.name or f'Rozmiar {size.id}')
    response = client.create('product_option_values', xml_body)
    new_id = _extract_id(response, 'product_option_value')

    size.presta_option_value_id = new_id
    size.save(using='MPD', update_fields=['presta_option_value_id'])
    logger.info('Utworzono product_option_value %s dla rozmiaru "%s" (MPD id=%s)',
                new_id, size.name, size.id)
    return new_id


def ensure_category(
    path: Paths, client: PrestaShopApiClient = None, dry_run: bool = False
) -> int:
    """Zwraca presta_category_id dla ścieżki MPD, tworząc ją (i rekurencyjnie
    jej rodzica) w PrestaShop jeśli jeszcze nie istnieje. Kategorie bez
    rodzica w MPD (parent_id=NULL) wieszamy pod korzeniem sklepu. dry_run=True:
    zwraca None zamiast tworzyć cokolwiek (także rekurencyjnie dla rodziców),
    gdy jeszcze nie ma mapowania."""
    if path.presta_category_id:
        return path.presta_category_id
    if dry_run:
        return None

    client = client or PrestaShopApiClient()

    if path.parent_id:
        try:
            parent = Paths.objects.using('MPD').get(id=path.parent_id)
        except Paths.DoesNotExist:
            id_parent = SHOP_ROOT_CATEGORY_ID
        else:
            id_parent = ensure_category(parent, client)
    else:
        id_parent = SHOP_ROOT_CATEGORY_ID

    name = path.name or f'Kategoria {path.id}'
    link_rewrite = slugify(name) or f'kategoria-{path.id}'
    xml_body = f'''<prestashop xmlns:xlink="http://www.w3.org/1999/xlink">
  <category>
    <id_parent><![CDATA[{id_parent}]]></id_parent>
    <active><![CDATA[1]]></active>
    <name>
      <language id="1"><![CDATA[{name}]]></language>
    </name>
    <link_rewrite>
      <language id="1"><![CDATA[{link_rewrite}]]></language>
    </link_rewrite>
  </category>
</prestashop>'''.encode('utf-8')
    response = client.create('categories', xml_body)
    new_id = _extract_id(response, 'category')

    path.presta_category_id = new_id
    path.save(using='MPD', update_fields=['presta_category_id'])
    logger.info('Utworzono category %s dla ścieżki "%s" (MPD id=%s)',
                new_id, path.name, path.id)
    return new_id
