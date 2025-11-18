#!/usr/bin/env python
"""
Skrypt testowy do sprawdzenia połączenia z MinIO
Uruchom: python test_minio.py
"""
import os
import sys
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Załaduj zmienne środowiskowe
load_dotenv('.env.dev')

# Konfiguracja MinIO
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'http://localhost:9000')
MINIO_PUBLIC_URL = os.getenv('MINIO_PUBLIC_URL')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
MINIO_BUCKET = os.getenv('MINIO_BUCKET') or os.getenv(
    'MINIO_BUCKET_NAME')  # Obsługa obu wariantów

# Kompatybilność wsteczna
if not MINIO_BUCKET:
    MINIO_BUCKET = os.getenv('DO_SPACES_BUCKET')
if not MINIO_ACCESS_KEY:
    MINIO_ACCESS_KEY = os.getenv('DO_SPACES_KEY')
if not MINIO_SECRET_KEY:
    MINIO_SECRET_KEY = os.getenv('DO_SPACES_SECRET')
if MINIO_ENDPOINT == 'http://localhost:9000' and os.getenv('DO_SPACES_REGION'):
    MINIO_ENDPOINT = f"https://{os.getenv('DO_SPACES_REGION')}.digitaloceanspaces.com"

DO_SPACES_REGION = os.getenv('DO_SPACES_REGION', 'us-east-1')

# Wyświetl wszystkie zmienne związane z MinIO/DO Spaces
print("🔍 Dostępne zmienne środowiskowe:")
minio_vars = {
    'MINIO_ENDPOINT': os.getenv('MINIO_ENDPOINT'),
    'MINIO_PUBLIC_URL': os.getenv('MINIO_PUBLIC_URL'),
    'MINIO_BUCKET': os.getenv('MINIO_BUCKET'),
    'MINIO_BUCKET_NAME': os.getenv('MINIO_BUCKET_NAME'),
    'MINIO_ACCESS_KEY': os.getenv('MINIO_ACCESS_KEY'),
    'MINIO_SECRET_KEY': os.getenv('MINIO_SECRET_KEY'),
    'DO_SPACES_BUCKET': os.getenv('DO_SPACES_BUCKET'),
    'DO_SPACES_KEY': os.getenv('DO_SPACES_KEY'),
    'DO_SPACES_SECRET': os.getenv('DO_SPACES_SECRET'),
    'DO_SPACES_REGION': os.getenv('DO_SPACES_REGION'),
}
for key, value in minio_vars.items():
    if value:
        display_value = '***' if 'KEY' in key or 'SECRET' in key else value
        print(f"   {key}: {display_value}")
    else:
        print(f"   {key}: BRAK")
print()

print("=" * 60)
print("🧪 TEST POŁĄCZENIA Z MINIO")
print("=" * 60)
print(f"Endpoint: {MINIO_ENDPOINT}")
print(f"Bucket: {MINIO_BUCKET}")
print(f"Access Key: {'***' if MINIO_ACCESS_KEY else 'BRAK'}")
print(f"Secret Key: {'***' if MINIO_SECRET_KEY else 'BRAK'}")
print(f"Region: {DO_SPACES_REGION}")
print()

# Sprawdź konfigurację
if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
    print("❌ MINIO_ACCESS_KEY lub MINIO_SECRET_KEY nie są ustawione!")
    sys.exit(1)

# Inicjalizacja klienta S3 (MinIO)
try:
    s3_client = boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name=DO_SPACES_REGION
    )
    print("✅ Klient S3 zainicjalizowany")
except Exception as e:
    print(f"❌ Błąd inicjalizacji klienta S3: {str(e)}")
    sys.exit(1)

# Test 1: Listowanie bucketów
print("\n📋 Test 1: Listowanie bucketów...")
try:
    response = s3_client.list_buckets()
    buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
    print(f"✅ Znaleziono {len(buckets)} bucketów:")
    for bucket in buckets:
        print(f"   - {bucket}")

    # Jeśli MINIO_BUCKET nie jest ustawiony, użyj pierwszego dostępnego
    if not MINIO_BUCKET:
        if buckets:
            MINIO_BUCKET = buckets[0]
            print(
                f"\n⚠️  MINIO_BUCKET nie był ustawiony - używam pierwszego dostępnego: '{MINIO_BUCKET}'")
        else:
            print("❌ Brak dostępnych bucketów!")
            sys.exit(1)
    elif MINIO_BUCKET not in buckets:
        print(f"⚠️  Bucket '{MINIO_BUCKET}' nie istnieje w liście!")
        print(
            f"   Dostępne buckety: {', '.join(buckets) if buckets else 'BRAK'}")
        if buckets:
            MINIO_BUCKET = buckets[0]
            print(f"   Używam pierwszego dostępnego: '{MINIO_BUCKET}'")
        else:
            sys.exit(1)
except ClientError as e:
    error_code = e.response.get('Error', {}).get('Code', '')
    error_message = e.response.get('Error', {}).get('Message', str(e))
    print(f"❌ Błąd listowania bucketów: {error_code} - {error_message}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Nieoczekiwany błąd: {str(e)}")
    sys.exit(1)

# Test 2: Sprawdzenie czy bucket istnieje
print(f"\n📋 Test 2: Sprawdzanie czy bucket '{MINIO_BUCKET}' istnieje...")
try:
    s3_client.head_bucket(Bucket=MINIO_BUCKET)
    print(f"✅ Bucket '{MINIO_BUCKET}' istnieje i jest dostępny")
except ClientError as e:
    error_code = e.response.get('Error', {}).get('Code', '')
    error_message = e.response.get('Error', {}).get('Message', str(e))
    if error_code == '404' or 'NoSuchBucket' in str(e):
        print(f"❌ Bucket '{MINIO_BUCKET}' nie istnieje!")
        print(f"   Utwórz bucket w MinIO lub sprawdź nazwę w zmiennych środowiskowych")
    else:
        print(f"❌ Błąd sprawdzania bucketu: {error_code} - {error_message}")
except Exception as e:
    print(f"❌ Nieoczekiwany błąd: {str(e)}")

# Test 3: Upload testowego pliku
print(f"\n📋 Test 3: Upload testowego pliku do '{MINIO_BUCKET}'...")
try:
    test_content = b"Test file content for MinIO upload"
    test_key = "MPD_test/test_upload.txt"

    s3_client.put_object(
        Bucket=MINIO_BUCKET,
        Key=test_key,
        Body=test_content,
        ContentType='text/plain'
    )
    print(f"✅ Plik testowy przesłany: {test_key}")

    # Sprawdź czy plik istnieje
    try:
        s3_client.head_object(Bucket=MINIO_BUCKET, Key=test_key)
        print(f"✅ Zweryfikowano obecność pliku w MinIO")

        # Pobierz plik z powrotem
        response = s3_client.get_object(Bucket=MINIO_BUCKET, Key=test_key)
        downloaded_content = response['Body'].read()
        if downloaded_content == test_content:
            print(f"✅ Pobrano plik z MinIO - zawartość zgodna")
        else:
            print(f"⚠️  Pobrano plik z MinIO - zawartość różna!")

        # Usuń testowy plik
        s3_client.delete_object(Bucket=MINIO_BUCKET, Key=test_key)
        print(f"✅ Usunięto testowy plik")

    except ClientError as e:
        print(f"⚠️  Nie można zweryfikować/pobrać pliku: {str(e)}")

except ClientError as e:
    error_code = e.response.get('Error', {}).get('Code', '')
    error_message = e.response.get('Error', {}).get('Message', str(e))
    print(f"❌ Błąd uploadu: {error_code} - {error_message}")
except Exception as e:
    print(f"❌ Nieoczekiwany błąd podczas uploadu: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 4: Listowanie obiektów w bucketcie
print(f"\n📋 Test 4: Listowanie obiektów w bucketcie '{MINIO_BUCKET}'...")
try:
    response = s3_client.list_objects_v2(Bucket=MINIO_BUCKET, MaxKeys=10)
    if 'Contents' in response:
        print(
            f"✅ Znaleziono {len(response['Contents'])} obiektów (pierwsze 10):")
        for obj in response['Contents'][:10]:
            print(
                f"   - {obj['Key']} ({obj['Size']} bajtów, zmodyfikowany: {obj['LastModified']})")
    else:
        print(f"ℹ️  Bucket jest pusty")
except ClientError as e:
    error_code = e.response.get('Error', {}).get('Code', '')
    error_message = e.response.get('Error', {}).get('Message', str(e))
    print(f"❌ Błąd listowania obiektów: {error_code} - {error_message}")
except Exception as e:
    print(f"❌ Nieoczekiwany błąd: {str(e)}")

print("\n" + "=" * 60)
print("✅ Test zakończony")
print("=" * 60)
