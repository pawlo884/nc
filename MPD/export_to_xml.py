import os
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
            xml.append(
                f'            <iaiext:item id="{path.id}" menu_id="1" textid="{textid}" iaiext:priority_menu="{idx}"/>')
        xml.append('          </iaiext:menu>')
        xml.append('        </iaiext:site>')
        xml.append('      </iaiext:navigation>')
        return '\n'.join(xml)

    def get_or_create_tracking(self):
        """Pobierz lub utwórz tracking dla full.xml"""
        from .models import ExportTracking
        tracking, created = ExportTracking.objects.using('MPD').get_or_create(
            export_type='full.xml',
            defaults={
                'last_exported_product_id': 0,
                'last_exported_timestamp': timezone.now(),
                'total_products_exported': 0,
                'export_status': 'success'
            }
        )
        return tracking

    def generate_xml(self, incremental=True):
        from django.utils.html import escape
        from .models import ProductVariants, ProductImage, StockAndPrices, ProductVariantsRetailPrice, ProductPaths, Paths, Vat
        from datetime import datetime, timedelta
        from django.db import models

        now = datetime.now()
        expires = now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<offer file_format="IOF" version="3.0" generated="{}" expires="{}" extensions="yes" xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml">'.format(
            now.strftime('%Y-%m-%d %H:%M:%S'), expires.strftime('%Y-%m-%d %H:%M:%S')))
        xml.append('  <products currency="PLN" language="pol">')

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
            currency = ''
            vat_rate = ''
            for variant in variants:
                pvrp = ProductVariantsRetailPrice.objects.using(
                    'MPD').filter(variant=variant).first()
                if pvrp:
                    currency = pvrp.currency or ''
                    if pvrp.vat:
                        vat_obj = Vat.objects.using(
                            'MPD').filter(id=pvrp.vat).first()
                        if vat_obj:
                            vat_rate = str(vat_obj.vat_rate)
                        else:
                            vat_rate = str(pvrp.vat)
                    break

            xml.append(
                f'    <product id="{iai_product_id}" currency="{currency}" type="regular" vat="{vat_rate}" site="1">')

            if product.brand:
                xml.append(
                    f'      <producer id="{product.brand.id}" name="{escape(product.brand.name) if product.brand.name else ""}"/>')

            # Dodaj wszystkie kategorie (category) powiązane z produktem
            product_paths = ProductPaths.objects.using(
                'MPD').filter(product_id=product.id)
            for product_path in product_paths:
                path_obj = Paths.objects.using('MPD').filter(
                    id=product_path.path_id).first()
                if path_obj:
                    xml.append(
                        f'      <category id="{path_obj.id}" name="{escape(path_obj.path)}"/>')

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
                    f'          <value id="{first_variant.color.id}" name="{escape(first_variant.color.name)}"/>')
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
                    size_attrs = [
                        f'id="{size_id}"',
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
                        xml.append(
                            f'          <price {" ".join(price_attrs)}/>')
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

        # Aktualizuj tracking po udanym eksporcie
        if variants_with_iai.exists():
            max_iai_id = variants_with_iai.aggregate(
                max_id=models.Max('iai_product_id')
            )['max_id']
            if max_iai_id:
                tracking = self.get_or_create_tracking()
                tracking.last_exported_product_id = max_iai_id
                tracking.last_exported_timestamp = timezone.now()
                tracking.total_products_exported += variants_with_iai.count()
                tracking.export_status = 'success'
                tracking.save()
                logger.info(
                    f"Zaktualizowano tracking - ostatni iai_product_id: {max_iai_id}")

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

            # Automatycznie odśwież gateway.xml po eksporcie
            try:
                gateway_exporter = GatewayXMLExporter()
                gateway_result = gateway_exporter.export()
                if gateway_result['bucket_url']:
                    print(
                        '✅ Gateway.xml zaktualizowany automatycznie!')
                else:
                    print(
                        '⚠️ Gateway.xml nie został zaktualizowany automatycznie')
            except Exception as e:
                print(
                    f'⚠️ Błąd podczas automatycznej aktualizacji gateway.xml: {str(e)}')
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
        if bucket_url:
            print('✅ Pełny eksport XML zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')

            # Automatycznie odśwież gateway.xml po eksporcie full.xml
            try:
                gateway_exporter = GatewayXMLExporter()
                gateway_result = gateway_exporter.export()
                if gateway_result['bucket_url']:
                    print('✅ Gateway.xml zaktualizowany automatycznie!')
                else:
                    print('⚠️ Gateway.xml nie został zaktualizowany automatycznie')
            except Exception as e:
                print(
                    f'⚠️ Błąd podczas automatycznej aktualizacji gateway.xml: {str(e)}')
        else:
            print('❌ Błąd podczas pełnego eksportu XML')
            print(f'📄 Lokalnie zapisano: {local_path}')
        return {'bucket_url': bucket_url, 'local_path': local_path}


class LightXMLExporter(BaseXMLExporter):
    def __init__(self):
        super().__init__('light.xml')

    def generate_xml(self):
        from django.utils.html import escape
        from .models import Products, ProductVariants, StockAndPrices, ProductVariantsRetailPrice, ProductvariantsSources, Vat
        from datetime import datetime, timedelta

        now = datetime.now()
        expires = now + timedelta(days=1)

        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<offer file_format="IOF" version="3.0" generated="{}" expires="{}" extensions="yes" xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml">'.format(
            now.strftime('%Y-%m-%d %H:%M:%S'), expires.strftime('%Y-%m-%d %H:%M:%S')))
        xml.append('  <products currency="PLN" language="pol">')

        # Pobierz wszystkie produkty z wariantami
        products = Products.objects.using('MPD').filter(
            productvariants__isnull=False
        ).distinct().select_related('brand')

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
        from datetime import datetime, timedelta
        from django.db.models import Q
        from .models import Products

        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        # Pobierz produkty zmienione w ciągu ostatniej godziny
        products = Products.objects.using('MPD').filter(
            Q(updated_at__gte=one_hour_ago) |
            Q(productvariants__updated_at__gte=one_hour_ago)
        ).distinct().select_related('brand')

        # Generuj XML tylko dla zmienionych produktów
        xml_content = self._generate_xml_for_products(products)
        local_path = self.save_local(xml_content)
        bucket_url = self.save_to_bucket(local_path)

        if bucket_url:
            print('✅ Eksport przyrostowy light.xml zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')

            # Automatycznie odśwież gateway.xml po eksporcie przyrostowym light.xml
            try:
                gateway_exporter = GatewayXMLExporter()
                gateway_result = gateway_exporter.export()
                if gateway_result['bucket_url']:
                    print(
                        '✅ Gateway.xml zaktualizowany automatycznie po eksporcie przyrostowym light.xml!')
                else:
                    print(
                        '⚠️ Gateway.xml nie został zaktualizowany automatycznie po eksporcie przyrostowym light.xml')
            except Exception as e:
                print(
                    f'⚠️ Błąd podczas automatycznej aktualizacji gateway.xml: {str(e)}')
        else:
            print('❌ Błąd podczas eksportu przyrostowego light.xml')
            print(f'📄 Lokalnie zapisano: {local_path}')

        return {'bucket_url': bucket_url, 'local_path': local_path}

    def _generate_xml_for_products(self, products):
        """Generuj XML dla określonej listy produktów"""
        from django.utils.html import escape
        from .models import ProductVariants, StockAndPrices, ProductVariantsRetailPrice, ProductvariantsSources, Vat
        from datetime import datetime, timedelta

        now = datetime.now()
        expires = now + timedelta(days=1)

        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<offer file_format="IOF" version="3.0" generated="{}" expires="{}" extensions="yes" xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml">'.format(
            now.strftime('%Y-%m-%d %H:%M:%S'), expires.strftime('%Y-%m-%d %H:%M:%S')))
        xml.append('  <products currency="PLN" language="pol">')

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

    def _create_meta_element(self, root, request_time=None):
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

        # Użyj request_time lub aktualnego czasu
        if request_time is None:
            request_time = timezone.now()

        # Konwertuj na lokalny czas (Europe/Warsaw)
        local_request_time = timezone.localtime(request_time)

        offer_created.set(
            "created", local_request_time.strftime("%Y-%m-%d %H:%M:%S"))
        offer_expires = ET.SubElement(time, "offer")
        offer_expires.set("expires", (local_request_time +
                          timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"))

    def _create_url_elements(self, root, request_time=None):
        # Użyj endpointów API zamiast statycznych plików
        from django.conf import settings

        # Podstawowy URL dla API z ustawień Django
        base_url = getattr(settings, 'API_BASE_URL', 'http://localhost:8000')

        # Użyj czasu żądania HTTP lub aktualnego czasu
        if request_time is None:
            request_time = datetime.now()

        # Tymczasowo dezaktywowane - zostawiam tylko gateway, full i full_change
        # required_elements = {}
        # optional_elements = {}
        # Generowanie węzłów wymaganych i opcjonalnych zostało wyłączone

        # Dodaj węzeł full z podwęzłem changes dla plików full_change
        self._create_full_with_changes_element(root, base_url, request_time)

    def _create_full_with_changes_element(self, root, base_url, request_time=None):
        """Tworzy węzeł full z podwęzłem changes dla rzeczywistych zmian w produktach"""

        try:
            # Utwórz węzeł full
            full_element = ET.SubElement(root, "full")

            # Dodaj podstawowe atrybuty dla full.xml - użyj endpointu API
            full_url = f"{base_url}/mpd/generate-full-xml/"
            full_element.set("url", full_url)

            # Dla endpointów API używamy czasu żądania HTTP
            import hashlib
            from datetime import timedelta

            # Użyj czasu żądania HTTP lub aktualnego czasu
            if request_time is None:
                request_time = timezone.now()

            # Konwertuj na lokalny czas (Europe/Warsaw)
            local_request_time = timezone.localtime(request_time)

            # Full.xml ma swój timestamp
            full_time = local_request_time.strftime('%Y-%m-%d %H:%M:%S')

            # Hash bazujący na rzeczywistych danych + czasie
            from .models import Products
            from django.db import models
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

                # Hash bazujący na: liczba produktów + ostatnia modyfikacja + czas żądania
                full_hash_input = f"generate-full-xml_{total_products}_{last_modified_str}_{local_request_time.strftime('%Y-%m-%d %H:%M:%S')}"
                full_hash = hashlib.md5(full_hash_input.encode()).hexdigest()

                logger.info(
                    f"Full.xml hash: products={total_products}, last_modified={last_modified_str}, request_time={full_time}")

            except Exception as e:
                # Fallback: hash bazujący tylko na czasie
                full_hash_input = f"generate-full-xml_{local_request_time.strftime('%Y-%m-%d %H:%M:%S')}"
                full_hash = hashlib.md5(full_hash_input.encode()).hexdigest()
                logger.warning(
                    f"Błąd generowania hash dla full.xml: {str(e)}, używam fallback")

            full_element.set("hash", full_hash)
            full_element.set("changed", full_time)

            # Sprawdź rzeczywiste zmiany w produktach zgodnie ze specyfikacją IdoSell

            # Pobierz produkty zmodyfikowane w ostatnich 60 minutach (specyfikacja IdoSell)
            cutoff_time = request_time - timedelta(minutes=60)

            recent_changes = Products.objects.using('MPD').filter(
                updated_at__gte=cutoff_time
            ).order_by('-updated_at')

            if recent_changes.exists():
                # Utwórz podwęzeł changes
                changes_element = ET.SubElement(full_element, "changes")

                # Generuj change dla każdej zmiany (zgodnie z IdoSell)
                for i, product in enumerate(recent_changes):
                    change_element = ET.SubElement(changes_element, "change")

                    # URL do endpointu API dla full_change
                    url = f"{base_url}/mpd/generate-full-change-xml/"
                    change_element.set("url", url)

                    # Timestamp w formacie ISO 8601 (YYYY-MM-DDThh-mm-ss) - specyfikacja IdoSell
                    # Użyj czasu modyfikacji produktu + małe przesunięcie dla unikalności
                    if product.updated_at:
                        change_time = product.updated_at + timedelta(seconds=i)
                    else:
                        change_time = local_request_time + timedelta(seconds=i)

                    # Konwertuj na lokalny czas
                    local_change_time = timezone.localtime(change_time)
                    change_time_str = local_change_time.strftime(
                        '%Y-%m-%d %H:%M:%S')

                    # Hash bazujący na konkretnym produkcie + czasie modyfikacji
                    try:
                        # Hash bazujący na: ID produktu + czas modyfikacji + indeks
                        change_hash_input = f"generate-full-change-xml_{product.id}_{local_change_time.strftime('%Y-%m-%dT%H-%M-%S')}_{i}"
                        hash_value = hashlib.md5(
                            change_hash_input.encode()).hexdigest()

                        logger.info(
                            f"Full_change.xml hash (IdoSell): product_id={product.id}, change_time={local_change_time.strftime('%Y-%m-%dT%H-%M-%S')}, index={i}")

                    except Exception as e:
                        # Fallback: hash bazujący tylko na czasie
                        change_hash_input = f"generate-full-change-xml_{local_change_time.strftime('%Y-%m-%dT%H-%M-%S')}_{i}"
                        hash_value = hashlib.md5(
                            change_hash_input.encode()).hexdigest()
                        logger.warning(
                            f"Błąd generowania hash dla full_change.xml: {str(e)}, używam fallback")

                    change_element.set("hash", hash_value)
                    change_element.set("changed", change_time_str)

                    logger.info(
                        f"API endpoint full_change (IdoSell): hash={hash_value}, changed={change_time_str}, product_id={product.id}")

                logger.info(
                    f"Wygenerowano {len(recent_changes)} zmian w full_change.xml")

            else:
                logger.info(
                    "Brak zmian w produktach w ostatnich 60 minutach (IdoSell)")

        except Exception as e:
            logger.error(
                f"Błąd podczas tworzenia węzła full z changes: {str(e)}")
            # Utwórz podstawowy węzeł full bez changes
            full_element = ET.SubElement(root, "full")
            full_element.set("url", f"{base_url}/mpd/generate-full-xml/")
            full_element.set("hash", "")
            full_element.set("changed", "")

    def generate_xml(self, request_time=None):
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
        self._create_meta_element(root, request_time)
        self._create_url_elements(root, request_time)
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
        from datetime import datetime, timedelta
        now = datetime.now()
        expires = now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<producers file_format="IOF" version="3.0" generated_by="nc" language="pol" generated="{}" expires="{}">'.format(
            now.strftime('%Y-%m-%d %H:%M:%S'), expires.strftime('%Y-%m-%d %H:%M:%S')))
        brands = Brands.objects.using('MPD').all()
        for brand in brands:
            # id: string, bez spacji, tylko a-z, A-Z, _, -
            brand_id = str(brand.id) if brand.id is not None else ''
            brand_id = brand_id.replace(' ', '_')
            name = escape(brand.name) if brand.name else ''
            xml.append(f'  <producer id="{brand_id}" name="{name}"/>')
        xml.append('</producers>')
        return '\n'.join(xml)


class StocksXMLExporter(BaseXMLExporter):
    def __init__(self):
        super().__init__('stocks.xml')

    def generate_xml(self):
        from django.utils.html import escape
        from .models import StockAndPrices
        from datetime import datetime, timedelta
        now = datetime.now()
        expires = now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<stocks file_format="IOF" version="3.0" generated_by="nc" language="pol" generated="{}" expires="{}">'.format(
            now.strftime('%Y-%m-%d %H:%M:%S'), expires.strftime('%Y-%m-%d %H:%M:%S')))
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


class UnitsXMLExporter(BaseXMLExporter):
    def __init__(self):
        super().__init__('units.xml')

    def generate_xml(self):
        from django.utils.html import escape
        from .models import Units
        from datetime import datetime, timedelta
        now = datetime.now()
        expires = now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<units file_format="IOF" version="3.0" generated="{}" expires="{}" language="pol">'.format(
            now.strftime('%Y-%m-%d %H:%M:%S'), expires.strftime('%Y-%m-%d %H:%M:%S')))
        units = Units.objects.using('MPD').all()
        for unit in units:
            xml.append(
                f'  <unit id="{unit.unit_id}" name="{escape(unit.name) if unit.name else ''}"/>')
        xml.append('</units>')
        return '\n'.join(xml)


class FullChangeXMLExporter(BaseXMLExporter):
    def __init__(self):
        # Generuj nazwę pliku z aktualną datą
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%dT%H-%M-%S')
        filename = f'full_change{timestamp}.xml'
        super().__init__(filename)
        self.timestamp = timestamp
        self.created_at = now

    def get_or_create_tracking(self):
        """Pobierz lub utwórz tracking dla full_change.xml - używa last_exported_product_id z full.xml"""
        from .models import ExportTracking

        # Najpierw pobierz tracking dla full.xml
        full_tracking = ExportTracking.objects.using('MPD').filter(
            export_type='full.xml'
        ).first()

        if not full_tracking:
            # Jeśli nie ma full.xml tracking, utwórz z wartością 0
            tracking, created = ExportTracking.objects.using('MPD').get_or_create(
                export_type='full_change.xml',
                defaults={
                    'last_exported_product_id': 0,
                    'last_exported_timestamp': timezone.now(),
                    'total_products_exported': 0,
                    'export_status': 'success'
                }
            )
            return tracking

        # Pobierz lub utwórz tracking dla full_change.xml z last_exported_product_id z full.xml
        tracking, created = ExportTracking.objects.using('MPD').get_or_create(
            export_type='full_change.xml',
            defaults={
                'last_exported_product_id': full_tracking.last_exported_product_id,
                'last_exported_timestamp': timezone.now(),
                'total_products_exported': full_tracking.last_exported_product_id,
                'export_status': 'success'
            }
        )

        # Jeśli tracking już istniał, ale ma mniejszy last_exported_product_id niż full.xml
        if not created and tracking.last_exported_product_id < full_tracking.last_exported_product_id:
            tracking.last_exported_product_id = full_tracking.last_exported_product_id
            tracking.total_products_exported = full_tracking.last_exported_product_id
            tracking.last_exported_timestamp = timezone.now()
            tracking.save()

        return tracking

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
            xml.append(
                f'            <iaiext:item id="{path.id}" menu_id="1" textid="{textid}" iaiext:priority_menu="{idx}"/>')
        xml.append('          </iaiext:menu>')
        xml.append('        </iaiext:site>')
        xml.append('      </iaiext:navigation>')
        return '\n'.join(xml)

    def generate_xml(self, incremental=True):
        from django.utils.html import escape
        from .models import ProductVariants, ProductImage, StockAndPrices, ProductVariantsRetailPrice, ProductPaths, Paths
        from datetime import datetime, timedelta
        from django.db.models import Q
        from .models import Vat

        now = datetime.now()
        expires = now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<offer file_format="IOF" version="3.0" generated="{}" expires="{}" extensions="yes" xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml">'.format(
            now.strftime('%Y-%m-%d %H:%M:%S'), expires.strftime('%Y-%m-%d %H:%M:%S')))
        xml.append('  <products currency="PLN" language="pol">')

        # Tracking nie jest używane w nowej logice IdoSell (60 minut dla wszystkich produktów)

        # Oblicz timestamp z 60 minut temu (specyfikacja IdoSell)
        sixty_minutes_ago = now - timedelta(minutes=60)

        if incremental:
            # Eksport przyrostowy - tylko produkty zmienione w ciągu ostatnich 60 minut (IdoSell)
            # Sprawdź zmiany w wariantach, produktach i obrazach - WSZYSTKIE produkty
            variants_with_iai = ProductVariants.objects.using('MPD').filter(
                iai_product_id__isnull=False
            ).filter(
                Q(updated_at__gte=sixty_minutes_ago) |  # Wariant zmieniony
                # Produkt zmieniony
                Q(product__updated_at__gte=sixty_minutes_ago) |
                # Obraz zmieniony
                Q(product__images__updated_at__gte=sixty_minutes_ago)
            ).select_related('product', 'size', 'color', 'producer_color', 'product__brand').distinct()

            logger.info(
                f"Eksport przyrostowy full_change.xml (IdoSell) - produkty zmienione od: {sixty_minutes_ago.strftime('%Y-%m-%d %H:%M:%S')} (wszystkie produkty)")
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
            currency = ''
            vat_rate = ''
            for variant in variants:
                pvrp = ProductVariantsRetailPrice.objects.using(
                    'MPD').filter(variant=variant).first()
                if pvrp:
                    currency = pvrp.currency or ''
                    if pvrp.vat:
                        vat_obj = Vat.objects.using(
                            'MPD').filter(id=pvrp.vat).first()
                        if vat_obj:
                            vat_rate = str(vat_obj.vat_rate)
                        else:
                            vat_rate = str(pvrp.vat)
                    break

            xml.append(
                f'    <product id="{iai_product_id}" currency="{currency}" type="regular" vat="{vat_rate}" site="1">')

            if product.brand:
                xml.append(
                    f'      <producer id="{product.brand.id}" name="{escape(product.brand.name) if product.brand.name else ""}"/>')

            # Dodaj wszystkie kategorie (category) powiązane z produktem
            product_paths = ProductPaths.objects.using(
                'MPD').filter(product_id=product.id)
            for product_path in product_paths:
                path_obj = Paths.objects.using('MPD').filter(
                    id=product_path.path_id).first()
                if path_obj:
                    xml.append(
                        f'      <category id="{path_obj.id}" name="{escape(path_obj.path)}"/>')

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
                    f'          <value id="{first_variant.color.id}" name="{escape(first_variant.color.name)}"/>')
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
                    size_attrs = [
                        f'id="{size_id}"',
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
                        xml.append(
                            f'          <price {" ".join(price_attrs)}/>')
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
    return exporter.export()


def export_incremental_full_change_xml():
    """Eksport przyrostowy zmienionych produktów do full_change.xml z datą w nazwie"""
    exporter = FullChangeXMLExporter()
    return exporter.export()


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
