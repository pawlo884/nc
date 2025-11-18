# pylint: disable=wrong-import-order
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Załaduj zmienne środowiskowe
load_dotenv('.env.dev')

# Konfiguracja S3 (MinIO)
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'http://localhost:9000')
MINIO_PUBLIC_URL = os.getenv('MINIO_PUBLIC_URL')  # Publiczny URL do MinIO (opcjonalny)
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
MINIO_BUCKET = os.getenv('MINIO_BUCKET') or os.getenv('MINIO_BUCKET_NAME')  # Obsługa obu wariantów

# Kompatybilność wsteczna - jeśli nie ma MINIO_*, użyj starych zmiennych DO_SPACES_*
if not MINIO_BUCKET:
    MINIO_BUCKET = os.getenv('DO_SPACES_BUCKET')
if not MINIO_ACCESS_KEY:
    MINIO_ACCESS_KEY = os.getenv('DO_SPACES_KEY')
if not MINIO_SECRET_KEY:
    MINIO_SECRET_KEY = os.getenv('DO_SPACES_SECRET')
if MINIO_ENDPOINT == 'http://localhost:9000' and os.getenv('DO_SPACES_REGION'):
    # Jeśli ustawiono DO_SPACES_REGION, użyj go do budowania endpointu
    MINIO_ENDPOINT = f"https://{os.getenv('DO_SPACES_REGION')}.digitaloceanspaces.com"

# Eksportuj dla kompatybilności wstecznej
DO_SPACES_BUCKET = MINIO_BUCKET
DO_SPACES_REGION = os.getenv('DO_SPACES_REGION', 'us-east-1')

# Inicjalizacja klienta S3 (MinIO)
s3_client = boto3.client('s3',
                         endpoint_url=MINIO_ENDPOINT,
                         aws_access_key_id=MINIO_ACCESS_KEY,
                         aws_secret_access_key=MINIO_SECRET_KEY,
                         region_name=DO_SPACES_REGION
                         )


def upload_image_to_bucket_and_get_url(image_path, product_id, producer_color_name=None, image_number=1):
    """
    Upload obrazu do MinIO bucket

    Args:
        image_path (str): URL lub ścieżka do obrazu
        product_id (int): ID produktu
        producer_color_name (str): Nazwa koloru producenta (opcjonalne)
        image_number (int): Numer obrazu (opcjonalne)

    Returns:
        str: URL przesłanego obrazu lub None w przypadku błędu
    """
    try:
        # Sprawdź konfigurację MinIO przed rozpoczęciem
        if not MINIO_BUCKET:
            logger.error("MINIO_BUCKET nie jest ustawiony! Sprawdź zmienne środowiskowe.")
            return None
        
        if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
            logger.error("MINIO_ACCESS_KEY lub MINIO_SECRET_KEY nie są ustawione! Sprawdź zmienne środowiskowe.")
            return None
        
        logger.info(f"Konfiguracja MinIO: endpoint={MINIO_ENDPOINT}, bucket={MINIO_BUCKET}, access_key={'***' if MINIO_ACCESS_KEY else 'BRAK'}")
        logger.info(
            f"Rozpoczynam przesyłanie zdjęcia: {image_path} dla produktu {product_id}")

        # Sprawdź środowisko - użyj Django settings jeśli dostępne, w przeciwnym razie sprawdź DJANGO_SETTINGS_MODULE
        try:
            is_production = not settings.DEBUG if hasattr(settings, 'DEBUG') else False
        except:
            is_production = os.getenv("DJANGO_SETTINGS_MODULE", '').endswith('.prod')
        
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
                # Dodaj headers aby uniknąć blokowania przez serwer
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8',
                    'Referer': 'http://matterhorn-wholesale.com/'
                }
                
                # Spróbuj najpierw z oryginalnym URL
                response = requests.get(image_path, stream=True, timeout=30, headers=headers, allow_redirects=True)
                
                # Jeśli status 500, spróbuj z https:// zamiast http://
                if response.status_code == 500 and image_path.startswith('http://'):
                    https_url = image_path.replace('http://', 'https://', 1)
                    logger.info(f"Status 500, próbuję z https://: {https_url}")
                    response = requests.get(https_url, stream=True, timeout=30, headers=headers, allow_redirects=True)
                    if response.status_code == 200:
                        image_path = https_url  # Zaktualizuj image_path dla dalszego użycia
                
                if response.status_code != 200:
                    error_msg = f"Nie można pobrać pliku z URL: {image_path}. Status code: {response.status_code}"
                    
                    # Sprawdź czy to może być problem z Cloudflare
                    if response.status_code == 500 or response.status_code == 502 or response.status_code == 503:
                        error_msg += " (Możliwa awaria Cloudflare/CDN)"
                        logger.warning(f"⚠️ {error_msg}")
                        logger.warning("Cloudflare może mieć awarię - zdjęcie nie może być pobrane z serwera Matterhorn")
                    else:
                        logger.error(error_msg)
                    
                    logger.error(f"Response headers: {dict(response.headers)}")
                    logger.error(f"Response text (first 500 chars): {response.text[:500]}")
                    return None
                file_data = response.content
                logger.info(
                    f"Pobrano plik z URL, rozmiar: {len(file_data)} bajtów")
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Błąd podczas pobierania pliku z URL: {image_path}. Błąd: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None
        elif image_path.startswith('db_images/'):
            # Lokalna ścieżka - spróbuj z pełnym URL
            base_url = 'http://matterhorn-wholesale.com/'
            full_url = base_url + image_path
            logger.info(f"Konwertuję lokalną ścieżkę na URL: {full_url}")
            # Rekurencyjnie wywołaj funkcję z pełnym URL
            return upload_image_to_bucket_and_get_url(full_url, product_id, producer_color_name, image_number)
        else:
            logger.info(f"Otwieranie pliku lokalnego: {image_path}")
            if not os.path.exists(image_path):
                logger.error(f"Plik do uploadu nie istnieje: {image_path}")
                return None
            with open(image_path, 'rb') as f:
                file_data = f.read()
                logger.info(
                    f"Odczytano plik lokalny, rozmiar: {len(file_data)} bajtów")

        # Prześlij do S3/MinIO
        logger.info(f"Przesyłanie pliku do MinIO: {new_path}")
        try:
            # Określ ContentType - popraw dla różnych rozszerzeń
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp'
            }
            content_type = content_type_map.get(file_extension, f'image/{file_extension[1:]}')
            
            # Dla MinIO nie używamy ACL (publiczny dostęp jest konfigurowany przez bucket policy)
            # Dla DO Spaces używamy ACL='public-read'
            put_object_params = {
                'Bucket': MINIO_BUCKET,
                'Key': new_path,
                'Body': file_data,
                'ContentType': content_type
            }
            
            # Dodaj ACL tylko dla DO Spaces (kompatybilność wsteczna)
            if MINIO_ENDPOINT and 'digitaloceanspaces.com' in str(MINIO_ENDPOINT):
                put_object_params['ACL'] = 'public-read'
            
            # Sprawdź czy bucket istnieje przed uploadem
            try:
                s3_client.head_bucket(Bucket=MINIO_BUCKET)
                logger.info(f"Bucket {MINIO_BUCKET} istnieje i jest dostępny")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == '404' or 'NoSuchBucket' in str(e):
                    logger.error(f"Bucket {MINIO_BUCKET} nie istnieje! Utwórz bucket w MinIO.")
                    return None
                else:
                    logger.warning(f"Nie można sprawdzić bucketu {MINIO_BUCKET}: {str(e)}")
            
            # Wykonaj upload
            s3_client.put_object(**put_object_params)
            logger.info(f"✅ Plik został pomyślnie przesłany do MinIO: {new_path}")
            
            # Sprawdź czy plik rzeczywiście został przesłany
            try:
                s3_client.head_object(Bucket=MINIO_BUCKET, Key=new_path)
                logger.info(f"✅ Zweryfikowano obecność pliku w MinIO: {new_path}")
            except ClientError as e:
                logger.warning(f"⚠️ Nie można zweryfikować obecności pliku w MinIO: {str(e)}")
                
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"❌ Błąd ClientError podczas przesyłania pliku do MinIO: {error_code} - {error_message}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
        except Exception as e:
            logger.error(f"❌ Błąd podczas przesyłania pliku do MinIO: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

        # Zwróć URL
        # Dla MinIO buduj URL z endpointu, dla DO Spaces użyj starego formatu
        if MINIO_ENDPOINT and 'digitaloceanspaces.com' in str(MINIO_ENDPOINT):
            file_url = f"https://{MINIO_BUCKET}.{DO_SPACES_REGION}.digitaloceanspaces.com/{new_path}"
        elif MINIO_PUBLIC_URL and MINIO_BUCKET:
            # Użyj MINIO_PUBLIC_URL jeśli jest dostępny (np. http://212.127.93.27:9100/nc-media)
            public_url_clean = str(MINIO_PUBLIC_URL).rstrip('/')
            file_url = f"{public_url_clean}/{new_path}"
            logger.info(f"MinIO public URL: {MINIO_PUBLIC_URL}, path: {new_path}")
        elif MINIO_ENDPOINT and MINIO_BUCKET:
            # MinIO - format URL: http://endpoint/bucket/key
            # Usuń trailing slash z endpointu jeśli istnieje
            endpoint_clean = str(MINIO_ENDPOINT).rstrip('/')
            file_url = f"{endpoint_clean}/{MINIO_BUCKET}/{new_path}"
            logger.info(f"MinIO endpoint: {MINIO_ENDPOINT}, bucket: {MINIO_BUCKET}, path: {new_path}")
        else:
            logger.error("Nie skonfigurowano MinIO ani DO Spaces")
            return None
        logger.info(f"Wygenerowany URL pliku: {file_url}")
        return file_url

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
        # Sprawdź czy bucket jest skonfigurowany
        if not MINIO_BUCKET:
            logger.warning(
                f"MINIO_BUCKET nie jest ustawiony. Pomijam usuwanie folderu dla produktu {product_id}.")
            return

        is_production = os.getenv(
            "DJANGO_SETTINGS_MODULE") == 'nc.settings.prod'
        bucket_folder = "MPD" if is_production else "MPD_test"
        prefix = f"{bucket_folder}/{product_id}/"

        # Sprawdź czy bucket istnieje przed operacją
        try:
            s3_client.head_bucket(Bucket=MINIO_BUCKET)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404' or 'NoSuchBucket' in str(e):
                logger.warning(
                    f"Bucket {MINIO_BUCKET} nie istnieje. Pomijam usuwanie folderu {prefix}.")
                return
            else:
                # Inny błąd - rzuć dalej
                raise

        # Pobierz listę obiektów do usunięcia
        response = s3_client.list_objects_v2(
            Bucket=MINIO_BUCKET, Prefix=prefix)

        if 'Contents' in response:
            for obj in response['Contents']:
                s3_client.delete_object(
                    Bucket=MINIO_BUCKET, Key=obj['Key'])
            logger.info(f"Usunięto folder {prefix} z bucketa.")
        else:
            logger.info(f"Folder {prefix} nie istnieje w buckecie lub jest pusty.")

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'NoSuchBucket' or 'NoSuchBucket' in str(e):
            logger.warning(
                f"Bucket {MINIO_BUCKET} nie istnieje. Pomijam usuwanie folderu {prefix}.")
        else:
            logger.error(
                f"Błąd podczas usuwania folderu {prefix} z bucketa: {str(e)}")
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
        uploaded_url = upload_image_to_bucket_and_get_url(
            image_url=image_url,
            product_id=product_id,
            color_name=color_name,
            image_number=i
        )

        if uploaded_url:
            uploaded_urls.append({
                'original_url': image_url,
                'uploaded_url': uploaded_url,
                'order': image_data.get('order', i)
            })

    return uploaded_urls
