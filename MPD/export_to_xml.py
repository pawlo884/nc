import os
from matterhorn.defs_db import s3_client, DO_SPACES_BUCKET, DO_SPACES_REGION
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
import requests
from datetime import datetime
from django.utils import timezone
from django.conf import settings
import gc
from .models import Sources

"""
Eksporter XML dla systemu MPD

Użycie:
- export_full() - eksport wszystkich produktów
- export_incremental() - eksport produktów zmienionych w ciągu ostatnich 2 godzin (do uruchamiania co godzinę)

Monitoring zmian:
- Sprawdza kolumny updated_at w tabelach: product_variants, products, product_variants_retail_price
- Sprawdza kolumnę last_updated w tabeli stock_and_prices
- Generuje plik full.xml z produktami, które mają visibility=0 jeśli nie mają ceny detalicznej
- Generuje plik full_change.xml z produktami zmienionymi w ciągu ostatnich 2 godzin
"""

logger = logging.getLogger(__name__)


class BaseXMLExporter:
    def __init__(self, filename):
        self.filename = filename
        self.batch_size = getattr(
            settings, 'DATABASE_OPTIMIZATION', {}).get('BATCH_SIZE', 1000)

    def generate_xml(self):
        raise NotImplementedError

    def save_local(self, xml_content):
        local_dir = 'MPD_test/xml/matterhorn/'
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, self.filename)

        # Zapisz w trybie strumieniowym dla dużych plików
        with open(local_path, 'w', encoding='utf-8') as f:
            if isinstance(xml_content, list):
                for line in xml_content:
                    f.write(line + '\n')
            else:
                f.write(xml_content)
        return local_path

    def save_to_bucket(self, local_file_path):
        try:
            bucket_path = f"MPD_test/xml/matterhorn/{self.filename}"

            # Czytaj plik w chunk'ach aby oszczędzić pamięć
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

    def cleanup_memory(self):
        """Czyszczenie pamięci po przetworzeniu batch'a"""
        gc.collect()


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

        # Użyj select_related dla optymalizacji
        product_paths = ProductPaths.objects.using('MPD').filter(
            product_id=product_id).select_related('path')

        for idx, product_path in enumerate(product_paths, 1):
            path = product_path.path
            if path and path.path:
                textid = escape(path.path)
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
        from django.utils import timezone
        from django.db import models

        now = datetime.now()
        expires = now + timedelta(days=1)
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<offer file_format="IOF" version="3.0" generated="{}" expires="{}" extensions="yes" xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml">'.format(
            now.strftime('%Y-%m-%d %H:%M:%S'), expires.strftime('%Y-%m-%d %H:%M:%S')))
        xml.append('  <products currency="PLN" language="pol">')

        # Pobierz tracking
        tracking = self.get_or_create_tracking()
        last_exported_id = tracking.last_exported_product_id or 0

        # Pobierz warianty z iai_product_id, od ostatniego wyeksportowanego
        if incremental and last_exported_id > 0:
            # Eksport przyrostowy - tylko nowe produkty
            variants_queryset = ProductVariants.objects.using('MPD').filter(
                iai_product_id__isnull=False,
                iai_product_id__gt=last_exported_id
            ).select_related('product', 'size', 'color', 'producer_color', 'product__brand')
            logger.info(
                f"Eksport przyrostowy full.xml - od iai_product_id: {last_exported_id}")
        else:
            # Pełny eksport - wszystkie produkty
            variants_queryset = ProductVariants.objects.using('MPD').filter(
                iai_product_id__isnull=False
            ).select_related('product', 'size', 'color', 'producer_color', 'product__brand')
            logger.info("Pełny eksport full.xml - wszystkie produkty")

        # Użyj iterator() dla optymalizacji pamięci
        total_variants = variants_queryset.count()
        logger.info(f"Przetwarzanie {total_variants} wariantów")

        processed_count = 0
        batch_count = 0

        # Przetwarzaj w batch'ach
        for offset in range(0, total_variants, self.batch_size):
            batch_count += 1
            logger.info(
                f"Przetwarzanie batch {batch_count} (offset: {offset})")

            # Pobierz batch wariantów
            batch_variants = list(
                variants_queryset[offset:offset + self.batch_size])

            # Grupuj warianty po iai_product_id w ramach batch'a
            grouped_variants = {}
            for variant in batch_variants:
                iai_id = variant.iai_product_id
                if iai_id not in grouped_variants:
                    grouped_variants[iai_id] = []
                grouped_variants[iai_id].append(variant)

            # Iteruj po unikalnych iai_product_id w batch'u
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
                            xml.append(
                                f'      <price {" ".join(price_attrs)}/>')

                # Sprawdź czy produkt ma cenę detaliczną w tabeli product_variants_retail_price
                has_retail_price = False
                for variant in variants:
                    retail_price_obj = ProductVariantsRetailPrice.objects.using(
                        'MPD').filter(variant=variant).first()
                    if retail_price_obj and hasattr(retail_price_obj, 'retail_price') and retail_price_obj.retail_price:
                        has_retail_price = True
                        break

                # Zawsze generuj węzeł visibility - yes jeśli ma cenę, no jeśli nie ma
                xml.append('      <iaiext:visibility>')
                if has_retail_price:
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
                                f'          <price {' '.join(price_attrs)}/>')
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
        if variants_queryset.exists():
            max_iai_id = variants_queryset.aggregate(
                max_id=models.Max('iai_product_id')
            )['max_id']
            if max_iai_id:
                tracking.last_exported_product_id = max_iai_id
                tracking.last_exported_timestamp = timezone.now()
                tracking.total_products_exported += variants_queryset.count()
                tracking.export_status = 'success'
                tracking.save()
                logger.info(
                    f"Zaktualizowano tracking - ostatni iai_product_id: {max_iai_id}")

        return '\n'.join(xml)

    def export_incremental(self):
        """Eksport przyrostowy - tylko nowe produkty"""
        return self.export()

    def export_full(self):
        """Eksport pełny - wszystkie produkty"""
        xml_content = self.generate_xml(incremental=False)
        local_path = self.save_local(xml_content)
        bucket_url = self.save_to_bucket(local_path)
        if bucket_url:
            print('✅ Pełny eksport XML zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
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


class GatewayXMLExporter(BaseXMLExporter):
    def __init__(self, source_name=None):
        # Zawsze używaj Matterhorn (id=2), ignoruj source_name
        super().__init__('gateway.xml')
        try:
            self.source = Sources.objects.get(id=2)  # Tylko Matterhorn
            self.source_name = self.source.name
        except Sources.DoesNotExist:
            raise ValueError("Nie znaleziono źródła Matterhorn (id=2)")

    def _create_meta_element(self, root):
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
        offer_created.set(
            "created", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        offer_expires = ET.SubElement(time, "offer")
        offer_expires.set("expires", (datetime.now(
        ) + timezone.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"))

    def _create_url_elements(self, root):
        elements = {
            "full": "full.xml",
            "full_change": "full_change.xml",
            "light": "light.xml",
            "categories": "categories.xml",
            "sizes": "sizes.xml",
            "producers": "producers.xml",
            "units": "units.xml",
            "parameters": "parameters.xml",
            "stocks": "stocks.xml",
            "series": "series.xml",
            "warranties": "warranties.xml",
            "preset": "preset.xml"
        }
        bucket_url = f"https://{DO_SPACES_BUCKET}.{DO_SPACES_REGION}.digitaloceanspaces.com/MPD_test/xml/matterhorn/"

        for element_name, file_name in elements.items():
            element = ET.SubElement(root, element_name)
            url = bucket_url + file_name
            element.set("url", url)

            # Najpierw sprawdź lokalny plik
            local_path = os.path.join('MPD_test/xml/matterhorn/', file_name)
            hash_value = ""
            changed_value = ""

            if os.path.exists(local_path):
                try:
                    # Oblicz hash z lokalnego pliku
                    import hashlib
                    with open(local_path, 'rb') as f:
                        file_content = f.read()
                        hash_value = hashlib.md5(file_content).hexdigest()

                    # Pobierz datę modyfikacji z systemu plików
                    mtime = os.path.getmtime(local_path)
                    changed_dt = datetime.fromtimestamp(mtime)
                    changed_value = changed_dt.strftime('%Y-%m-%d %H:%M:%S')

                except Exception as e:
                    logger.warning(
                        f"Błąd podczas obliczania hash/changed dla {file_name}: {str(e)}")
                    hash_value = ""
                    changed_value = ""
            else:
                # Fallback: sprawdź zdalny plik
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        import hashlib
                        hash_value = hashlib.md5(response.content).hexdigest()

                        # Spróbuj pobrać datę z nagłówków
                        last_modified = response.headers.get('Last-Modified')
                        if last_modified:
                            try:
                                # Różne formaty dat w nagłówkach HTTP
                                for fmt in ['%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S GMT']:
                                    try:
                                        changed_dt = datetime.strptime(
                                            last_modified, fmt)
                                        changed_value = changed_dt.strftime(
                                            '%Y-%m-%d %H:%M:%S')
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                changed_value = ""
                except Exception as e:
                    logger.warning(
                        f"Błąd podczas pobierania zdalnego pliku {file_name}: {str(e)}")
                    hash_value = ""
                    changed_value = ""

            element.set("hash", hash_value)
            element.set("changed", changed_value)

    def generate_xml(self):
        root = ET.Element("provider_description")
        root.set("file_format", "IOF")
        root.set("version", "3.0")
        root.set("generated_by", "nc")
        root.set("generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._create_meta_element(root)
        self._create_url_elements(root)
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
        super().__init__('full_change.xml')

    def get_or_create_tracking(self):
        """Pobierz lub utwórz tracking dla full_change.xml - używa last_exported_product_id z full.xml"""
        from .models import ExportTracking
        from django.utils import timezone

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

        # Pobierz tracking
        tracking = self.get_or_create_tracking()
        last_exported_id = tracking.last_exported_product_id or 0

        # Oblicz timestamp z 2 godziny temu
        two_hours_ago = now - timedelta(hours=2)

        if incremental:
            # Eksport przyrostowy - tylko produkty zmienione w ciągu ostatnich 2 godzin
            # ALE tylko te które są już wyeksportowane (id ≤ last_exported_product_id)
            if last_exported_id > 0:
                # Sprawdź zmiany w wariantach i produktach
                # Tylko dla produktów z id ≤ last_exported_product_id
                variants_with_iai = ProductVariants.objects.using('MPD').filter(
                    iai_product_id__isnull=False,
                    iai_product_id__lte=last_exported_id  # Tylko wyeksportowane produkty
                ).filter(
                    Q(updated_at__gte=two_hours_ago) |  # Wariant zmieniony
                    Q(product__updated_at__gte=two_hours_ago)  # Produkt zmieniony
                ).select_related('product', 'size', 'color', 'producer_color', 'product__brand').distinct()

                logger.info(
                    f"Eksport przyrostowy full_change.xml - produkty zmienione od: {two_hours_ago.strftime('%Y-%m-%d %H:%M:%S')} (tylko wyeksportowane, id ≤ {last_exported_id})")
            else:
                # Brak wyeksportowanych produktów - pusta lista
                variants_with_iai = ProductVariants.objects.using('MPD').none()
                logger.info(
                    "Eksport przyrostowy full_change.xml - brak wyeksportowanych produktów")
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

            # Sprawdź czy produkt ma cenę detaliczną w tabeli product_variants_retail_price
            has_retail_price = False
            for variant in variants:
                retail_price_obj = ProductVariantsRetailPrice.objects.using(
                    'MPD').filter(variant=variant).first()
                if retail_price_obj and hasattr(retail_price_obj, 'retail_price') and retail_price_obj.retail_price:
                    has_retail_price = True
                    break

            # Zawsze generuj węzeł visibility - yes jeśli ma cenę, no jeśli nie ma
            xml.append('      <iaiext:visibility>')
            if has_retail_price:
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
                    f'      <sizes iaiext:group_name="{group_name}" iaiext:group_id="1" iaiext:sizeList="full">')
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
                            f'          <price {' '.join(price_attrs)}/>')
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
                            f'  <stock id="{stock_id}" quantity="{stock_price.stock}"/>')
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

    def export_incremental(self):
        """Eksport przyrostowy - tylko produkty zmienione w ciągu ostatnich 2 godzin"""
        return self.export()

    def export_full(self):
        """Eksport pełny - wszystkie produkty"""
        xml_content = self.generate_xml(incremental=False)
        local_path = self.save_local(xml_content)
        bucket_url = self.save_to_bucket(local_path)
        if bucket_url:
            print('✅ Pełny eksport full_change.xml zakończony pomyślnie!')
            print(f'📁 URL: {bucket_url}')
            print(f'📄 Lokalnie zapisano: {local_path}')
        else:
            print('❌ Błąd podczas pełnego eksportu full_change.xml')
            print(f'📄 Lokalnie zapisano: {local_path}')
        return {'bucket_url': bucket_url, 'local_path': local_path}
