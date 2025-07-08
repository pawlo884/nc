import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from django.utils import timezone
from .models import Products, ProductVariants, StockAndPrices
from matterhorn.defs_db import s3_client, DO_SPACES_BUCKET, DO_SPACES_REGION
import logging

logger = logging.getLogger(__name__)


def export_to_full_xml():
    """Generuje pełny plik XML z produktami w formacie IOF"""
    # Pierwsza linia XML - nagłówek
    xml_content = '<?xml version="1.0" encoding="utf-8"?>\n'

    # Element offer z atrybutami
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    expires_time = (datetime.now() + timezone.timedelta(days=1)
                    ).strftime('%Y-%m-%d %H:%M:%S')

    xml_content += f'<offer xmlns:iof="http://www.iai-shop.com/developers/iof.phtml" xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml" file_format="IOF" generated="{current_time}" expires="{expires_time}" version="3.0" extensions="yes">\n'

    # Element products z atrybutami
    xml_content += '    <products xmlns:iaiext="http://www.iai-shop.com/developers/iof/extensions.phtml" currency="PLN" iof_translation_generated="yes" language="pol">\n'
    xml_content += '    </products>\n'

    # Zamykający tag offer
    xml_content += '</offer>\n'

    return xml_content


def save_xml_to_bucket(xml_content, filename='export_full.xml'):
    """Zapisuje wygenerowany XML do bucketa"""
    try:
        # Zapisanie do pliku tymczasowego
        temp_file = filename
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        # Przesłanie do bucketa
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


def create_xml_file():
    """Główna funkcja do wywołania eksportu XML"""
    try:
        xml_content = export_to_full_xml()
        file_url = save_xml_to_bucket(xml_content)

        if file_url:
            print('✅ Eksport XML zakończony pomyślnie!')
            print(f'📁 URL: {file_url}')
            return file_url
        else:
            print('❌ Błąd podczas eksportu XML')
            return None
    except Exception as e:
        print(f'❌ Błąd podczas eksportu XML: {e}')
        return None
