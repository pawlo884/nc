import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from django.utils import timezone
from .models import Sources
from matterhorn.defs_db import s3_client, DO_SPACES_BUCKET, DO_SPACES_REGION
import logging

logger = logging.getLogger(__name__)


class XMLExporter:
    def __init__(self, source_name):
        self.source_name = source_name
        self.source = Sources.objects.filter(name=source_name).first()
        if not self.source:
            raise ValueError(f"Nie znaleziono źródła o nazwie: {source_name}")

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
        offer_expires.set("expires", (datetime.now() +
                          timezone.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"))

    def _create_url_elements(self, root):
        elements = {
            "full": "fulloferta.xml",
            "light": "lightoferta.xml",
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

        for element_name, file_name in elements.items():
            element = ET.SubElement(root, element_name)
            element.set("url", f"https://adres.pl/{file_name}")

    def export_sources_to_xml(self):
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

        temp_file = f"{self.source_name.lower()}_gateway.xml"
        with open(temp_file, "wb") as f:
            f.write(xmlstr)

        try:
            bucket_path = f"MPD_test/xml/{temp_file}"

            with open(temp_file, 'rb') as f:
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
