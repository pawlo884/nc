# pylint: disable=wrong-import-order
import os
from urllib.parse import urlsplit
from dotenv import load_dotenv
import boto3
import logging
import requests

logger = logging.getLogger(__name__)

# Załaduj zmienne środowiskowe
load_dotenv('.env.dev')

# Konfiguracja S3 (MinIO / S3-compatible)
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT')
MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
MINIO_REGION = os.getenv('MINIO_REGION', 'us-east-1')
MINIO_PUBLIC_URL = os.getenv('MINIO_PUBLIC_URL')

DO_SPACES_BUCKET = os.getenv('DO_SPACES_BUCKET')
DO_SPACES_REGION = os.getenv('DO_SPACES_REGION')
DO_SPACES_ACCESS_KEY_ID = os.getenv('DO_SPACES_KEY') or os.getenv(
    'DO_SPACES_ACCESS_KEY_ID')
DO_SPACES_SECRET = os.getenv('DO_SPACES_SECRET')

if MINIO_ENDPOINT and MINIO_ACCESS_KEY and MINIO_SECRET_KEY:
    S3_BUCKET = MINIO_BUCKET_NAME or 'nc-media'
    S3_REGION = MINIO_REGION
    S3_ENDPOINT = MINIO_ENDPOINT.rstrip('/')
    S3_ACCESS_KEY = MINIO_ACCESS_KEY
    S3_SECRET = MINIO_SECRET_KEY
    PUBLIC_BASE_URL = (
        MINIO_PUBLIC_URL.rstrip('/')
        if MINIO_PUBLIC_URL
        else f"{S3_ENDPOINT}/{S3_BUCKET}"
    )
else:
    S3_BUCKET = DO_SPACES_BUCKET
    S3_REGION = DO_SPACES_REGION or 'us-east-1'
    S3_ENDPOINT = (
        f'https://{DO_SPACES_REGION}.digitaloceanspaces.com'
        if DO_SPACES_REGION else None
    )
    S3_ACCESS_KEY = DO_SPACES_ACCESS_KEY_ID
    S3_SECRET = DO_SPACES_SECRET
    PUBLIC_BASE_URL = (
        f"https://{DO_SPACES_BUCKET}.{DO_SPACES_REGION}.digitaloceanspaces.com"
        if DO_SPACES_BUCKET and DO_SPACES_REGION else None
    )

# Brak wymaganej konfiguracji nie powinien blokować operacji niezwiązanych ze storage
# (np. collectstatic w czasie builda). Zamiast wyjątku ustawiamy tryb "no-storage".
if not all([S3_BUCKET, S3_ACCESS_KEY, S3_SECRET]):
    logger.warning(
        "Brak wymaganej konfiguracji MinIO/S3 (MINIO_* lub DO_SPACES_*). "
        "Przechodzę w tryb no-storage (upload/DELETE będą pomijane)."
    )
    S3_BUCKET = S3_BUCKET or "no-storage"
    S3_REGION = S3_REGION if 'S3_REGION' in globals() else None
    S3_ENDPOINT = S3_ENDPOINT if 'S3_ENDPOINT' in globals() else None
    S3_ACCESS_KEY = S3_ACCESS_KEY or None
    S3_SECRET = S3_SECRET or None
    PUBLIC_BASE_URL = None

BUCKET_PUBLIC_BASE_URL = PUBLIC_BASE_URL


def normalize_storage_key(url: str) -> str:
    """Zastąp pełny URL relatywną ścieżką wewnątrz bucketa (bez prefiksu bucket name)."""
    if not url:
        return url
    if url.startswith(('http://', 'https://')):
        parts = urlsplit(url)
        path = parts.path.lstrip('/')
    else:
        path = url.lstrip('/')
    
    # Usuń prefiks nazwy bucketa jeśli jest w ścieżce
    bucket_name = S3_BUCKET
    if path.startswith(f'{bucket_name}/'):
        path = path[len(f'{bucket_name}/'):]
    
    return path


def build_public_url(key: str) -> str | None:
    """Zwróć publiczny URL dla klucza w buckecie."""
    if not key:
        return None
    if key.startswith(('http://', 'https://')):
        return key
    if BUCKET_PUBLIC_BASE_URL:
        return f"{BUCKET_PUBLIC_BASE_URL.rstrip('/')}/{key.lstrip('/')}"
    return None


def resolve_image_url(value: str) -> str | None:
    """Zwróć publiczny URL niezależnie od tego, czy w bazie jest pełny adres czy klucz."""
    return build_public_url(normalize_storage_key(value))

if all([S3_ACCESS_KEY, S3_SECRET]):
    s3_client = boto3.client(
        's3',
        region_name=S3_REGION,
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET
    )
else:
    s3_client = None


def upload_image_to_bucket_and_get_url(image_path, product_id, producer_color_name=None, image_number=1):
    """
    Upload obrazu do bucketa S3 kompatybilnego z MinIO

    Args:
        image_path (str): URL lub ścieżka do obrazu
        product_id (int): ID produktu
        producer_color_name (str): Nazwa koloru producenta (opcjonalne)
        image_number (int): Numer obrazu (opcjonalne)

    Returns:
        str: URL przesłanego obrazu lub None w przypadku błędu
    """
    try:
        logger.info(
            f"Rozpoczynam przesyłanie zdjęcia: {image_path} dla produktu {product_id}")

        is_production = os.getenv(
            "DJANGO_SETTINGS_MODULE") == 'nc.settings.prod'
        bucket_folder = "MPD" if is_production else "MPD_test"
        logger.info(
            f"Środowisko: {'produkcyjne' if is_production else 'testowe'}, folder: {bucket_folder}")

        # Określ rozszerzenie pliku
        if image_path.startswith(('http://', 'https://')):
            # Pobierz rozszerzenie z URL
            file_extension = os.path.splitext(
                image_path.split('?')[0])[1].lower()
        else:
            file_extension = os.path.splitext(image_path)[1].lower()

        logger.info(f"Rozszerzenie pliku: {file_extension}")

        if file_extension not in ['.jpg', '.jpeg', '.png', '.webp']:
            logger.error(f"Nieprawidłowe rozszerzenie pliku: {file_extension}")
            return None

        # Zamień znaki niedozwolone na podkreślnik
        safe_color = producer_color_name.replace(
            '/', '_').replace(' ', '_') if producer_color_name else ""
        suffix = f"_{safe_color}" if safe_color else ""
        new_filename = f"{product_id}_{image_number}{suffix}{file_extension}"
        new_path = f"{bucket_folder}/{product_id}/{new_filename}"
        logger.info(f"Nowa nazwa pliku: {new_filename}, ścieżka: {new_path}")

        # Pobierz dane obrazu
        if image_path.startswith(('http://', 'https://')):
            logger.info(f"Pobieranie pliku z URL: {image_path}")
            try:
                response = requests.get(image_path, stream=True, timeout=30)
                if response.status_code != 200:
                    logger.error(
                        f"Nie można pobrać pliku z URL: {image_path}. Status code: {response.status_code}")
                    return None
                file_data = response.content
                logger.info(
                    f"Pobrano plik z URL, rozmiar: {len(file_data)} bajtów")
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Błąd podczas pobierania pliku z URL: {image_path}. Błąd: {str(e)}")
                return None
        else:
            logger.info(f"Otwieranie pliku lokalnego: {image_path}")
            if not os.path.exists(image_path):
                logger.error(f"Plik do uploadu nie istnieje: {image_path}")
                return None
            with open(image_path, 'rb') as f:
                file_data = f.read()
                logger.info(
                    f"Odczytano plik lokalny, rozmiar: {len(file_data)} bajtów")

        # Prześlij do S3
        if not s3_client:
            logger.warning("Tryb no-storage: pomijam upload do S3")
            return None
        logger.info(f"Przesyłanie pliku do S3: {new_path}")
        try:
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=new_path,
                Body=file_data,
                ContentType=f'image/{file_extension[1:]}',
                ACL='public-read'
            )
            logger.info(f"Plik został pomyślnie przesłany do S3: {new_path}")
        except Exception as e:
            logger.error(f"Błąd podczas przesyłania pliku do S3: {str(e)}")
            return None

        # Zwróć URL
        file_key = normalize_storage_key(new_path)
        file_url = build_public_url(file_key)
        logger.info(f"Wygenerowany URL pliku: {file_url}")
        return file_key

    except Exception as e:
        logger.error(f"Błąd podczas przesyłania pliku do S3: {str(e)}")
        return None


def delete_product_folder_from_bucket(product_id):
    """
    Usuń folder produktu z bucketa

    Args:
        product_id (int): ID produktu
    """
    try:
        if not s3_client:
            logger.warning("Tryb no-storage: pomijam usuwanie z bucketa")
            return
        is_production = os.getenv(
            "DJANGO_SETTINGS_MODULE") == 'nc.settings.prod'
        bucket_folder = "MPD" if is_production else "MPD_test"
        prefix = f"{bucket_folder}/{product_id}/"

        # Pobierz listę obiektów do usunięcia
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET, Prefix=prefix)

        if 'Contents' in response:
            for obj in response['Contents']:
                s3_client.delete_object(
                    Bucket=S3_BUCKET, Key=obj['Key'])
        logger.info(f"Usunięto folder {prefix} z bucketa.")

    except Exception as e:
        logger.error(
            f"Błąd podczas usuwania folderu {prefix} z bucketa: {str(e)}")


def upload_product_images_to_bucket(product_id, images_data):
    """
    Upload wszystkich obrazów produktu do bucketa

    Args:
        product_id (int): ID produktu
        images_data (list): Lista danych obrazów z bazy

    Returns:
        list: Lista URL-ów przesłanych obrazów
    """
    uploaded_urls = []

    for i, image_data in enumerate(images_data, 1):
        image_url = image_data.get('image_url')
        if not image_url:
            continue

        # Pobierz nazwę koloru z danych produktu
        color_name = image_data.get('color_name', '')

        # Upload obrazu
        uploaded_key = upload_image_to_bucket_and_get_url(
            image_url=image_url,
            product_id=product_id,
            color_name=color_name,
            image_number=i
        )

        if uploaded_key:
            uploaded_urls.append({
                'original_url': image_url,
                'uploaded_url': build_public_url(uploaded_key),
                'storage_key': uploaded_key,
                'order': image_data.get('order', i)
            })

    return uploaded_urls
