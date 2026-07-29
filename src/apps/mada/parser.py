"""
Parser products.xml z feedu Mada.

Plik pełny waży ~24 MB, dlatego produkty parsujemy strumieniowo (iterparse)
zamiast wczytywać cały dokument do DOM naraz - element <PRODUCT> jest
czyszczony (`elem.clear()`) zaraz po przetworzeniu.
"""
import io
import logging
from typing import Dict, Iterator, Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


def _text(el, tag: str) -> str:
    child = el.find(tag)
    if child is None or child.text is None:
        return ''
    return child.text.strip()


def parse_producers(xml_bytes: bytes) -> Dict[str, str]:
    """Słownik producer_id -> nazwa z sekcji <PRODUCERS> (pojedynczy blok na
    początku pliku, poprzedzający wszystkie <PRODUCT>)."""
    producers: Dict[str, str] = {}
    stream = io.BytesIO(xml_bytes)
    for _, elem in ET.iterparse(stream, events=('end',)):
        if elem.tag == 'PRODUCERS':
            for prod_el in elem.findall('PRODUCER'):
                producer_id = prod_el.get('id')
                if producer_id:
                    producers[producer_id] = (prod_el.text or '').strip()
            elem.clear()
            break  # blok występuje raz przed PRODUCTS - dalej nie ma sensu skanować
    return producers


def parse_product_element(product_el) -> Dict:
    """Zamienia element <PRODUCT> na dict gotowy do zapisu w bazie."""
    api_id_raw = _text(product_el, 'ID')

    producer_el = product_el.find('PRODUCER')
    producer_id = (producer_el.text or '').strip() if producer_el is not None and producer_el.text else None

    categories = []
    for cat_el in product_el.findall('./CATEGORIES/CATEGORY'):
        categories.append({
            'c1': cat_el.get('c1'),
            'c2': cat_el.get('c2'),
            'name': (cat_el.text or '').strip(),
        })

    similar_products = [
        (s.text or '').strip()
        for s in product_el.findall('./SIMILAR_PRODUCTS/SIMILAR')
        if s.text
    ]

    variants = []
    for model_el in product_el.findall('./MODELS/MODEL'):
        color = _text(model_el, 'COLOR')
        for size_el in model_el.findall('SIZE'):
            ean = (size_el.get('ean') or '').strip()
            try:
                stock = int(size_el.get('amount') or 0)
            except ValueError:
                stock = 0
            size_label = (size_el.text or '').strip()
            variants.append({
                'color': color,
                'size': size_label,
                'ean': ean,
                'stock': stock,
                'variant_key': ean or f'{color}|{size_label}',
            })

    attributes = [
        {
            'id': attr_el.get('id'),
            'group_id': attr_el.get('group_id'),
            'value': (attr_el.text or '').strip(),
        }
        for attr_el in product_el.findall('./ATTRIBUTES/ATTRIBUTE')
    ]

    images = []
    for idx, img_el in enumerate(product_el.findall('./IMAGES/IMG')):
        url = (img_el.text or '').strip()
        if not url:
            continue
        images.append({
            'api_image_id': img_el.get('id') or str(idx),
            'url': url,
            'order': idx,
        })

    return {
        'api_id': int(api_id_raw) if api_id_raw.isdigit() else None,
        'name': _text(product_el, 'NAME'),
        'desc': _text(product_el, 'DESC'),
        'producer_id': producer_id,
        'price': _text(product_el, 'PRICE') or None,
        'old_price': _text(product_el, 'OLD_PRICE') or None,
        'vat': _text(product_el, 'VAT') or None,
        'categories': categories,
        'variants': variants,
        'images': images,
        'raw_data': {
            'producer_address': _text(product_el, 'PRODUCER_ADDRESS'),
            'producer_security_info': _text(product_el, 'PRODUCER_SECURITY_INFO'),
            'similar_products': similar_products,
            'attributes': attributes,
        },
    }


def iter_products(xml_bytes: bytes) -> Iterator[Dict]:
    """Generator: parsuje products.xml strumieniowo, zwalniając pamięć po każdym <PRODUCT>."""
    stream = io.BytesIO(xml_bytes)
    for _, elem in ET.iterparse(stream, events=('end',)):
        if elem.tag != 'PRODUCT':
            continue
        try:
            parsed = parse_product_element(elem)
        except Exception:
            logger.exception('Nie udało się sparsować elementu PRODUCT, pomijam.')
            elem.clear()
            continue
        elem.clear()
        if parsed['api_id'] is not None:
            yield parsed
