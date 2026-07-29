"""
Testy parsera products.xml (feed Mada) - na przykładowym fragmencie XML
odzwierciedlającym realną strukturę feedu (bez pobierania z API).
"""
from django.test import SimpleTestCase

from mada.parser import iter_products, parse_producers

SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<DATA>
  <FLAGS>
    <FLAG id="1">Recommended</FLAG>
  </FLAGS>
  <PRODUCERS>
    <PRODUCER id="110"><![CDATA[Gatta]]></PRODUCER>
    <PRODUCER id="43"><![CDATA[Golden Lady]]></PRODUCER>
  </PRODUCERS>
  <PRODUCTS>
    <PRODUCT>
      <ID>161</ID>
      <NAME><![CDATA[Rajstopy Gatta Estella 15 den 2-4]]></NAME>
      <DESC><![CDATA[Rajstopy damskie 15 den]]></DESC>
      <PRODUCER>110</PRODUCER>
      <PRODUCER_ADDRESS>Ferax sp. z o.o.</PRODUCER_ADDRESS>
      <PRODUCER_SECURITY_INFO>Info bezpieczenstwa</PRODUCER_SECURITY_INFO>
      <PRICE>12.04</PRICE>
      <VAT>23</VAT>
      <CATEGORIES>
        <CATEGORY c1="30" c2="63"><![CDATA[Rajstopy / lycra]]></CATEGORY>
      </CATEGORIES>
      <SIMILAR_PRODUCTS>
        <SIMILAR>63194</SIMILAR>
      </SIMILAR_PRODUCTS>
      <MODELS>
        <MODEL>
          <COLOR><![CDATA[nero/czarny]]></COLOR>
          <SIZE amount="43" ean="000223000290">2-S</SIZE>
          <SIZE amount="130" ean="000223000490">4-L</SIZE>
        </MODEL>
        <MODEL>
          <COLOR><![CDATA[bez EAN]]></COLOR>
          <SIZE amount="5">uniwersalny</SIZE>
        </MODEL>
      </MODELS>
      <ATTRIBUTES>
        <ATTRIBUTE id="1" group_id="1"><![CDATA[15 den]]></ATTRIBUTE>
      </ATTRIBUTES>
      <IMAGES>
        <IMG id="305045">https://www.mada.pl/img/product-n/161/1800/305045.jpg</IMG>
      </IMAGES>
    </PRODUCT>
    <PRODUCT>
      <ID>162</ID>
      <NAME><![CDATA[Produkt bez wariantow]]></NAME>
      <DESC><![CDATA[Opis]]></DESC>
      <PRODUCER>43</PRODUCER>
      <PRICE>9.99</PRICE>
      <OLD_PRICE>14.99</OLD_PRICE>
      <VAT>23</VAT>
      <CATEGORIES>
        <CATEGORY c1="30" c2="64"><![CDATA[Rajstopy / mikrofibra]]></CATEGORY>
      </CATEGORIES>
      <MODELS></MODELS>
      <IMAGES></IMAGES>
    </PRODUCT>
  </PRODUCTS>
</DATA>
""".encode('utf-8')


class ParseProducersTest(SimpleTestCase):
    def test_parses_producer_dict(self):
        producers = parse_producers(SAMPLE_XML)
        self.assertEqual(producers, {'110': 'Gatta', '43': 'Golden Lady'})


class IterProductsTest(SimpleTestCase):
    def test_parses_all_products(self):
        products = list(iter_products(SAMPLE_XML))
        self.assertEqual(len(products), 2)

    def test_parses_product_fields(self):
        products = {p['api_id']: p for p in iter_products(SAMPLE_XML)}
        p = products[161]
        self.assertEqual(p['name'], 'Rajstopy Gatta Estella 15 den 2-4')
        self.assertEqual(p['producer_id'], '110')
        self.assertEqual(p['price'], '12.04')
        self.assertIsNone(p['old_price'])
        self.assertEqual(p['vat'], '23')
        self.assertEqual(p['categories'], [{'c1': '30', 'c2': '63', 'name': 'Rajstopy / lycra'}])
        self.assertEqual(p['raw_data']['similar_products'], ['63194'])
        self.assertEqual(len(p['images']), 1)
        self.assertEqual(p['images'][0]['api_image_id'], '305045')

    def test_parses_variants_with_and_without_ean(self):
        products = {p['api_id']: p for p in iter_products(SAMPLE_XML)}
        variants = products[161]['variants']
        self.assertEqual(len(variants), 3)

        with_ean = next(v for v in variants if v['ean'] == '000223000290')
        self.assertEqual(with_ean['variant_key'], '000223000290')
        self.assertEqual(with_ean['stock'], 43)
        self.assertEqual(with_ean['color'], 'nero/czarny')
        self.assertEqual(with_ean['size'], '2-S')

        without_ean = next(v for v in variants if v['color'] == 'bez EAN')
        self.assertEqual(without_ean['ean'], '')
        self.assertEqual(without_ean['variant_key'], 'bez EAN|uniwersalny')

    def test_product_without_variants_or_images(self):
        products = {p['api_id']: p for p in iter_products(SAMPLE_XML)}
        p = products[162]
        self.assertEqual(p['variants'], [])
        self.assertEqual(p['images'], [])
        self.assertEqual(p['old_price'], '14.99')

    def test_skips_malformed_xml_gracefully(self):
        broken = b'<DATA><PRODUCTS><PRODUCT><ID>not-a-number</ID></PRODUCT></PRODUCTS></DATA>'
        self.assertEqual(list(iter_products(broken)), [])
