import os
import hashlib
from matterhorn.defs_db import s3_client, DO_SPACES_BUCKET, DO_SPACES_REGION
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from django.utils import timezone
from .models import Sources

"""
Eksporter XML dla systemu MPD

Użycie:
- export_full() - eksport wszystkich produktów
- export_incremental() - eksport produktów zmienionych w ciągu ostatnich 2 godzin (do uruchamiania co godzinę)

Monitoring zmian:
- Sprawdza kolumny updated_at w tabelach: product_variants, products, product_variants_retail_price
- Sprawdza kolumnę last_updated w tabeli stock_and_prices
- Sprawdza kolumnę updated_at w tabeli product_images
- Generuje plik full.xml z produktami, które mają visibility=0 jeśli nie mają ceny detalicznej
- Generuje plik full_change.xml z produktami zmienionymi w ciągu ostatnich 2 godzin (tylko te już w full.xml)
- Generuje plik light.xml z produktami zmienionymi w ciągu ostatniej godziny
"""

logger = logging.getLogger(__name__)


class BaseXMLExporter:
    def __init__(self, filename):
        self.filename = filename

    def generate_xml(self):
        raise NotImplementedError

    def save_local(self, xml_content):
        local_dir = 'MPD_test/xml/matterhorn/'
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, self.filename)
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        return local_path

    def save_to_bucket(self, local_file_path):
        try:
            bucket_path = f"MPD_test/xml/matterhorn/{self.filename}"
            with open(local_file_path, 'rb') as f:
                file_data = f.read()
            s3_client.put_object(
                Bucket=DO_SPACES_BUCKET,
                Key=bucket_path,
                Body=file_data,
                ContentType='application/xml',
                ACL='public-read'
            )
            file_url = f"https://{DO_SPACES_BUCKET}.{DO_SPACES_REGION}.digitaloceanspaces.com/{bucket_path}"
            logger.info(
                f"Plik XML został pomyślnie przesłany do bucketa: {file_url}")
            return file_url
        except Exception as e:
            logger.error(
                f"Błąd podczas przesyłania pliku XML do bucketa: {str(e)}")
            return None

    def export(self):
        xml_content = self.generate_xml()
        local_path = self.save_local(xml_content)
        bucket_url = self.save_to_bucket(local_path)
        if bucket_url:
            print('✅ Eksport XML zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
        else:
            print('❌ Błąd podczas eksportu XML')
            print(f'📄 Lokalnie zapisano: {local_path}')
        return {'bucket_url': bucket_url, 'local_path': local_path}


class FullXMLExporter(BaseXMLExporter):
    def __init__(self):
        super().__init__('full.xml')

    def generate_navigation_xml(self, product_id):
        from .models import Paths, ProductPaths
        from django.utils.html import escape
        xml = []
        xml.append('      <iaiext:navigation>')
        xml.append('        <iaiext:site id="1">')
        xml.append('          <iaiext:menu id="1">')
        product_paths = ProductPaths.objects.using(
            'MPD').filter(product_id=product_id)
        path_ids = set(pp.path_id for pp in product_paths)
        paths = list(Paths.objects.using('MPD').filter(
            id__in=path_ids).order_by('id'))
        for idx, path in enumerate(paths, 1):
            textid = escape(path.path) if path.path else ''
            # Użyj iai_menu_id zamiast id dla węzła iaiext:item
            item_id = path.iai_menu_id if path.iai_menu_id else path.id
            xml.append(
                f'            <iaiext:item id="{item_id}" menu_id="1" textid="{textid}" iaiext:priority_menu="{idx}"/>')
        xml.append('          </iaiext:menu>')
        xml.append('        </iaiext:site>')
        xml.append('      </iaiext:navigation>')
        return '\n'.join(xml)

    def generate_xml(self, incremental=True):
        from django.utils.html import escape
        from .models import ProductVariants, ProductImage, StockAndPrices, ProductVariantsRetailPrice, ProductPaths, Paths, Vat
        from datetime import timedelta

        now = timezone.now()
        # Konwertuj na czas lokalny (Europe/Warsaw)
        local_now = timezone.localtime(now)
        local_expires = local_now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<offer file_format="IOF" version="3.0" generated="{}" expires="{}" extensions="yes" xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml">'.format(
            local_now.strftime('%Y-%m-%d %H:%M:%S'), local_expires.strftime('%Y-%m-%d %H:%M:%S')))
        xml.append('  <products language="pol">')

        # ZAWSZE generuj pełną ofertę - ignoruj parametr incremental
        # Pobierz wszystkie warianty z iai_product_id
        variants_with_iai = ProductVariants.objects.using('MPD').filter(
            iai_product_id__isnull=False
        ).select_related('product', 'size', 'color', 'producer_color', 'product__brand')
        logger.info("Generowanie pełnej oferty full.xml - wszystkie produkty")

        # Grupuj warianty po iai_product_id
        grouped_variants = {}
        for variant in variants_with_iai:
            iai_id = variant.iai_product_id
            if iai_id not in grouped_variants:
                grouped_variants[iai_id] = []
            grouped_variants[iai_id].append(variant)

        # Iteruj po unikalnych iai_product_id
        for iai_product_id, variants in grouped_variants.items():
            if not variants:
                continue

            # Pobierz pierwszy wariant do uzyskania danych produktu
            first_variant = variants[0]
            product = first_variant.product

            # Pobierz dane waluty i VAT z pierwszego wariantu
            currency = '' or 'PLN'
            vat_rate = ''
            has_price = False
            for variant in variants:
                pvrp = ProductVariantsRetailPrice.objects.using(
                    'MPD').filter(variant=variant).first()
                if pvrp:
                    currency = pvrp.currency or 'PLN'
                    if pvrp.vat:
                        vat_obj = Vat.objects.using(
                            'MPD').filter(id=pvrp.vat).first()
                        if vat_obj:
                            vat_rate = str(vat_obj.vat_rate)
                        else:
                            vat_rate = str(pvrp.vat)
                    has_price = True
                    break

            # Jeśli nie ma ceny, ustaw VAT na 0
            if not has_price:
                vat_rate = '0'

            xml.append(
                f'    <product id="{iai_product_id}" currency="{currency}" type="regular" vat="{vat_rate}" site="1">')

            if product.brand:
                xml.append(
                    f'      <producer id="{product.brand.iai_brand_id}" name="{escape(product.brand.name) if product.brand.name else ""}"/>')

            # Dodaj węzeł deliverer
            xml.append('      <iaiext:deliverer id="1" name="Matterhorn"/>')

            # Dodaj węzeł date_created z kolumny created_at
            if product.created_at:
                # Konwertuj na czas lokalny (Europe/Warsaw)
                local_created_at = timezone.localtime(product.created_at)
                xml.append(
                    f'      <iaiext:date_created datetime="{local_created_at.strftime("%Y-%m-%d %H:%M:%S")}"/>')

            # Dodaj węzeł modification_date z kolumny updated_at
            if product.updated_at:
                # Konwertuj na czas lokalny (Europe/Warsaw)
                local_updated_at = timezone.localtime(product.updated_at)
                xml.append(
                    f'      <iaiext:modification_date datetime="{local_updated_at.strftime("%Y-%m-%d %H:%M:%S")}"/>')

            # Dodaj wszystkie kategorie (category) powiązane z produktem
            product_paths = ProductPaths.objects.using(
                'MPD').filter(product_id=product.id)
            for product_path in product_paths:
                path_obj = Paths.objects.using('MPD').filter(
                    id=product_path.path_id).first()
                if path_obj:
                    # Użyj iai_category_id zamiast id, jeśli jest dostępny
                    category_id = path_obj.iai_category_id if path_obj.iai_category_id else path_obj.id
                    xml.append(
                        f'      <category id="{category_id}" name="{escape(path_obj.path)}"/>')

            # Dodaj jednostkę, jeśli jest przypisana
            if product.unit:
                xml.append(
                    f'      <unit id="{product.unit.unit_id}" name="{escape(product.unit.name) if product.unit.name else ""}"/>')

            if product.name:
                xml.append('      <description>')
                xml.append(f'        <name>{escape(product.name)}</name>')
                if product.short_description:
                    xml.append(
                        f'        <short_desc><![CDATA[{product.short_description}]]></short_desc>')
                if product.description:
                    xml.append(
                        f'        <long_desc><![CDATA[{product.description}]]></long_desc>')
                xml.append('      </description>')

            # Dodaj parametry produktu (kolor dla tego wariantu)
            if first_variant.color:
                xml.append('      <parameters>')
                xml.append(
                    '        <parameter type="parameter" id="26" name="Kolor">')
                xml.append(
                    f'          <value id="{first_variant.color.iai_colors_id}" name="{escape(first_variant.color.name)}"/>')
                xml.append('        </parameter>')
                xml.append('      </parameters>')

            # Dodaj cenę na poziomie produktu (pierwsza cena z pierwszego wariantu)
            first_stock_price = StockAndPrices.objects.using(
                'MPD').filter(variant=first_variant).first()
            if first_stock_price:
                retail_price_obj = ProductVariantsRetailPrice.objects.using(
                    'MPD').filter(variant=first_variant).first()
                if retail_price_obj:
                    gross = retail_price_obj.retail_price if hasattr(
                        retail_price_obj, 'retail_price') else ''
                    net = retail_price_obj.net_price if hasattr(
                        retail_price_obj, 'net_price') else ''
                    price_attrs = []
                    if gross or net:
                        if gross:
                            price_attrs.append(f'gross="{gross}"')
                        if net:
                            price_attrs.append(f'net="{net}"')
                    if price_attrs:
                        xml.append(f'      <price {" ".join(price_attrs)}/>')
                    else:
                        # Brak ceny w bazie - dodaj cenę 0 jako fallback
                        # Zgodnie z dokumentacją full.md, @net jest wymagany
                        xml.append('      <price gross="0" net="0"/>')

            # Użyj kolumny visibility z tabeli products
            xml.append('      <iaiext:visibility>')
            if product.visibility:
                xml.append('        <iaiext:site visible="yes"/>')
            else:
                xml.append('        <iaiext:site visible="no"/>')
            xml.append('      </iaiext:visibility>')

            # Dodaj sekcję nawigacyjną dla tego produktu (po description, przed sizes)
            xml.append(self.generate_navigation_xml(product.id))

            # Pobierz group_name z category pierwszego rozmiaru
            group_name = ''
            for variant in variants:
                if variant.size and variant.size.category:
                    group_name = variant.size.category
                    break

            if variants:
                xml.append(
                    f'      <sizes iaiext:group_name="{group_name}" iaiext:group_id="1098261181" iaiext:sizeList="full">')
                for variant in variants:
                    size_name = variant.size.name if variant.size else ""
                    # panel_name: size_name + '_' + group_name
                    panel_name = f'{size_name}_{group_name}' if size_name and group_name else size_name or group_name
                    # code_external: product_id-variant_id (variant_id jest unikalny dla każdego wariantu)
                    code_external = f'{product.id}-{variant.variant_id}'
                    # code_producer: z tabeli product_variants_sources (ean, gtin14, gtin13, other)
                    from .models import ProductvariantsSources
                    variant_source = ProductvariantsSources.objects.using(
                        'MPD').filter(variant=variant).first()
                    code_producer = ''
                    if variant_source:
                        # Sprawdź kolejno: ean, gtin14, gtin13, other
                        if variant_source.ean:
                            code_producer = variant_source.ean
                        elif variant_source.gtin14:
                            code_producer = variant_source.gtin14
                        elif variant_source.gtin13:
                            code_producer = variant_source.gtin13
                        elif variant_source.other:
                            code_producer = variant_source.other

                    # Buduj atrybuty do węzła <size>
                    size_id = variant.size.iai_size_id if variant.size and variant.size.iai_size_id else ''
                    # Dodaj wymagany atrybut @code w formacie iai_product_id-size_id
                    code_value = f"{iai_product_id}-{size_id}" if size_id else f"{iai_product_id}"
                    size_attrs = [
                        f'id="{size_id}"',
                        f'code="{escape(code_value)}"',
                        f'name="{escape(size_name)}"',
                        f'panel_name="{escape(panel_name)}"',
                        f'iaiext:code_external="{code_external}"'
                    ]
                    if code_producer:
                        size_attrs.append(
                            f'code_producer="{escape(code_producer)}"')
                        xml.append(
                            f'        <size {' '.join(size_attrs)}>'
                        )
                        stock_price = StockAndPrices.objects.using(
                            'MPD').filter(variant=variant).first()
                        if stock_price:
                            # Pobierz ceny detaliczne z product_variants_retail_price
                            retail_price_obj = None
                            try:
                                from .models import ProductVariantsRetailPrice
                                retail_price_obj = ProductVariantsRetailPrice.objects.using(
                                    'MPD').filter(variant=variant).first()
                            except Exception:
                                pass
                            gross = retail_price_obj.retail_price if retail_price_obj and hasattr(
                                retail_price_obj, 'retail_price') else ''
                            net = retail_price_obj.net_price if retail_price_obj and hasattr(
                                retail_price_obj, 'net_price') else ''
                            price_attrs = []
                            if gross or net:
                                if gross:
                                    price_attrs.append(f'gross="{gross}"')
                                if net:
                                    price_attrs.append(f'net="{net}"')

                            if price_attrs:
                                xml.append(
                                    f'          <price {" ".join(price_attrs)}/>')
                            else:
                                # Brak ceny w bazie - dodaj cenę 0 jako fallback (jak w light.xml)
                                # Zgodnie z dokumentacją full.md, @net jest wymagany
                                xml.append(
                                    '          <price gross="0" net="0"/>')

                            # Dodaj stan magazynowy
                            source = Sources.objects.filter(
                                id=stock_price.source.id).first() if stock_price and stock_price.source else None
                            stock_id = ""
                            if source and hasattr(source, 'type'):
                                if source.type == 'Magazyn główny':
                                    stock_id = "1"
                                elif source.type == 'Magazyn obcy':
                                    stock_id = "0"
                                elif source.type == 'Magazyn wymiany':
                                    stock_id = "3"
                                elif source.type == 'Magazyn pomocniczy':
                                    stock_id = "2"
                            xml.append(
                                f'          <stock id="{stock_id}" quantity="{stock_price.stock}"/>')
                    xml.append('        </size>')
                xml.append('      </sizes>')

            # Dodaj obrazy produktu (obrazy przypisane do tego iai_product_id)
            images = ProductImage.objects.using('MPD').filter(
                product=product,
                iai_product_id=iai_product_id
            )
            if images:
                xml.append('      <images>')
                xml.append('        <large>')
                for img in images:
                    xml.append(
                        f'          <image url="{escape(img.file_path)}"/>')
                xml.append('        </large>')
                xml.append('      </images>')

            xml.append('    </product>')

        xml.append('  </products>')
        xml.append('</offer>')

        # Tracking nie jest już potrzebne w nowej logice IdoSell
        logger.info(
            f"Eksport zakończony - wyeksportowano {variants_with_iai.count()} produktów")

        return '\n'.join(xml)

    def export_incremental(self):
        """Eksport przyrostowy - teraz generuje pełną ofertę"""
        # Wywołaj metodę bazową export() zamiast self.export()
        # Zawsze false - pełna oferta
        xml_content = self.generate_xml(incremental=False)
        local_path = self.save_local(xml_content)
        bucket_url = self.save_to_bucket(local_path)

        result = {'bucket_url': bucket_url, 'local_path': local_path}

        if bucket_url:
            print('✅ Eksport pełnej oferty XML zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
        else:
            print('❌ Błąd podczas eksportu XML')
            print(f'📄 Lokalnie zapisano: {local_path}')

        return result

    def export_full(self):
        """Eksport pełny - wszystkie produkty"""
        xml_content = self.generate_xml(
            incremental=False)  # Zawsze false - pełna oferta
        local_path = self.save_local(xml_content)
        bucket_url = self.save_to_bucket(local_path)

        # Zapisz rekord o wygenerowanym pliku full.xml
        self.save_full_record(bucket_url, local_path)

        if bucket_url:
            print('✅ Pełny eksport XML zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
        else:
            print('❌ Błąd podczas pełnego eksportu XML')
            print(f'📄 Lokalnie zapisano: {local_path}')
        return {'bucket_url': bucket_url, 'local_path': local_path}

    def save_full_record(self, bucket_url, local_path):
        """Zapisz rekord o wygenerowanym pliku full.xml"""
        from .models import FullChangeFile
        from django.utils import timezone
        try:
            now = timezone.now()
            local_now = timezone.localtime(now)
            timestamp = local_now.strftime('%Y-%m-%dT%H-%M-%S')
            FullChangeFile.objects.using('MPD').create(
                filename='full.xml',
                timestamp=timestamp,
                created_at=now,
                bucket_url=bucket_url,
                local_path=local_path,
                file_size=os.path.getsize(
                    local_path) if os.path.exists(local_path) else 0
            )
            print(f"✅ Zapisano rekord pliku full.xml: {timestamp}")
        except Exception as e:
            print(f"❌ Błąd podczas zapisywania rekordu full.xml: {str(e)}")


class LightXMLExporter(BaseXMLExporter):
    def __init__(self):
        super().__init__('light.xml')

    def export(self):
        xml_content = self.generate_xml()
        local_path = self.save_local(xml_content)

        # Zapisz rekord do bazy danych
        from .models import FullChangeFile

        light_file = FullChangeFile.objects.using('MPD').create(
            filename='light.xml',
            timestamp=timezone.localtime(
                timezone.now()).strftime('%Y-%m-%dT%H-%M-%S'),
            local_path=local_path,
            file_size=0,  # Zostanie zaktualizowane po zapisie

        )

        # Zaktualizuj rozmiar pliku
        if os.path.exists(local_path):
            light_file.file_size = os.path.getsize(local_path)
            light_file.save(using='MPD')

        bucket_url = self.save_to_bucket(local_path)
        if bucket_url:
            print('✅ Eksport XML zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
        else:
            print('❌ Błąd podczas eksportu XML')
            print(f'📄 Lokalnie zapisano: {local_path}')
        return {'bucket_url': bucket_url, 'local_path': local_path}

    def generate_xml(self):
        from django.utils.html import escape
        from .models import Products, ProductVariants, StockAndPrices, ProductVariantsRetailPrice, ProductvariantsSources, Vat, FullChangeFile
        from datetime import timedelta

        now = timezone.now()
        # Konwertuj na czas lokalny (Europe/Warsaw)
        local_now = timezone.localtime(now)
        local_expires = local_now + timedelta(days=1)

        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<offer file_format="IOF" version="3.0" generated="{}" expires="{}" extensions="yes" xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml">'.format(
            local_now.strftime('%Y-%m-%d %H:%M:%S'), local_expires.strftime('%Y-%m-%d %H:%M:%S')))
        xml.append('  <products language="pol">')

        # Eksport przyrostowy - tylko produkty zmienione w ciągu ostatniej godziny
        from datetime import timedelta
        from django.db.models import Q

        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)

        # Pobierz datę utworzenia ostatniego pliku full.xml
        last_full_file = FullChangeFile.objects.using('MPD').filter(
            filename='full.xml'
        ).order_by('-created_at').first()

        if last_full_file:
            # Eksportuj tylko produkty ze zmienionymi stanami magazynowymi lub cenami w ciągu ostatniej godziny,
            # które były już w full.xml (utworzone przed datą full.xml)
            full_file_created_at = last_full_file.created_at
            products = Products.objects.using('MPD').filter(
                Q(productvariants__stockandprices__last_updated__gte=one_hour_ago) |
                Q(productvariants__productvariantsretailprice__updated_at__gte=one_hour_ago),
                created_at__lte=full_file_created_at
            ).distinct().select_related('brand')
            logger.info(
                f"Light.xml: eksportuję produkty ze zmienionymi stanami/cenami w ciągu ostatniej godziny, utworzone przed {full_file_created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            # Brak pliku full.xml - eksportuj produkty ze zmienionymi stanami/cenami
            products = Products.objects.using('MPD').filter(
                Q(productvariants__stockandprices__last_updated__gte=one_hour_ago) |
                Q(productvariants__productvariantsretailprice__updated_at__gte=one_hour_ago)
            ).distinct().select_related('brand')
            logger.info(
                "Light.xml: brak pliku full.xml - eksportuję produkty ze zmienionymi stanami/cenami z ostatniej godziny")

        for product in products:
            # Pobierz warianty dla tego produktu
            variants = ProductVariants.objects.using('MPD').filter(
                product=product
            ).select_related('size', 'color', 'producer_color')

            if variants:
                # Użyj iai_product_id z pierwszego wariantu
                first_variant = variants.first()
                iai_product_id = first_variant.iai_product_id if first_variant and first_variant.iai_product_id else product.id

                # Pobierz VAT z pierwszego wariantu który ma cenę detaliczną
                vat_rate = None
                for variant in variants:
                    retail_price = ProductVariantsRetailPrice.objects.using('MPD').filter(
                        variant=variant
                    ).first()
                    if retail_price and retail_price.vat:
                        # Pobierz VAT z tabeli vat
                        vat_obj = Vat.objects.using('MPD').filter(
                            id=retail_price.vat
                        ).first()
                        if vat_obj:
                            vat_rate = vat_obj.vat_rate
                        else:
                            vat_rate = retail_price.vat
                        break

                # Pobierz group_name z category rozmiaru (jak w FullXMLExporter)
                group_name = ''
                for variant in variants:
                    if variant.size and variant.size.category:
                        group_name = variant.size.category
                        break

                # Buduj atrybuty produktu
                product_attrs = [f'id="{iai_product_id}"']
                if vat_rate:
                    product_attrs.append(f'vat="{vat_rate}"')
                else:
                    # Brak VAT w bazie - dodaj VAT 0 jako fallback
                    product_attrs.append('vat="0"')

                xml.append(f'    <product {" ".join(product_attrs)}>')

                # Dodaj cenę na poziomie produktu (jeśli istnieje)
                first_variant_retail = ProductVariantsRetailPrice.objects.using('MPD').filter(
                    variant=variants.first()
                ).first()
                if first_variant_retail:
                    gross = first_variant_retail.retail_price if hasattr(
                        first_variant_retail, 'retail_price') else ''
                    net = first_variant_retail.net_price if hasattr(
                        first_variant_retail, 'net_price') else ''

                    price_attrs = []
                    if gross or net:
                        if gross:
                            price_attrs.append(f'gross="{gross}"')
                        if net:
                            price_attrs.append(f'net="{net}"')

                    if price_attrs:
                        xml.append(f'      <price {" ".join(price_attrs)}/>')
                else:
                    # Brak ceny w bazie - dodaj cenę 0 jako fallback
                    xml.append('      <price gross="0" net="0"/>')

                # Dodaj cenę detaliczną na poziomie produktu (jeśli istnieje)
                # try:
                #     if first_variant_retail and hasattr(first_variant_retail, 'retail_price') and first_variant_retail.retail_price:
                #         xml.append(
                #             f'      <srp net="{first_variant_retail.retail_price}"/>')
                # except Exception:
                #     pass

                xml.append('      <sizes>')

                for variant in variants:
                    # Pobierz dane o rozmiarze
                    size_id = variant.size.iai_size_id if variant.size and variant.size.iai_size_id else ''
                    size_name = variant.size.name if variant.size else ""
                    # panel_name: size_name + '_' + group_name (group_name z brand produktu)
                    panel_name = f'{size_name}_{group_name}' if size_name and group_name else size_name or group_name

                    # code_external: product_id-variant_id (identycznie jak w FullXMLExporter)
                    code_external = f'{product.id}-{variant.variant_id}'

                    # Pobierz kod producenta - identycznie jak w FullXMLExporter
                    code_producer = ""
                    try:
                        variant_source = ProductvariantsSources.objects.using('MPD').filter(
                            variant=variant
                        ).first()
                        if variant_source:
                            # Sprawdź kolejno: ean, gtin14, gtin13, other (identycznie jak w FullXMLExporter)
                            if variant_source.ean:
                                code_producer = variant_source.ean
                            elif variant_source.gtin14:
                                code_producer = variant_source.gtin14
                            elif variant_source.gtin13:
                                code_producer = variant_source.gtin13
                            elif variant_source.other:
                                code_producer = variant_source.other
                    except Exception:
                        pass

                    # Buduj atrybuty rozmiaru - tylko wymagane
                    size_attrs = []
                    if size_id:
                        size_attrs.append(f'id="{size_id}"')
                    if size_name:
                        size_attrs.append(f'name="{escape(size_name)}"')
                    if panel_name:
                        size_attrs.append(f'panel_name="{escape(panel_name)}"')
                    if code_producer:
                        size_attrs.append(
                            f'code_producer="{escape(code_producer)}"')
                    if code_external:
                        size_attrs.append(
                            f'iaiext:code_external="{escape(code_external)}"')

                    xml.append(f'        <size {" ".join(size_attrs)}>')

                    # Pobierz cenę i stan magazynowy
                    stock_price = StockAndPrices.objects.using('MPD').filter(
                        variant=variant
                    ).first()

                    if stock_price:
                        # Dodaj cenę na poziomie rozmiaru - identycznie jak w FullXMLExporter
                        try:
                            retail_price_obj = ProductVariantsRetailPrice.objects.using('MPD').filter(
                                variant=variant
                            ).first()
                        except Exception:
                            pass

                        gross = retail_price_obj.retail_price if retail_price_obj and hasattr(
                            retail_price_obj, 'retail_price') else ''
                        net = retail_price_obj.net_price if retail_price_obj and hasattr(
                            retail_price_obj, 'net_price') else ''

                        price_attrs = []
                        if gross or net:
                            if gross:
                                price_attrs.append(f'gross="{gross}"')
                            if net:
                                price_attrs.append(f'net="{net}"')

                        if price_attrs:
                            xml.append(
                                f'          <price {" ".join(price_attrs)}/>')
                        else:
                            # Brak ceny w bazie - dodaj cenę 0 jako fallback
                            xml.append('          <price gross="0" net="0"/>')

                        # Dodaj stan magazynowy - tak samo jak w full.xml
                        stock_id = ""
                        if stock_price.source and hasattr(stock_price.source, 'type'):
                            if stock_price.source.type == 'Magazyn główny':
                                stock_id = "1"
                            elif stock_price.source.type == 'Magazyn obcy':
                                stock_id = "0"
                            elif stock_price.source.type == 'Magazyn wymiany':
                                stock_id = "3"
                            elif stock_price.source.type == 'Magazyn pomocniczy':
                                stock_id = "2"

                        xml.append(
                            f'          <stock id="{stock_id}" quantity="{stock_price.stock}"/>')

                    # Pobierz cenę detaliczną na poziomie rozmiaru
                    # try:
                    #     retail_price = ProductVariantsRetailPrice.objects.using('MPD').filter(
                    #         variant=variant
                    #     ).first()
                    #     if retail_price and hasattr(retail_price, 'retail_price') and retail_price.retail_price:
                    #         xml.append(
                    #             f'          <srp net="{retail_price.retail_price}"/>')
                    # except Exception:
                    #     pass

                    xml.append('        </size>')

                xml.append('      </sizes>')
                xml.append('    </product>')

        xml.append('  </products>')
        xml.append('</offer>')
        return '\n'.join(xml)

    def export_incremental(self):
        """Eksport przyrostowy - tylko produkty zmienione w ciągu ostatniej godziny"""
        from datetime import timedelta
        from django.db.models import Q
        from .models import Products, FullChangeFile

        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)

        # Pobierz datę utworzenia ostatniego pliku full.xml
        last_full_file = FullChangeFile.objects.using('MPD').filter(
            filename='full.xml'
        ).order_by('-created_at').first()

        if last_full_file:
            # Eksportuj tylko produkty zmienione w ciągu ostatniej godziny,
            # które były już w full.xml (utworzone przed datą full.xml)
            full_file_created_at = last_full_file.created_at
            products = Products.objects.using('MPD').filter(
                Q(updated_at__gte=one_hour_ago) |
                Q(productvariants__updated_at__gte=one_hour_ago) |
                Q(productvariants__stockandprices__last_updated__gte=one_hour_ago) |
                Q(productvariants__productvariantsretailprice__updated_at__gte=one_hour_ago),
                created_at__lte=full_file_created_at
            ).distinct().select_related('brand')
            logger.info(
                f"Light.xml incremental: eksportuję produkty zmienione w ciągu ostatniej godziny, utworzone przed {full_file_created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            # Brak pliku full.xml - eksportuj wszystkie zmienione produkty
            products = Products.objects.using('MPD').filter(
                Q(updated_at__gte=one_hour_ago) |
                Q(productvariants__updated_at__gte=one_hour_ago) |
                Q(productvariants__stockandprices__last_updated__gte=one_hour_ago) |
                Q(productvariants__productvariantsretailprice__updated_at__gte=one_hour_ago)
            ).distinct().select_related('brand')
            logger.info(
                "Light.xml incremental: brak pliku full.xml - eksportuję wszystkie zmienione produkty")

        # Generuj XML tylko dla zmienionych produktów
        xml_content = self._generate_xml_for_products(products)
        local_path = self.save_local(xml_content)
        bucket_url = self.save_to_bucket(local_path)

        if bucket_url:
            print('✅ Eksport przyrostowy light.xml zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
        else:
            print('❌ Błąd podczas eksportu przyrostowego light.xml')
            print(f'📄 Lokalnie zapisano: {local_path}')

        return {'bucket_url': bucket_url, 'local_path': local_path}

    def _generate_xml_for_products(self, products):
        """Generuj XML dla określonej listy produktów"""
        from django.utils.html import escape
        from .models import ProductVariants, StockAndPrices, ProductVariantsRetailPrice, ProductvariantsSources, Vat
        from datetime import timedelta

        now = timezone.now()
        # Konwertuj na czas lokalny (Europe/Warsaw)
        local_now = timezone.localtime(now)
        local_expires = local_now + timedelta(days=1)

        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<offer file_format="IOF" version="3.0" generated="{}" expires="{}" extensions="yes" xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml">'.format(
            local_now.strftime('%Y-%m-%d %H:%M:%S'), local_expires.strftime('%Y-%m-%d %H:%M:%S')))
        xml.append('  <products language="pol">')

        for product in products:
            # Pobierz warianty dla tego produktu
            variants = ProductVariants.objects.using('MPD').filter(
                product=product
            ).select_related('size', 'color', 'producer_color')

            if variants:
                # Użyj iai_product_id z pierwszego wariantu
                first_variant = variants.first()
                iai_product_id = first_variant.iai_product_id if first_variant and first_variant.iai_product_id else product.id

                # Pobierz VAT z pierwszego wariantu który ma cenę detaliczną
                vat_rate = None
                for variant in variants:
                    retail_price = ProductVariantsRetailPrice.objects.using('MPD').filter(
                        variant=variant
                    ).first()
                    if retail_price and retail_price.vat:
                        # Pobierz VAT z tabeli vat
                        vat_obj = Vat.objects.using('MPD').filter(
                            id=retail_price.vat
                        ).first()
                        if vat_obj:
                            vat_rate = vat_obj.vat_rate
                        else:
                            vat_rate = retail_price.vat
                        break

                # Pobierz group_name z category rozmiaru
                group_name = ''
                for variant in variants:
                    if variant.size and variant.size.category:
                        group_name = variant.size.category
                        break

                # Buduj atrybuty produktu
                product_attrs = [f'id="{iai_product_id}"']
                if vat_rate:
                    product_attrs.append(f'vat="{vat_rate}"')
                else:
                    # Brak VAT w bazie - dodaj VAT 0 jako fallback
                    product_attrs.append('vat="0"')

                xml.append(f'    <product {" ".join(product_attrs)}>')

                # Dodaj cenę na poziomie produktu (jeśli istnieje)
                first_variant_retail = ProductVariantsRetailPrice.objects.using('MPD').filter(
                    variant=variants.first()
                ).first()
                if first_variant_retail:
                    gross = first_variant_retail.retail_price if hasattr(
                        first_variant_retail, 'retail_price') else ''
                    net = first_variant_retail.net_price if hasattr(
                        first_variant_retail, 'net_price') else ''

                    price_attrs = []
                    if gross or net:
                        if gross:
                            price_attrs.append(f'gross="{gross}"')
                        if net:
                            price_attrs.append(f'net="{net}"')

                    if price_attrs:
                        xml.append(f'      <price {" ".join(price_attrs)}/>')

                xml.append('      <sizes>')

                for variant in variants:
                    # Pobierz dane o rozmiarze
                    size_id = variant.size.iai_size_id if variant.size and variant.size.iai_size_id else ''
                    size_name = variant.size.name if variant.size else ""
                    panel_name = f'{size_name}_{group_name}' if size_name and group_name else size_name or group_name

                    # code_external: product_id-variant_id
                    code_external = f'{product.id}-{variant.variant_id}'

                    # Pobierz kod producenta
                    code_producer = ""
                    try:
                        variant_source = ProductvariantsSources.objects.using('MPD').filter(
                            variant=variant
                        ).first()
                        if variant_source:
                            if variant_source.ean:
                                code_producer = variant_source.ean
                            elif variant_source.gtin14:
                                code_producer = variant_source.gtin14
                            elif variant_source.gtin13:
                                code_producer = variant_source.gtin13
                            elif variant_source.other:
                                code_producer = variant_source.other
                    except Exception:
                        pass

                    # Buduj atrybuty rozmiaru
                    size_attrs = []
                    if size_id:
                        size_attrs.append(f'id="{size_id}"')
                    if size_name:
                        size_attrs.append(f'name="{escape(size_name)}"')
                    if panel_name:
                        size_attrs.append(f'panel_name="{escape(panel_name)}"')
                    if code_producer:
                        size_attrs.append(
                            f'code_producer="{escape(code_producer)}"')
                    if code_external:
                        size_attrs.append(
                            f'iaiext:code_external="{escape(code_external)}"')

                    xml.append(f'        <size {" ".join(size_attrs)}>')

                    # Pobierz cenę i stan magazynowy
                    stock_price = StockAndPrices.objects.using('MPD').filter(
                        variant=variant
                    ).first()

                    if stock_price:
                        # Dodaj cenę na poziomie rozmiaru
                        try:
                            retail_price_obj = ProductVariantsRetailPrice.objects.using('MPD').filter(
                                variant=variant
                            ).first()
                        except Exception:
                            pass

                        gross = retail_price_obj.retail_price if retail_price_obj and hasattr(
                            retail_price_obj, 'retail_price') else ''
                        net = retail_price_obj.net_price if retail_price_obj and hasattr(
                            retail_price_obj, 'net_price') else ''

                        price_attrs = []
                        if gross or net:
                            if gross:
                                price_attrs.append(f'gross="{gross}"')
                            if net:
                                price_attrs.append(f'net="{net}"')

                        if price_attrs:
                            xml.append(
                                f'          <price {" ".join(price_attrs)}/>')

                        # Dodaj stan magazynowy
                        stock_id = ""
                        if stock_price.source and hasattr(stock_price.source, 'type'):
                            if stock_price.source.type == 'Magazyn główny':
                                stock_id = "1"
                            elif stock_price.source.type == 'Magazyn obcy':
                                stock_id = "0"
                            elif stock_price.source.type == 'Magazyn wymiany':
                                stock_id = "3"
                            elif stock_price.source.type == 'Magazyn pomocniczy':
                                stock_id = "2"

                        xml.append(
                            f'          <stock id="{stock_id}" quantity="{stock_price.stock}"/>')

                    xml.append('        </size>')

                xml.append('      </sizes>')
                xml.append('    </product>')

        xml.append('  </products>')
        xml.append('</offer>')
        return '\n'.join(xml)


class GatewayXMLExporter(BaseXMLExporter):
    def __init__(self, source_name=None):
        # Zawsze używaj Matterhorn (id=2), ignoruj source_name
        super().__init__('gateway.xml')
        try:
            self.source = Sources.objects.get(id=2)  # Tylko Matterhorn
            self.source_name = self.source.name
        except Exception:
            raise ValueError("Nie znaleziono źródła Matterhorn (id=2)")

    def _create_meta_element(self, root, request_time=None, full_time=None):
        from datetime import timedelta
        meta = ET.SubElement(root, "meta")
        long_name = ET.SubElement(meta, "long_name")
        long_name.text = f"<![CDATA[{self.source.long_name}]]>" if self.source.long_name else ""
        short_name = ET.SubElement(meta, "short_name")
        short_name.text = f"<![CDATA[{self.source.short_name}]]>" if self.source.short_name else ""
        if self.source.showcase_image:
            showcase_image = ET.SubElement(meta, "showcase_image")
            showcase_image.set("url", self.source.showcase_image)
        if self.source.email:
            email = ET.SubElement(meta, "email")
            email.text = f"<![CDATA[{self.source.email}]]>"
        if self.source.tel:
            tel = ET.SubElement(meta, "tel")
            tel.text = f"<![CDATA[{self.source.tel}]]>"

        # Dodaj fax (wymagany przez XSD)
        fax = ET.SubElement(meta, "fax")
        fax.text = f"<![CDATA[{getattr(self.source, 'fax', '+48 503 503 876')}]]>"

        if self.source.www:
            www = ET.SubElement(meta, "www")
            www.text = f"<![CDATA[{self.source.www}]]>"
        if any([self.source.street, self.source.zipcode, self.source.city, self.source.country]):
            address = ET.SubElement(meta, "address")
            if self.source.street:
                street = ET.SubElement(address, "street")
                street.text = f"<![CDATA[{self.source.street}]]>"
            if self.source.zipcode:
                zipcode = ET.SubElement(address, "zipcode")
                zipcode.text = f"<![CDATA[{self.source.zipcode}]]>"
            if self.source.city:
                city = ET.SubElement(address, "city")
                city.text = f"<![CDATA[{self.source.city}]]>"
            if self.source.country:
                country = ET.SubElement(address, "country")
                country.text = f"<![CDATA[{self.source.country}]]>"
        time = ET.SubElement(meta, "time")
        offer_created = ET.SubElement(time, "offer")

        # Użyj full_time jako bazowego czasu, aby created nie było późniejsze niż changed
        if full_time:
            # Konwertuj string na datetime
            from datetime import datetime
            try:
                # Parsuj czas z formatu "YYYY-MM-DD HH:MM:SS"
                base_time = datetime.strptime(full_time, "%Y-%m-%d %H:%M:%S")
                # Konwertuj na timezone-aware datetime
                base_time = timezone.make_aware(base_time)
            except ValueError:
                # Fallback: użyj request_time lub aktualnego czasu
                base_time = request_time if request_time else timezone.now()
        else:
            # Brak full_time - użyj request_time lub aktualnego czasu
            base_time = request_time if request_time else timezone.now()

        # Konwertuj na lokalny czas (Europe/Warsaw)
        local_base_time = timezone.localtime(base_time)

        offer_created.set(
            "created", local_base_time.strftime("%Y-%m-%d %H:%M:%S"))
        offer_expires = ET.SubElement(time, "offer")
        offer_expires.set("expires", (local_base_time +
                          timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"))

    def _create_url_elements(self, root, request_time=None, full_time=None):
        # Użyj endpointów API zamiast statycznych plików
        from django.conf import settings

        # Podstawowy URL dla API z ustawień Django
        base_url = getattr(settings, 'API_BASE_URL', 'http://localhost:8000')

        # Użyj czasu żądania HTTP lub aktualnego czasu
        if request_time is None:
            request_time = timezone.now()

        # Dodaj węzeł full z podwęzłem changes dla plików full_change
        print("=== WYWOŁUJĘ _create_full_with_changes_element ===")
        logger.info("=== WYWOŁUJĘ _create_full_with_changes_element ===")
        self._create_full_with_changes_element(
            root, base_url, request_time, full_time)

        # Dodaj wymagane elementy zgodnie ze schematem XSD
        self._create_light_element(root, base_url)
        self._create_categories_element(root, base_url)
        self._create_sizes_element(root, base_url)
        self._create_producers_element(root, base_url)

        # Opcjonalne elementy - pomijamy na chwilę obecną
        # self._create_units_element(root, base_url)
        # self._create_parameters_element(root, base_url)
        # self._create_stocks_element(root, base_url)
        # self._create_series_element(root, base_url)
        # self._create_warranties_element(root, base_url)
        # self._create_preset_element(root, base_url)

    def _create_full_with_changes_element(self, root, base_url, request_time=None, full_time=None):
        """Tworzy węzeł full z podwęzłem changes dla rzeczywistych zmian w produktach"""
        print("=== ROZPOCZYNAM _create_full_with_changes_element ===")
        logger.info("=== ROZPOCZYNAM _create_full_with_changes_element ===")

        try:
            # Utwórz węzeł full
            full_element = ET.SubElement(root, "full")

            # Dodaj podstawowe atrybuty dla full.xml - użyj endpointu API
            full_url = f"{base_url}/mpd/generate-full-xml/"
            full_element.set("url", full_url)

            # Dla endpointów API używamy czasu żądania HTTP
            import hashlib
            from django.utils import timezone

            # Użyj czasu żądania HTTP lub aktualnego czasu
            if request_time is None:
                request_time = timezone.now()

            # Konwertuj na lokalny czas (Europe/Warsaw)
            local_request_time = timezone.localtime(request_time)

            # Użyj przekazanego full_time zamiast pobierania z bazy
            if not full_time:
                # Fallback: pobierz z bazy jeśli nie przekazano
                from .models import FullChangeFile
                last_full_file = FullChangeFile.objects.using('MPD').filter(
                    filename='full.xml'
                ).order_by('-created_at').first()

                if last_full_file:
                    full_time = timezone.localtime(
                        last_full_file.created_at).strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(
                        f"Używam czasu ostatniego full.xml: {full_time}")
                else:
                    full_time = ""
                    logger.info(
                        "Brak pliku full.xml w bazie - używam pustych wartości")
            else:
                # Jeśli full_time jest przekazane, pobierz last_full_file dla hash
                from .models import FullChangeFile
                last_full_file = FullChangeFile.objects.using('MPD').filter(
                    filename='full.xml'
                ).order_by('-created_at').first()

            # Hash bazujący na rzeczywistych danych + czasie
            from .models import Products
            from django.db import models
            if last_full_file:
                try:
                    # Pobierz liczbę produktów i ostatni timestamp modyfikacji
                    total_products = Products.objects.using('MPD').count()
                    last_modified = Products.objects.using('MPD').aggregate(
                        last_modified=models.Max('updated_at')
                    )['last_modified']

                    if last_modified:
                        last_modified_str = last_modified.strftime(
                            '%Y-%m-%d %H:%M:%S')
                    else:
                        last_modified_str = "1970-01-01 00:00:00"

                    # Hash bazujący na: liczba produktów + ostatnia modyfikacja + czas full.xml
                    full_hash_input = f"generate-full-xml_{total_products}_{last_modified_str}_{full_time}"
                    full_hash = hashlib.md5(
                        full_hash_input.encode()).hexdigest()

                    logger.info(
                        f"Full.xml hash: products={total_products}, last_modified={last_modified_str}, full_time={full_time}")

                except Exception as e:
                    # Fallback: hash bazujący tylko na czasie
                    full_hash_input = f"generate-full-xml_{full_time}"
                    full_hash = hashlib.md5(
                        full_hash_input.encode()).hexdigest()
                    logger.warning(
                        f"Błąd generowania hash dla full.xml: {str(e)}, używam fallback")
            else:
                # Brak rekordu full.xml w bazie - użyj pustego hasha
                full_hash = ""
                logger.info(
                    "Brak pliku full.xml w bazie - używam pustego hasha")

            full_element.set("hash", full_hash)
            full_element.set("changed", full_time)

            # Sprawdź rzeczywiste pliki full_change.xml z bazy

            # Pobierz ostatnie 25 plików full_change.xml z bazy
            recent_full_change_files = FullChangeFile.objects.using('MPD').filter(
                filename__startswith='full_change'
            ).order_by('-created_at')[:25]

            # Debug: sprawdź ile plików full_change znaleziono
            print(
                f"Znaleziono {recent_full_change_files.count()} plików full_change w bazie")
            logger.info(
                f"Znaleziono {recent_full_change_files.count()} plików full_change w bazie")

            # Debug: wyświetl nazwy plików
            for fcf in recent_full_change_files:
                print(
                    f"Plik w bazie: {fcf.filename} (created_at: {fcf.created_at})")
                logger.info(
                    f"Plik w bazie: {fcf.filename} (created_at: {fcf.created_at})")

            # Zawsze utwórz podwęzeł changes
            changes_element = ET.SubElement(full_element, "changes")

            if recent_full_change_files.exists():
                print(
                    f"Znaleziono {recent_full_change_files.count()} plików full_change, przetwarzam...")
                logger.info(
                    f"Znaleziono {recent_full_change_files.count()} plików full_change, przetwarzam...")
                # Generuj change dla każdego wygenerowanego pliku full_change.xml
                for full_change_file in recent_full_change_files:
                    print(f"Przetwarzam plik: {full_change_file.filename}")
                    logger.info(
                        f"Przetwarzam plik: {full_change_file.filename}")
                    change_element = ET.SubElement(changes_element, "change")

                    # Nazwa pliku: full_change2025-09-02T09-06-15.xml (czas lokalny)
                    # Wyciągnij timestamp z nazwy pliku i potraktuj jako czas lokalny
                    filename = full_change_file.filename
                    change_time = None
                    print(f"DEBUG: Przetwarzam plik {filename}")
                    print(f"DEBUG: Długość nazwy pliku: {len(filename)}")
                    print(f"DEBUG: filename[12:-4] = '{filename[12:-4]}'")
                    print(f"DEBUG: filename[12:] = '{filename[12:]}'")
                    print(f"DEBUG: filename[:-4] = '{filename[:-4]}'")
                    print(f"DEBUG: filename[0:12] = '{filename[0:12]}'")
                    print(f"DEBUG: filename[12] = '{filename[12]}'")
                    print(f"DEBUG: filename[13] = '{filename[13]}'")
                    print(f"DEBUG: filename[14] = '{filename[14]}'")

                    if filename.startswith('full_change') and filename.endswith('.xml'):
                        # Wyciągnij timestamp z nazwy pliku (np. "2025-09-02T09-06-15")
                        # Usuń "full_change" i ".xml" - użyj bezpiecznego podejścia
                        timestamp_part = filename.replace(
                            'full_change', '').replace('.xml', '')
                        print(f"DEBUG: timestamp_part = {timestamp_part}")

                        # Spróbuj różne formaty timestamp
                        timestamp_formats = [
                            '%Y-%m-%dT%H-%M-%S',  # 2025-09-02T09-06-15
                            # 25-09-02T09-06-15 (rok 2-cyfrowy)
                            '%y-%m-%dT%H-%M-%S',
                            '%m-%dT%H-%M-%S',     # 09-02T09-06-15 (bez roku)
                        ]

                        # Dodatkowe formaty dla niepoprawnych nazw plików
                        if timestamp_part.startswith('0'):
                            # Format dla 025-09-02T22-33-26 (3-cyfrowy rok)
                            try:
                                # Wyciągnij rok, miesiąc, dzień, godzinę, minutę, sekundę
                                parts = timestamp_part.split('T')
                                if len(parts) == 2:
                                    date_part = parts[0]  # 025-09-02
                                    time_part = parts[1]  # 22-33-26

                                    date_parts = date_part.split('-')
                                    time_parts = time_part.split('-')

                                    if len(date_parts) == 3 and len(time_parts) == 3:
                                        year = int(date_parts[0])  # 025
                                        month = int(date_parts[1])  # 09
                                        day = int(date_parts[2])   # 02
                                        hour = int(time_parts[0])  # 22
                                        minute = int(time_parts[1])  # 33
                                        second = int(time_parts[2])  # 26

                                        # Napraw rok (025 -> 2025)
                                        if year < 100:
                                            year += 2000
                                        elif year < 1000:
                                            year += 1000

                                        parsed_time = datetime(
                                            year, month, day, hour, minute, second)
                                        change_time = timezone.make_aware(
                                            parsed_time)
                                        logger.info(
                                            f"Naprawiłem timestamp z 3-cyfrowego roku: {timestamp_part} -> {parsed_time}")
                                        break
                            except (ValueError, IndexError):
                                pass

                        for fmt in timestamp_formats:
                            try:
                                parsed_time = datetime.strptime(
                                    timestamp_part, fmt)

                                # Napraw rok jeśli użyto formatu 2-cyfrowego lub bez roku
                                if fmt == '%y-%m-%dT%H-%M-%S':
                                    # Konwertuj 2-cyfrowy rok na 4-cyfrowy (25 -> 2025)
                                    parsed_time = parsed_time.replace(
                                        year=2000 + parsed_time.year)
                                elif fmt == '%m-%dT%H-%M-%S':
                                    # Dodaj aktualny rok
                                    current_year = timezone.now().year
                                    parsed_time = parsed_time.replace(
                                        year=current_year)

                                # Traktuj jako czas lokalny i konwertuj na timezone-aware
                                change_time = timezone.make_aware(parsed_time)
                                logger.info(
                                    f"Parsuję timestamp z nazwy pliku: {timestamp_part} (format: {fmt})")
                                break

                            except ValueError:
                                continue

                        if change_time is None:
                            print(
                                f"DEBUG: Nie udało się sparsować timestamp z nazwy pliku: {timestamp_part}")
                            logger.warning(
                                f"Nie udało się sparsować timestamp z nazwy pliku: {timestamp_part}")
                            change_time = None

                    # Fallback: użyj created_at z bazy jeśli nie udało się sparsować nazwy pliku
                    if change_time is None:
                        print(f"DEBUG: Używam fallback - created_at z bazy")
                    if full_change_file.created_at:
                        if timezone.is_aware(full_change_file.created_at):
                            change_time = full_change_file.created_at
                        else:
                            change_time = timezone.make_aware(
                                full_change_file.created_at)
                            print(
                                f"DEBUG: Używam created_at z bazy: {full_change_file.created_at}")
                            logger.info(
                                f"Używam created_at z bazy: {full_change_file.created_at}")
                    else:
                        change_time = local_request_time
                        print(f"DEBUG: Brak created_at, używam request_time")
                        logger.warning(
                            "Brak timestamp w nazwie pliku i created_at, używam request_time")

                    # Konwertuj na lokalny czas
                    local_change_time = timezone.localtime(change_time)
                    change_time_str = local_change_time.strftime(
                        '%Y-%m-%d %H:%M:%S')
                    print(f"DEBUG: change_time_str = {change_time_str}")

                    # URL do konkretnego pliku full_changeYYYY-MM-DDThh-mm-ss.xml (zachowaj oryginalną nazwę UTC)
                    # Użyj bucket_url z bazy danych zamiast endpointu API
                    if full_change_file.bucket_url:
                        url = full_change_file.bucket_url
                    else:
                        # Fallback: URL do endpointu API jeśli brak bucket_url
                        # Użyj oryginalnej nazwy pliku z bazy (UTC)
                        url = f"{base_url}/mpd/{filename}"
                    print(f"DEBUG: url = {url}")
                    change_element.set("url", url)

                    # Hash bazujący na nazwie pliku full_change.xml
                    try:
                        # Hash bazujący na rzeczywistych zmianach w danych (ignoruje timestamp w pliku)
                        # Użyj timestamp ostatniej zmiany w produktach + liczba zmienionych produktów
                        from .models import Products
                        from datetime import timedelta
                        from django.db.models import Q
                        from django.utils import timezone

                        # Pobierz ostatni timestamp modyfikacji produktów
                        last_product_change = Products.objects.using('MPD').aggregate(
                            last_modified=models.Max('updated_at')
                        )['last_modified']

                        # Pobierz liczbę produktów zmienionych w ciągu ostatnich 30 minut (IOF 3.0)
                        thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
                        changed_products_count = Products.objects.using('MPD').filter(
                            Q(updated_at__gte=thirty_minutes_ago) |
                            Q(productvariants__updated_at__gte=thirty_minutes_ago) |
                            Q(productvariants__product__images__updated_at__gte=thirty_minutes_ago)
                        ).distinct().count()

                        if last_product_change:
                            last_change_str = last_product_change.strftime(
                                '%Y-%m-%dT%H-%M-%S')
                        else:
                            last_change_str = "1970-01-01T00-00-00"

                        # Hash bazujący na: ostatnia zmiana produktów + liczba zmienionych produktów + rozmiar pliku
                        file_size = full_change_file.file_size or 0
                        change_hash_input = f"full_change_data_{last_change_str}_{changed_products_count}_{file_size}"
                        hash_value = hashlib.md5(
                            change_hash_input.encode()).hexdigest()

                        logger.info(
                            f"Full_change.xml hash z danych: filename={full_change_file.filename}, last_change={last_change_str}, changed_count={changed_products_count}, size={file_size}")

                    except Exception as e:
                        # Fallback: hash bazujący na rozmiarze pliku i czasie utworzenia
                        file_size = full_change_file.file_size or 0
                        change_hash_input = f"full_change_fallback_{full_change_file.created_at.strftime('%Y-%m-%dT%H-%M-%S')}_{file_size}"
                        hash_value = hashlib.md5(
                            change_hash_input.encode()).hexdigest()
                        logger.warning(
                            f"Błąd generowania hash dla full_change.xml: {str(e)}, używam fallback")

                    change_element.set("hash", hash_value)
                    change_element.set("changed", change_time_str)

                    print(
                        f"DEBUG: Dodano element change do XML: url={url}, changed={change_time_str}")
                    logger.info(
                        f"API endpoint full_change: hash={hash_value}, changed={change_time_str}, filename={full_change_file.filename}")
                    logger.info(
                        f"Dodano element change do XML: url={url}, changed={change_time_str}")

                logger.info(
                    f"Wygenerowano {len(recent_full_change_files)} zmian w full_change.xml")

            else:
                # Brak plików full_change.xml w bazie - utwórz pusty change
                print("Brak plików full_change w bazie - tworzę pusty element change")
                logger.warning(
                    "Brak plików full_change w bazie - tworzę pusty element change")
                change_element = ET.SubElement(changes_element, "change")

                # URL do endpointu API dla full_change
                url = f"{base_url}/mpd/generate-full-change-xml/"
                change_element.set("url", url)
                change_element.set("hash", "")
                change_element.set("changed", "")

                logger.info(
                    "Brak plików full_change.xml w bazie - utworzono pusty change")

        except Exception as e:
            logger.error(
                f"Błąd podczas tworzenia węzła full z changes: {str(e)}")
            # Nie twórz dodatkowego węzła full - główny już istnieje
            # Tylko loguj błąd i kontynuuj

    def _create_light_element(self, root, base_url):
        """Tworzy węzeł light zgodnie ze schematem XSD"""
        light_element = ET.SubElement(root, "light")
        light_element.set("url", f"{base_url}/mpd/generate-light-xml/")
        logger.info("Light.xml: utworzono węzeł light bez hash i changed")

    def _create_categories_element(self, root, base_url):
        """Tworzy węzeł categories zgodnie ze schematem XSD"""
        from .models import FullChangeFile
        from django.utils import timezone

        categories_element = ET.SubElement(root, "categories")
        categories_element.set(
            "url", f"{base_url}/mpd/generate-categories-xml/")

        # Pobierz ostatni plik categories.xml z bazy
        try:
            latest_categories_file = FullChangeFile.objects.using('MPD').filter(
                filename='categories.xml'
            ).order_by('-created_at').first()

            if latest_categories_file:
                # Hash bazujący na nazwie pliku i czasie utworzenia
                hash_input = f"categories_xml_{latest_categories_file.created_at.strftime('%Y-%m-%dT%H-%M-%S')}"
                hash_value = hashlib.md5(hash_input.encode()).hexdigest()

                # Czas w formacie YYYY-MM-DD HH:MM:SS
                if timezone.is_aware(latest_categories_file.created_at):
                    categories_time = latest_categories_file.created_at
                else:
                    categories_time = timezone.make_aware(
                        latest_categories_file.created_at)

                local_categories_time = timezone.localtime(categories_time)
                categories_time_str = local_categories_time.strftime(
                    '%Y-%m-%d %H:%M:%S')

                categories_element.set("hash", hash_value)
                categories_element.set("changed", categories_time_str)
                logger.info(
                    f"Categories.xml: hash={hash_value}, changed={categories_time_str}")
            else:
                categories_element.set("hash", "")
                categories_element.set("changed", "")
                logger.info(
                    "Brak plików categories.xml w bazie - pusty hash i changed")
        except Exception as e:
            categories_element.set("hash", "")
            categories_element.set("changed", "")
            logger.warning(f"Błąd pobierania categories.xml z bazy: {str(e)}")

    def _create_sizes_element(self, root, base_url):
        """Tworzy węzeł sizes zgodnie ze schematem XSD"""
        from .models import FullChangeFile
        from django.utils import timezone

        sizes_element = ET.SubElement(root, "sizes")
        sizes_element.set("url", f"{base_url}/mpd/generate-sizes-xml/")

        # Pobierz ostatni plik sizes.xml z bazy
        try:
            latest_sizes_file = FullChangeFile.objects.using('MPD').filter(
                filename='sizes.xml'
            ).order_by('-created_at').first()

            if latest_sizes_file:
                # Hash bazujący na nazwie pliku i czasie utworzenia
                hash_input = f"sizes_xml_{latest_sizes_file.created_at.strftime('%Y-%m-%dT%H-%M-%S')}"
                hash_value = hashlib.md5(hash_input.encode()).hexdigest()

                # Czas w formacie YYYY-MM-DD HH:MM:SS
                if timezone.is_aware(latest_sizes_file.created_at):
                    sizes_time = latest_sizes_file.created_at
                else:
                    sizes_time = timezone.make_aware(
                        latest_sizes_file.created_at)

                local_sizes_time = timezone.localtime(sizes_time)
                sizes_time_str = local_sizes_time.strftime(
                    '%Y-%m-%d %H:%M:%S')

                sizes_element.set("hash", hash_value)
                sizes_element.set("changed", sizes_time_str)
                logger.info(
                    f"Sizes.xml: hash={hash_value}, changed={sizes_time_str}")
            else:
                sizes_element.set("hash", "")
                sizes_element.set("changed", "")
                logger.info(
                    "Brak plików sizes.xml w bazie - pusty hash i changed")
        except Exception as e:
            sizes_element.set("hash", "")
            sizes_element.set("changed", "")
            logger.error(f"Błąd podczas pobierania sizes.xml: {str(e)}")

    def _create_producers_element(self, root, base_url):
        """Tworzy węzeł producers zgodnie ze schematem XSD"""
        from .models import FullChangeFile
        from django.utils import timezone

        producers_element = ET.SubElement(root, "producers")
        producers_element.set(
            "url", f"{base_url}/mpd/generate-producers-xml/")

        # Pobierz ostatni plik producers.xml z bazy
        try:
            latest_producers_file = FullChangeFile.objects.using('MPD').filter(
                filename='producers.xml'
            ).order_by('-created_at').first()

            if latest_producers_file:
                # Hash bazujący na nazwie pliku i czasie utworzenia
                hash_input = f"producers_xml_{latest_producers_file.created_at.strftime('%Y-%m-%dT%H-%M-%S')}"
                hash_value = hashlib.md5(hash_input.encode()).hexdigest()

                # Czas w formacie YYYY-MM-DD HH:MM:SS
                if timezone.is_aware(latest_producers_file.created_at):
                    producers_time = latest_producers_file.created_at
                else:
                    producers_time = timezone.make_aware(
                        latest_producers_file.created_at)

                local_producers_time = timezone.localtime(producers_time)
                producers_time_str = local_producers_time.strftime(
                    '%Y-%m-%d %H:%M:%S')

                producers_element.set("hash", hash_value)
                producers_element.set("changed", producers_time_str)
                logger.info(
                    f"Producers.xml: hash={hash_value}, changed={producers_time_str}")
            else:
                producers_element.set("hash", "")
                producers_element.set("changed", "")
                logger.info(
                    "Brak plików producers.xml w bazie - pusty hash i changed")
        except Exception as e:
            producers_element.set("hash", "")
            producers_element.set("changed", "")
            logger.warning(f"Błąd pobierania producers.xml z bazy: {str(e)}")

    def generate_xml(self, request_time=None):
        print("=== ROZPOCZYNAM GatewayXMLExporter.generate_xml ===")
        logger.info("=== ROZPOCZYNAM GatewayXMLExporter.generate_xml ===")
        root = ET.Element("provider_description")
        root.set("file_format", "IOF")
        root.set("version", "3.0")
        root.set("generated_by", "nc")

        # Użyj czasu żądania HTTP lub aktualnego czasu
        if request_time is None:
            request_time = timezone.now()

        # Konwertuj na lokalny czas (Europe/Warsaw)
        local_request_time = timezone.localtime(request_time)
        root.set("generated", local_request_time.strftime("%Y-%m-%d %H:%M:%S"))

        # Pobierz full_time z bazy danych, aby przekazać go do _create_meta_element
        from .models import FullChangeFile
        last_full_file = FullChangeFile.objects.using('MPD').filter(
            filename='full.xml'
        ).order_by('-created_at').first()

        full_time = ""
        if last_full_file:
            full_time = timezone.localtime(
                last_full_file.created_at).strftime('%Y-%m-%d %H:%M:%S')

        self._create_meta_element(root, request_time, full_time)
        self._create_url_elements(root, request_time, full_time)
        xmlstr = minidom.parseString(
            ET.tostring(root, encoding="utf-8")
        ).toprettyxml(indent="  ", encoding="utf-8")
        return xmlstr.decode("utf-8")


class ProducersXMLExporter(BaseXMLExporter):
    def __init__(self):
        super().__init__('producers.xml')

    def generate_xml(self):
        from django.utils.html import escape
        from .models import Brands
        from datetime import timedelta
        now = timezone.now()
        # Konwertuj na czas lokalny (Europe/Warsaw)
        local_now = timezone.localtime(now)
        local_expires = local_now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<producers file_format="IOF" version="3.0" generated_by="nc" language="pol" generated="{}" expires="{}">'.format(
            local_now.strftime('%Y-%m-%d %H:%M:%S'), local_expires.strftime('%Y-%m-%d %H:%M:%S')))
        brands = Brands.objects.using('MPD').filter(iai_brand_id__isnull=False)
        for brand in brands:
            # id: string, bez spacji, tylko a-z, A-Z, _, -
            brand_id = str(brand.iai_brand_id)
            brand_id = brand_id.replace(' ', '_')
            name = escape(brand.name) if brand.name else ''
            xml.append(f'  <producer id="{brand_id}" name="{name}"/>')
        xml.append('</producers>')
        return '\n'.join(xml)

    def export(self):
        xml_content = self.generate_xml()
        local_path = self.save_local(xml_content)

        # Zapisz rekord do bazy danych
        from .models import FullChangeFile

        producers_file = FullChangeFile.objects.using('MPD').create(
            filename='producers.xml',
            timestamp=timezone.localtime(
                timezone.now()).strftime('%Y-%m-%dT%H-%M-%S'),
            local_path=local_path,
            file_size=0,  # Zostanie zaktualizowane po zapisie
        )

        # Zaktualizuj rozmiar pliku
        if os.path.exists(local_path):
            producers_file.file_size = os.path.getsize(local_path)
            producers_file.save(using='MPD')

        bucket_url = self.save_to_bucket(local_path)
        if bucket_url:
            print('✅ Eksport XML zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
        else:
            print('❌ Błąd podczas eksportu XML')
            print(f'📄 Lokalnie zapisano: {local_path}')
        return {'bucket_url': bucket_url, 'local_path': local_path}


class StocksXMLExporter(BaseXMLExporter):
    def __init__(self):
        super().__init__('stocks.xml')

    def generate_xml(self):
        from django.utils.html import escape
        from .models import StockAndPrices
        from datetime import timedelta
        now = timezone.now()
        # Konwertuj na czas lokalny (Europe/Warsaw)
        local_now = timezone.localtime(now)
        local_expires = local_now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<stocks file_format="IOF" version="3.0" generated_by="nc" language="pol" generated="{}" expires="{}">'.format(
            local_now.strftime('%Y-%m-%d %H:%M:%S'), local_expires.strftime('%Y-%m-%d %H:%M:%S')))
        stocks = StockAndPrices.objects.using(
            'MPD').all().select_related('variant__product')
        for stock in stocks:
            variant = stock.variant
            product = variant.product if variant else None
            stock_id = str(variant.variant_id) if variant else ''
            stock_id = stock_id.replace(' ', '_')
            name = escape(product.name) if product and product.name else ''
            xml.append(f'  <stock id="{stock_id}" name="{name}"/>')
        xml.append('</stocks>')
        return '\n'.join(xml)


class CategoriesXMLExporter(BaseXMLExporter):
    def __init__(self):
        super().__init__('categories.xml')

    def export(self):
        xml_content = self.generate_xml()
        local_path = self.save_local(xml_content)

        # Zapisz rekord do bazy danych
        from .models import FullChangeFile

        categories_file = FullChangeFile.objects.using('MPD').create(
            filename='categories.xml',
            timestamp=timezone.localtime(
                timezone.now()).strftime('%Y-%m-%dT%H-%M-%S'),
            local_path=local_path,
            file_size=0,  # Zostanie zaktualizowane po zapisie

        )

        # Zaktualizuj rozmiar pliku
        if os.path.exists(local_path):
            categories_file.file_size = os.path.getsize(local_path)
            categories_file.save(using='MPD')

        bucket_url = self.save_to_bucket(local_path)
        if bucket_url:
            print('✅ Eksport XML zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
        else:
            print('❌ Błąd podczas eksportu XML')
            print(f'📄 Lokalnie zapisano: {local_path}')
        return {'bucket_url': bucket_url, 'local_path': local_path}

    def generate_xml(self):
        from django.utils.html import escape
        from .models import Paths
        from datetime import timedelta

        now = timezone.now()
        # Konwertuj na czas lokalny (Europe/Warsaw)
        local_now = timezone.localtime(now)
        local_expires = local_now + timedelta(days=1)

        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<categories file_format="IOF" version="3.0" generated_by="nc" language="pol" generated="{}" expires="{}">'.format(
            local_now.strftime('%Y-%m-%d %H:%M:%S'), local_expires.strftime('%Y-%m-%d %H:%M:%S')))

        # Pobierz wszystkie ścieżki (kategorie) z bazy
        paths = Paths.objects.using('MPD').all().order_by('id')

        # Grupuj ścieżki według poziomów hierarchii
        categories_tree = {}
        for path in paths:
            if path.path:
                # Podziel ścieżkę na części (np. "Moda damska\Bielizna" -> ["Moda damska", "Bielizna"])
                path_parts = path.path.split('\\')

                # Buduj hierarchię
                current_level = categories_tree
                for i, part in enumerate(path_parts):
                    if part not in current_level:
                        current_level[part] = {
                            'id': path.iai_category_id if path.iai_category_id else path.id if i == len(path_parts) - 1 else None,
                            'children': {},
                            'full_path': '\\'.join(path_parts[:i + 1])
                        }
                    current_level = current_level[part]['children']

        # Generuj XML z hierarchii używając parent_id
        # Rekurencyjnie generuj XML z hierarchii
        def generate_category_tree(parent_id=None, level=1):
            xml_lines = []
            indent = '  ' * level

            # Znajdź dzieci dla danego parent_id
            children = [path for path in paths if path.parent_id == parent_id]

            for child in children:
                # Użyj iai_category_id zamiast id, jeśli jest dostępny
                category_id = child.iai_category_id if child.iai_category_id else child.id

                if child.parent_id is None:
                    # To jest kategoria główna
                    xml_lines.append(f'{indent}<category id="{category_id}">')
                    xml_lines.append(
                        f'{indent}  <name xml:lang="pol">{escape(child.name)}</name>')

                    # Rekurencyjnie generuj podkategorie
                    sub_xml = generate_category_tree(child.id, level + 1)
                    if sub_xml:
                        xml_lines.extend(sub_xml)

                    xml_lines.append(f'{indent}</category>')
                else:
                    # To jest podkategoria
                    xml_lines.append(f'{indent}<category id="{category_id}">')
                    xml_lines.append(
                        f'{indent}  <name xml:lang="pol">{escape(child.name)}</name>')

                    # Rekurencyjnie generuj podkategorie
                    sub_xml = generate_category_tree(child.id, level + 1)
                    if sub_xml:
                        xml_lines.extend(sub_xml)

                    xml_lines.append(f'{indent}</category>')

            return xml_lines

        # Generuj XML z hierarchii
        xml.extend(generate_category_tree())

        xml.append('</categories>')
        return '\n'.join(xml)


class UnitsXMLExporter(BaseXMLExporter):
    def __init__(self):
        super().__init__('units.xml')

    def generate_xml(self):
        from django.utils.html import escape
        from .models import Units
        from datetime import timedelta
        now = timezone.now()
        # Konwertuj na czas lokalny (Europe/Warsaw)
        local_now = timezone.localtime(now)
        local_expires = local_now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<units file_format="IOF" version="3.0" generated="{}" expires="{}" language="pol">'.format(
            local_now.strftime('%Y-%m-%d %H:%M:%S'), local_expires.strftime('%Y-%m-%d %H:%M:%S')))
        units = Units.objects.using('MPD').all()
        for unit in units:
            xml.append(
                f'  <unit id="{unit.unit_id}" name="{escape(unit.name) if unit.name else ''}"/>')
        xml.append('</units>')
        return '\n'.join(xml)


class FullChangeXMLExporter(BaseXMLExporter):
    def __init__(self):
        # Generuj nazwę pliku z aktualną datą w czasie lokalnym
        now = timezone.now()
        local_now = timezone.localtime(now)
        timestamp = local_now.strftime('%Y-%m-%dT%H-%M-%S')
        filename = f'full_change{timestamp}.xml'
        super().__init__(filename)
        self.timestamp = timestamp
        self.created_at = now  # Zachowaj oryginalny czas UTC w bazie

    def save_full_change_record(self, bucket_url, local_path):
        """Zapisz rekord o wygenerowanym pliku full_change"""
        from .models import FullChangeFile
        try:
            FullChangeFile.objects.using('MPD').create(
                filename=self.filename,
                timestamp=self.timestamp,
                created_at=self.created_at,
                bucket_url=bucket_url,
                local_path=local_path,
                file_size=os.path.getsize(
                    local_path) if os.path.exists(local_path) else 0
            )
            logger.info(f"Zapisano rekord pliku full_change: {self.filename}")
        except Exception as e:
            logger.error(
                f"Błąd podczas zapisywania rekordu full_change: {str(e)}")

    def export(self):
        """Przesłonięta metoda export aby zapisać rekord pliku"""
        xml_content = self.generate_xml()
        local_path = self.save_local(xml_content)
        bucket_url = self.save_to_bucket(local_path)

        # Zapisz rekord o wygenerowanym pliku
        self.save_full_change_record(bucket_url, local_path)

        if bucket_url:
            print('✅ Eksport XML zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
        else:
            print('❌ Błąd podczas eksportu XML')
            print(f'📄 Lokalnie zapisano: {local_path}')
        return {'bucket_url': bucket_url, 'local_path': local_path}

    def generate_navigation_xml(self, product_id):
        from .models import Paths, ProductPaths
        from django.utils.html import escape
        xml = []
        xml.append('      <iaiext:navigation>')
        xml.append('        <iaiext:site id="1">')
        xml.append('          <iaiext:menu id="1">')
        product_paths = ProductPaths.objects.using(
            'MPD').filter(product_id=product_id)
        path_ids = set(pp.path_id for pp in product_paths)
        paths = list(Paths.objects.using('MPD').filter(
            id__in=path_ids).order_by('id'))
        for idx, path in enumerate(paths, 1):
            textid = escape(path.path) if path.path else ''
            # Użyj iai_menu_id zamiast id dla węzła iaiext:item
            item_id = path.iai_menu_id if path.iai_menu_id else path.id
            xml.append(
                f'            <iaiext:item id="{item_id}" menu_id="1" textid="{textid}" iaiext:priority_menu="{idx}"/>')
        xml.append('          </iaiext:menu>')
        xml.append('        </iaiext:site>')
        xml.append('      </iaiext:navigation>')
        return '\n'.join(xml)

    def generate_xml(self, incremental=True):
        from django.utils.html import escape
        from .models import ProductVariants, ProductImage, StockAndPrices, ProductVariantsRetailPrice, ProductPaths, Paths
        from datetime import timedelta
        from django.db.models import Q
        from .models import Vat

        now = timezone.now()
        # Konwertuj na czas lokalny (Europe/Warsaw)
        local_now = timezone.localtime(now)
        local_expires = local_now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<offer file_format="IOF" version="3.0" generated="{}" expires="{}" extensions="yes" xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml">'.format(
            local_now.strftime('%Y-%m-%d %H:%M:%S'), local_expires.strftime('%Y-%m-%d %H:%M:%S')))
        xml.append('  <products language="pol">')

        # Tracking nie jest używane w nowej logice IOF 3.0 (30 minut dla wszystkich produktów)

        # Oblicz timestamp z 30 minut temu (specyfikacja IOF 3.0)
        thirty_minutes_ago = now - timedelta(minutes=30)

        if incremental:
            # Eksport przyrostowy - tylko produkty zmienione w ciągu ostatnich 30 minut (IOF 3.0)
            # Sprawdź zmiany w wariantach, produktach i obrazach - WSZYSTKIE produkty
            variants_with_iai = ProductVariants.objects.using('MPD').filter(
                iai_product_id__isnull=False
            ).filter(
                Q(updated_at__gte=thirty_minutes_ago) |  # Wariant zmieniony
                # Produkt zmieniony
                Q(product__updated_at__gte=thirty_minutes_ago) |
                # Obraz zmieniony
                Q(product__images__updated_at__gte=thirty_minutes_ago)
            ).select_related('product', 'size', 'color', 'producer_color', 'product__brand').distinct()

            logger.info(
                f"Eksport przyrostowy full_change.xml (IOF 3.0) - produkty zmienione od: {thirty_minutes_ago.strftime('%Y-%m-%d %H:%M:%S')} (zgodnie z IOF 3.0)")
        else:
            # Pełny eksport - wszystkie produkty
            variants_with_iai = ProductVariants.objects.using('MPD').filter(
                iai_product_id__isnull=False
            ).select_related('product', 'size', 'color', 'producer_color', 'product__brand')
            logger.info("Pełny eksport full_change.xml - wszystkie produkty")

        # Grupuj warianty po iai_product_id
        grouped_variants = {}
        for variant in variants_with_iai:
            iai_id = variant.iai_product_id
            if iai_id not in grouped_variants:
                grouped_variants[iai_id] = []
            grouped_variants[iai_id].append(variant)

        # Iteruj po unikalnych iai_product_id
        for iai_product_id, variants in grouped_variants.items():
            if not variants:
                continue

            # Pobierz pierwszy wariant do uzyskania danych produktu
            first_variant = variants[0]
            product = first_variant.product

            # Pobierz dane waluty i VAT z pierwszego wariantu
            currency = '' or 'PLN'
            vat_rate = ''
            has_price = False
            for variant in variants:
                pvrp = ProductVariantsRetailPrice.objects.using(
                    'MPD').filter(variant=variant).first()
                if pvrp:
                    currency = pvrp.currency or 'PLN'
                    if pvrp.vat:
                        vat_obj = Vat.objects.using(
                            'MPD').filter(id=pvrp.vat).first()
                        if vat_obj:
                            vat_rate = str(vat_obj.vat_rate)
                        else:
                            vat_rate = str(pvrp.vat)
                    has_price = True
                    break

            # Jeśli nie ma ceny, ustaw VAT na 0
            if not has_price:
                vat_rate = '0'

            xml.append(
                f'    <product id="{iai_product_id}" currency="{currency}" type="regular" vat="{vat_rate}" site="1">')

            if product.brand:
                xml.append(
                    f'      <producer id="{product.brand.iai_brand_id}" name="{escape(product.brand.name) if product.brand.name else ""}"/>')

            # Dodaj węzeł deliverer
            xml.append('      <iaiext:deliverer id="1" name="Matterhorn"/>')

            # Dodaj węzeł date_created z kolumny created_at
            if product.created_at:
                # Konwertuj na czas lokalny (Europe/Warsaw)
                local_created_at = timezone.localtime(product.created_at)
                xml.append(
                    f'      <iaiext:date_created datetime="{local_created_at.strftime("%Y-%m-%d %H:%M:%S")}"/>')

            # Dodaj węzeł modification_date z kolumny updated_at
            if product.updated_at:
                # Konwertuj na czas lokalny (Europe/Warsaw)
                local_updated_at = timezone.localtime(product.updated_at)
                xml.append(
                    f'      <iaiext:modification_date datetime="{local_updated_at.strftime("%Y-%m-%d %H:%M:%S")}"/>')

            # Dodaj wszystkie kategorie (category) powiązane z produktem
            product_paths = ProductPaths.objects.using(
                'MPD').filter(product_id=product.id)
            for product_path in product_paths:
                path_obj = Paths.objects.using('MPD').filter(
                    id=product_path.path_id).first()
                if path_obj:
                    # Użyj iai_category_id zamiast id, jeśli jest dostępny
                    category_id = path_obj.iai_category_id if path_obj.iai_category_id else path_obj.id
                    xml.append(
                        f'      <category id="{category_id}" name="{escape(path_obj.path)}"/>')

            # Dodaj jednostkę, jeśli jest przypisana
            if product.unit:
                xml.append(
                    f'      <unit id="{product.unit.unit_id}" name="{escape(product.unit.name) if product.unit.name else ""}"/>')

            if product.name:
                xml.append('      <description>')
                xml.append(f'        <name>{escape(product.name)}</name>')
                if product.short_description:
                    xml.append(
                        f'        <short_desc><![CDATA[{product.short_description}]]></short_desc>')
                if product.description:
                    xml.append(
                        f'        <long_desc><![CDATA[{product.description}]]></long_desc>')

                xml.append('      </description>')

            # Dodaj parametry produktu (kolor dla tego wariantu)
            if first_variant.color:
                xml.append('      <parameters>')
                xml.append(
                    '        <parameter type="parameter" id="26" name="Kolor">')
                xml.append(
                    f'          <value id="{first_variant.color.iai_colors_id}" name="{escape(first_variant.color.name)}"/>')
                xml.append('        </parameter>')
                xml.append('      </parameters>')

            # Dodaj cenę na poziomie produktu (pierwsza cena z pierwszego wariantu)
            first_stock_price = StockAndPrices.objects.using(
                'MPD').filter(variant=first_variant).first()
            if first_stock_price:
                retail_price_obj = ProductVariantsRetailPrice.objects.using(
                    'MPD').filter(variant=first_variant).first()
                if retail_price_obj:
                    gross = retail_price_obj.retail_price if hasattr(
                        retail_price_obj, 'retail_price') else ''
                    net = retail_price_obj.net_price if hasattr(
                        retail_price_obj, 'net_price') else ''
                    price_attrs = []
                    if gross or net:
                        if gross:
                            price_attrs.append(f'gross="{gross}"')
                        if net:
                            price_attrs.append(f'net="{net}"')
                    if price_attrs:
                        xml.append(f'      <price {" ".join(price_attrs)}/>')
                    else:
                        # Brak ceny w bazie - dodaj cenę 0 jako fallback
                        # Zgodnie z dokumentacją full.md, @net jest wymagany
                        xml.append('      <price gross="0" net="0"/>')

            # Użyj kolumny visibility z tabeli products
            xml.append('      <iaiext:visibility>')
            if product.visibility:
                xml.append('        <iaiext:site visible="yes"/>')
            else:
                xml.append('        <iaiext:site visible="no"/>')
            xml.append('      </iaiext:visibility>')

            # Dodaj sekcję nawigacyjną dla tego produktu
            xml.append(self.generate_navigation_xml(product.id))

            # Pobierz group_name z category pierwszego rozmiaru
            group_name = ''
            for variant in variants:
                if variant.size and variant.size.category:
                    group_name = variant.size.category
                    break

            if variants:
                xml.append(
                    f'      <sizes iaiext:group_name="{group_name}" iaiext:group_id="1098261181" iaiext:sizeList="full">')
                for variant in variants:
                    size_name = variant.size.name if variant.size else ""
                    # panel_name: size_name + '_' + group_name
                    panel_name = f'{size_name}_{group_name}' if size_name and group_name else size_name or group_name
                    # code_external: product_id-variant_id (variant_id jest unikalny dla każdego wariantu)
                    code_external = f'{product.id}-{variant.variant_id}'
                    # code_producer: z tabeli product_variants_sources (ean, gtin14, gtin13, other)
                    from .models import ProductvariantsSources
                    variant_source = ProductvariantsSources.objects.using(
                        'MPD').filter(variant=variant).first()
                    code_producer = ''
                    if variant_source:
                        # Sprawdź kolejno: ean, gtin14, gtin13, other
                        if variant_source.ean:
                            code_producer = variant_source.ean
                        elif variant_source.gtin14:
                            code_producer = variant_source.gtin14
                        elif variant_source.gtin13:
                            code_producer = variant_source.gtin13
                        elif variant_source.other:
                            code_producer = variant_source.other

                    # Buduj atrybuty do węzła <size>
                    size_id = variant.size.iai_size_id if variant.size and variant.size.iai_size_id else ''
                    # Dodaj wymagany atrybut @code w formacie iai_product_id-size_id
                    code_value = f"{iai_product_id}-{size_id}" if size_id else f"{iai_product_id}"
                    size_attrs = [
                        f'id="{size_id}"',
                        f'code="{escape(code_value)}"',
                        f'name="{escape(size_name)}"',
                        f'panel_name="{escape(panel_name)}"',
                        f'iaiext:code_external="{code_external}"'
                    ]
                    # Dodaj wymagany atrybut @code zgodnie ze schematem XSD
                    if code_producer:
                        size_attrs.append(
                            f'code_producer="{escape(code_producer)}"')
                    xml.append(
                        f'        <size {' '.join(size_attrs)}>'
                    )
                    stock_price = StockAndPrices.objects.using(
                        'MPD').filter(variant=variant).first()
                    if stock_price:
                        # Pobierz ceny detaliczne z product_variants_retail_price
                        retail_price_obj = None
                        try:
                            from .models import ProductVariantsRetailPrice
                            retail_price_obj = ProductVariantsRetailPrice.objects.using(
                                'MPD').filter(variant=variant).first()
                        except Exception:
                            pass
                        gross = retail_price_obj.retail_price if retail_price_obj and hasattr(
                            retail_price_obj, 'retail_price') else ''
                        net = retail_price_obj.net_price if retail_price_obj and hasattr(
                            retail_price_obj, 'net_price') else ''
                        price_attrs = []
                        if gross or net:
                            if gross:
                                price_attrs.append(f'gross="{gross}"')
                            if net:
                                price_attrs.append(f'net="{net}"')

                        if price_attrs:
                            xml.append(
                                f'          <price {" ".join(price_attrs)}/>')
                        else:
                            # Brak ceny w bazie - dodaj cenę 0 jako fallback (jak w light.xml)
                            # Zgodnie z dokumentacją full.md, @net jest wymagany
                            xml.append('          <price gross="0" net="0"/>')
                        source = Sources.objects.filter(
                            id=stock_price.source.id).first() if stock_price and stock_price.source else None
                        stock_id = ""
                        if source and hasattr(source, 'type'):
                            if source.type == 'Magazyn główny':
                                stock_id = "1"
                            elif source.type == 'Magazyn obcy':
                                stock_id = "0"
                            elif source.type == 'Magazyn wymiany':
                                stock_id = "3"
                            elif source.type == 'Magazyn pomocniczy':
                                stock_id = "2"
                        xml.append(
                            f'          <stock id="{stock_id}" quantity="{stock_price.stock}"/>')
                    xml.append('        </size>')
                xml.append('      </sizes>')

            # Dodaj obrazy produktu (obrazy przypisane do tego iai_product_id)
            images = ProductImage.objects.using('MPD').filter(
                product=product,
                iai_product_id=iai_product_id
            )
            if images:
                xml.append('      <images>')
                xml.append('        <large>')
                for img in images:
                    xml.append(
                        f'          <image url="{escape(img.file_path)}"/>')
                xml.append('        </large>')
                xml.append('      </images>')

            xml.append('    </product>')

        xml.append('  </products>')
        xml.append('</offer>')
        return '\n'.join(xml)


def refresh_gateway_after_export():
    """
    Funkcja pomocnicza do odświeżania gateway.xml po eksporcie innych plików XML.
    Może być wywoływana ręcznie lub automatycznie po eksporcie.
    """
    try:
        gateway_exporter = GatewayXMLExporter()
        result = gateway_exporter.export()
        if result['bucket_url']:
            print('✅ Gateway.xml odświeżony pomyślnie!')
            print(f'📁 URL: {result["bucket_url"]}')
            print(f'📄 Lokalnie zapisano: {result["local_path"]}')
            return True
        else:
            print('❌ Błąd podczas odświeżania gateway.xml')
            return False
    except Exception as e:
        print(f'❌ Błąd podczas odświeżania gateway.xml: {str(e)}')
        return False


# Funkcje eksportu dla łatwego użycia
def export_full_xml():
    """Eksport pełny wszystkich produktów do full.xml"""
    exporter = FullXMLExporter()
    return exporter.export_full()


def export_incremental_xml():
    """Eksport pełnej oferty do full.xml (dawniej przyrostowy)"""
    exporter = FullXMLExporter()
    return exporter.export_incremental()


def export_full_change_xml():
    """Eksport pełny wszystkich produktów do full_change.xml z datą w nazwie"""
    exporter = FullChangeXMLExporter()
    result = exporter.export()
    return result.get('bucket_url', '') if result else ''


def export_incremental_full_change_xml():
    """Eksport przyrostowy zmienionych produktów do full_change.xml z datą w nazwie"""
    exporter = FullChangeXMLExporter()
    result = exporter.export()
    return result.get('bucket_url', '') if result else ''


def export_light_xml():
    """Eksport przyrostowy zmienionych produktów do light.xml"""
    exporter = LightXMLExporter()
    return exporter.export_incremental()


def export_gateway_xml():
    """Eksport gateway.xml"""
    exporter = GatewayXMLExporter()
    return exporter.export()


def export_all_xml():
    """Eksport wszystkich plików XML"""
    print("🚀 Rozpoczynam eksport wszystkich plików XML...")

    # Eksport full.xml
    print("\n📦 Eksport full.xml...")
    full_result = export_full_xml()

    # Eksport full_change.xml
    print("\n📦 Eksport full_change.xml...")
    full_change_result = export_full_change_xml()

    # Eksport light.xml
    print("\n📦 Eksport light.xml...")
    light_result = export_light_xml()

    # Eksport pozostałych plików
    print("\n📦 Eksport pozostałych plików...")
    producers_result = ProducersXMLExporter().export()
    stocks_result = StocksXMLExporter().export()
    units_result = UnitsXMLExporter().export()

    # Ostatni eksport gateway.xml (zaktualizuje wszystkie hashe i węzeł changes)
    print("\n📦 Eksport gateway.xml...")
    gateway_result = export_gateway_xml()

    print("\n🎉 Eksport wszystkich plików XML zakończony!")
    return {
        'full': full_result,
        'full_change': full_change_result,
        'light': light_result,
        'producers': producers_result,
        'stocks': stocks_result,
        'units': units_result,
        'gateway': gateway_result
    }


def test_gateway_refresh():
    """Funkcja testowa do sprawdzenia odświeżania gateway.xml"""
    print("🧪 Test odświeżania gateway.xml...")

    # Sprawdź aktualny stan plików lokalnych
    local_dir = 'MPD_test/xml/matterhorn/'
    full_path = os.path.join(local_dir, 'full.xml')

    if os.path.exists(full_path):
        mtime = os.path.getmtime(full_path)
        changed_dt = datetime.fromtimestamp(mtime)
        print(
            f"📄 full.xml - ostatnia modyfikacja: {changed_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        # Oblicz hash
        import hashlib
        with open(full_path, 'rb') as f:
            file_content = f.read()
            hash_value = hashlib.md5(file_content).hexdigest()
        print(f"🔐 full.xml - hash: {hash_value}")
    else:
        print("❌ Plik full.xml nie istnieje lokalnie")

    # Odśwież gateway.xml
    print("\n🔄 Odświeżam gateway.xml...")
    success = refresh_gateway_after_export()

    if success:
        print("✅ Test zakończony pomyślnie!")
    else:
        print("❌ Test nie powiódł się!")

    return success


def refresh_gateway_simple():
    """
    Prosta funkcja do odświeżenia gateway.xml bez bazy danych.
    Tylko odczytuje pliki lokalne i aktualizuje hash/changed.
    """
    try:
        print("🔄 Odświeżam gateway.xml (prosta metoda)...")

        # Sprawdź pliki lokalne
        local_dir = 'MPD_test/xml/matterhorn/'
        full_path = os.path.join(local_dir, 'full.xml')

        if not os.path.exists(full_path):
            print("❌ Plik full.xml nie istnieje lokalnie")
            return False

        # Oblicz nowy hash i datę dla full.xml
        import hashlib
        with open(full_path, 'rb') as f:
            file_content = f.read()
            new_hash = hashlib.md5(file_content).hexdigest()

        mtime = os.path.getmtime(full_path)
        new_changed = datetime.fromtimestamp(
            mtime).strftime('%Y-%m-%d %H:%M:%S')

        print(f"📄 full.xml - hash: {new_hash}, changed: {new_changed}")

        # Odczytaj aktualny gateway.xml
        gateway_path = os.path.join(local_dir, 'gateway.xml')
        if not os.path.exists(gateway_path):
            print("❌ Plik gateway.xml nie istnieje lokalnie")
            return False

        # Zaktualizuj gateway.xml
        import xml.etree.ElementTree as ET
        tree = ET.parse(gateway_path)
        root = tree.getroot()

        # Znajdź element <full> i zaktualizuj jego atrybuty
        for full_elem in root.findall('full'):
            old_hash = full_elem.get('hash', '')
            old_changed = full_elem.get('changed', '')

            full_elem.set('hash', new_hash)
            full_elem.set('changed', new_changed)

            print(f"🔄 Zaktualizowano: hash '{old_hash}' -> '{new_hash}'")
            print(
                f"🔄 Zaktualizowano: changed '{old_changed}' -> '{new_changed}'")

            # Zaktualizuj również timestamp w głównym elemencie
            root.set('generated', new_changed)
            print(f"🔄 Zaktualizowano: generated -> '{new_changed}'")
            break

        # Zapisz zaktualizowany plik
        tree.write(gateway_path, encoding='utf-8', xml_declaration=True)
        print(f"✅ Gateway.xml zaktualizowany i zapisany: {gateway_path}")

        return True

    except Exception as e:
        print(f"❌ Błąd podczas odświeżania gateway.xml: {str(e)}")
        return False


class SizesXMLExporter(BaseXMLExporter):
    """Eksporter dla pliku sizes.xml zgodnie ze schematem sizes.xsd"""

    def __init__(self):
        super().__init__('sizes.xml')

    def export(self):
        xml_content = self.generate_xml()
        local_path = self.save_local(xml_content)

        # Zapisz rekord do bazy danych
        from .models import FullChangeFile

        sizes_file = FullChangeFile.objects.using('MPD').create(
            filename='sizes.xml',
            timestamp=timezone.localtime(
                timezone.now()).strftime('%Y-%m-%dT%H-%M-%S'),
            local_path=local_path,
            file_size=0,  # Zostanie zaktualizowane po zapisie
        )

        # Zaktualizuj rozmiar pliku
        if os.path.exists(local_path):
            sizes_file.file_size = os.path.getsize(local_path)
            sizes_file.save(using='MPD')

        bucket_url = self.save_to_bucket(local_path)
        if bucket_url:
            print('✅ Eksport XML zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
        else:
            print('❌ Błąd podczas eksportu XML')
            print(f'📄 Lokalnie zapisano: {local_path}')
        return {'bucket_url': bucket_url, 'local_path': local_path}

    def generate_xml(self):
        from django.utils.html import escape
        from .models import Sizes

        now = timezone.now()
        # Konwertuj na czas lokalny (Europe/Warsaw)
        local_now = timezone.localtime(now)

        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<sizes file_format="IOF" version="3.0" language="pol" generated="{}">'.format(
            local_now.strftime('%Y-%m-%d %H:%M:%S')))

        # Pobierz wszystkie unikalne rozmiary z tabeli Sizes
        sizes = Sizes.objects.using('MPD').filter(
            category__isnull=False,
            name__isnull=False
        ).order_by('category', 'name')

        # Grupuj rozmiary według kategorii
        current_category = None
        for size in sizes:
            if size.category != current_category:
                # Zamknij poprzednią grupę jeśli istnieje
                if current_category is not None:
                    xml.append('  </group>')

                # Otwórz nową grupę
                current_category = size.category
                xml.append(
                    f'  <group id="1098261181" name="{escape(current_category)}">')

            # Użyj iai_size_id zamiast id, jeśli jest dostępny
            size_id = size.iai_size_id if size.iai_size_id else size.id
            size_name = size.name

            xml.append(
                f'    <size id="{size_id}" name="{escape(size_name)}">')
            xml.append(
                f'      <name xml:lang="pol">{escape(size_name)}</name>')
            xml.append('    </size>')

        # Zamknij ostatnią grupę
        if current_category is not None:
            xml.append('  </group>')

        xml.append('</sizes>')

        return '\n'.join(xml)
