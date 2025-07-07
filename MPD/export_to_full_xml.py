import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from django.utils import timezone
from .models import Products, ProductVariants, StockAndPrices


def export_to_full_xml():
    """Generuje pełny plik XML z produktami w formacie IOF"""

    # Tworzenie głównego elementu offer
    root = ET.Element('offer')
    root.set('xmlns:iof', 'http://www.iai-shop.com/developers/iof.phtml')
    root.set('xmlns:iaiext',
             'http://www.iai-shop.com/developers/iof/extensions.phtml')
    root.set('file_format', 'IOF')
    root.set('generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    root.set('expires', (datetime.now() + timezone.timedelta(days=1)
                         ).strftime('%Y-%m-%d %H:%M:%S'))
    root.set('version', '3.0')
    root.set('extensions', 'yes')

    # Tworzenie elementu products
    products = ET.SubElement(root, 'products')
    products.set('xmlns:iaiext',
                 'http://www.iai-shop.com/developers/iof/extensions.phtml')
    products.set('currency', 'PLN')
    products.set('iof_translation_generated', 'yes')
    products.set('language', 'pol')

    # Pobieranie produktów z bazy danych
    products_data = Products.objects.all()

    for product in products_data:
        # Tworzenie elementu product
        product_element = ET.SubElement(products, 'product')
        product_element.set('id', str(product.id))
        product_element.set('currency', 'PLN')
        product_element.set('code_on_card', str(product.id))
        product_element.set('producer_code_standard', 'OTHER')
        product_element.set('type', 'regular')
        product_element.set('vat', '23.0')
        product_element.set('site', '1')

        # Dodawanie producenta
        if product.brand:
            producer = ET.SubElement(product_element, 'producer')
            producer.set('id', str(product.brand.id)
                         if product.brand.id else '1')
            producer.set('name', product.brand.name or 'Unknown')

        # Dodawanie kategorii (domyślna)
        category = ET.SubElement(product_element, 'category')
        category.set('id', '1')
        category.set('name', 'Domyślna kategoria')

        # Dodawanie jednostki
        unit = ET.SubElement(product_element, 'unit')
        unit.set('id', '0')
        unit.set('name', 'szt.')

        # Dodawanie serii
        series = ET.SubElement(product_element, 'series')
        series.set('id', '1')
        series.set('name', 'Default Series')

        # Dodawanie gwarancji
        warranty = ET.SubElement(product_element, 'warranty')
        warranty.set('id', '1')
        warranty.set('type', 'producer')
        warranty.set('period', '12')
        warranty.set('name', 'Gwarancja producenta na 1 rok')

        # Dodawanie karty produktu
        card = ET.SubElement(product_element, 'card')
        card.set('url', f'https://example.com/products/{product.id}.html')

        # Dodawanie opisu
        description = ET.SubElement(product_element, 'description')

        # Nazwa produktu
        name_eng = ET.SubElement(description, 'name')
        name_eng.set('xml:lang', 'eng')
        name_eng.text = f'Product {product.id}'

        name_pol = ET.SubElement(description, 'name')
        name_pol.set('xml:lang', 'pol')
        name_pol.text = product.name or f'Produkt {product.id}'

        # Długi opis
        long_desc_eng = ET.SubElement(description, 'long_desc')
        long_desc_eng.set('xml:lang', 'eng')
        long_desc_eng.text = f'Long description of product {product.id}'

        long_desc_pol = ET.SubElement(description, 'long_desc')
        long_desc_pol.set('xml:lang', 'pol')
        long_desc_pol.text = product.description or f'Opis długi produktu {product.id}'

        # Krótki opis
        short_desc_eng = ET.SubElement(description, 'short_desc')
        short_desc_eng.set('xml:lang', 'eng')
        short_desc_eng.text = f'Short description of product {product.id}'

        short_desc_pol = ET.SubElement(description, 'short_desc')
        short_desc_pol.set('xml:lang', 'pol')
        short_desc_pol.text = f'Opis krótki produktu {product.id}'

        # Pobieranie wariantów produktu
        variants = ProductVariants.objects.filter(product=product)

        if variants.exists():
            # Dodawanie rozmiarów
            sizes = ET.SubElement(product_element, 'sizes')
            sizes.set('iaiext:group_name', 'One size')
            sizes.set('iaiext:group_id', '-1')
            sizes.set('iaiext:sizeList', 'full')

            for variant in variants:
                # Pobieranie ceny i stanu magazynowego
                stock_price = StockAndPrices.objects.filter(
                    variant_id=variant.id).first()

                size = ET.SubElement(sizes, 'size')
                size.set('id', str(variant.id))
                size.set(
                    'name', variant.size.name if variant.size and variant.size.name else 'one size')
                size.set('panel_name',
                         variant.size.name if variant.size and variant.size.name else 'one size')
                size.set('code', f'{product.id}-{variant.id}')
                size.set('weight', '0')
                size.set('iaiext:weight_net', '0')
                size.set('code_producer', variant.ean or '')
                size.set('iaiext:code_external', '')
                size.set('iaiext:priority', '0')

                # Cena dla rozmiaru
                size_price = ET.SubElement(size, 'price')
                if stock_price:
                    size_price.set('gross', str(stock_price.price))
                    # Przykładowa cena netto (81% ceny brutto)
                    net_price = float(stock_price.price) * 0.81
                    size_price.set('net', str(net_price))
                else:
                    size_price.set('gross', '0')
                    size_price.set('net', '0')

                # Stan magazynowy
                stock = ET.SubElement(size, 'stock')
                stock.set('id', '1')
                if stock_price:
                    stock.set('quantity', str(stock_price.stock))
                    stock.set('available_stock_quantity',
                              str(stock_price.stock))
                    stock.set('stock_quantity', str(stock_price.stock))
                else:
                    stock.set('quantity', '0')
                    stock.set('available_stock_quantity', '0')
                    stock.set('stock_quantity', '0')
        else:
            # Domyślny rozmiar jeśli brak wariantów
            sizes = ET.SubElement(product_element, 'sizes')
            sizes.set('iaiext:group_name', 'One size')
            sizes.set('iaiext:group_id', '-1')
            sizes.set('iaiext:sizeList', 'full')

            size = ET.SubElement(sizes, 'size')
            size.set('id', 'uniw')
            size.set('name', 'one size')
            size.set('panel_name', 'one size')
            size.set('code', f'{product.id}-uniw')
            size.set('weight', '0')
            size.set('iaiext:weight_net', '0')
            size.set('code_producer', '')
            size.set('iaiext:code_external', '')
            size.set('iaiext:priority', '0')

            # Cena dla rozmiaru
            size_price = ET.SubElement(size, 'price')
            size_price.set('gross', '0')
            size_price.set('net', '0')

            # Stan magazynowy
            stock = ET.SubElement(size, 'stock')
            stock.set('id', '1')
            stock.set('quantity', '0')
            stock.set('available_stock_quantity', '0')
            stock.set('stock_quantity', '0')

        # Dodawanie obrazów
        images = ET.SubElement(product_element, 'images')
        large = ET.SubElement(images, 'large')

        # Domyślny obraz
        image = ET.SubElement(large, 'image')
        image.set('iaiext:priority', '1')
        image.set('url', f'https://example.com/images/{product.id}_1.jpg')
        image.set('hash', 'default_hash')
        image.set('changed', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        image.set('width', '4000')
        image.set('height', '2667')

        # Ikony
        icons = ET.SubElement(images, 'icons')
        icon = ET.SubElement(icons, 'icon')
        icon.set('url', f'https://example.com/icons/{product.id}.jpg')
        icon.set('hash', 'default_hash')
        icon.set('changed', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        icon.set('width', '350')
        icon.set('height', '233')

        # Dodawanie parametrów
        parameters = ET.SubElement(product_element, 'parameters')

        # Przykładowy parametr
        param = ET.SubElement(parameters, 'parameter')
        param.set('type', 'parameter')
        param.set('id', '1')
        param.set('priority', '0')
        param.set('distinction', 'n')
        param.set('group_distinction', 'n')
        param.set('hide', 'n')
        param.set('auction_template_hide', 'n')
        param.set('name', 'Przykładowy parametr')

        value = ET.SubElement(param, 'value')
        value.set('id', '1')
        value.set('priority', '0')
        value.set('name', 'Wartość')

    # Konwertowanie do stringa XML z formatowaniem
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8')

    return pretty_xml.decode('utf-8')


def save_xml_to_file(filename='export_full.xml'):
    """Zapisuje wygenerowany XML do pliku"""
    xml_content = export_to_full_xml()

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print(f'Plik XML został zapisany jako: {filename}')
    return filename


def create_xml_file():
    """Główna funkcja do wywołania eksportu XML"""
    try:
        filename = save_xml_to_file()
        print('✅ Eksport XML zakończony pomyślnie!')
        print(f'📁 Plik: {filename}')
        return filename
    except Exception as e:
        print(f'❌ Błąd podczas eksportu XML: {e}')
        return None
