#!/usr/bin/env python
"""Test połączenia z MinIO API"""
import os
import sys
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError

# Załaduj zmienne środowiskowe
load_dotenv('.env.dev')

MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'https://minio-api.sowa.ch')
MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'nc-media')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
MINIO_REGION = os.getenv('MINIO_REGION', 'us-east-1')

print(f"=== Test połączenia z MinIO ===\n")
print(f"Endpoint: {MINIO_ENDPOINT}")
print(f"Bucket: {MINIO_BUCKET_NAME}")
print(f"Region: {MINIO_REGION}")
print(f"Access Key: {'[OK] ustawiony' if MINIO_ACCESS_KEY else '[BRAK]'}")
print(f"Secret Key: {'[OK] ustawiony' if MINIO_SECRET_KEY else '[BRAK]'}")
print()

if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
    print("[ERROR] Blad: Brak poświadczeń (MINIO_ACCESS_KEY lub MINIO_SECRET_KEY)")
    print("Ustaw te zmienne w pliku .env.dev")
    sys.exit(1)

try:
    # Utwórz klienta S3
    s3_client = boto3.client(
        's3',
        region_name=MINIO_REGION,
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        use_ssl=True,
        verify=True
    )
    
    print("[OK] Klient S3 utworzony pomyslnie")
    
    # Test 1: Lista bucketów
    print("\n--- Test 1: Lista bucketow ---")
    try:
        response = s3_client.list_buckets()
        buckets = [b['Name'] for b in response.get('Buckets', [])]
        print(f"[OK] Polaczenie dziala! Znaleziono {len(buckets)} bucket(ow):")
        for bucket in buckets:
            print(f"  - {bucket}")
    except Exception as e:
        print(f"[ERROR] Blad podczas listowania bucketow: {e}")
        raise
    
    # Test 2: Sprawdzenie czy bucket istnieje
    print(f"\n--- Test 2: Sprawdzenie bucketa '{MINIO_BUCKET_NAME}' ---")
    try:
        s3_client.head_bucket(Bucket=MINIO_BUCKET_NAME)
        print(f"[OK] Bucket '{MINIO_BUCKET_NAME}' istnieje i jest dostepny")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"[ERROR] Bucket '{MINIO_BUCKET_NAME}' nie istnieje")
        elif error_code == '403':
            print(f"[ERROR] Brak uprawnien do bucketa '{MINIO_BUCKET_NAME}'")
        else:
            print(f"[ERROR] Blad dostepu do bucketa: {e}")
            raise
    except Exception as e:
        print(f"[ERROR] Blad podczas sprawdzania bucketa: {e}")
        raise
    
    # Test 3: Lista obiektów w bucketcie (pierwsze 10)
    print(f"\n--- Test 3: Lista obiektow w '{MINIO_BUCKET_NAME}' (max 10) ---")
    try:
        response = s3_client.list_objects_v2(Bucket=MINIO_BUCKET_NAME, MaxKeys=10)
        if 'Contents' in response:
            print(f"[OK] Znaleziono {len(response['Contents'])} obiekt(ow):")
            for obj in response['Contents'][:10]:
                print(f"  - {obj['Key']} ({obj['Size']} bajtow)")
        else:
            print("[OK] Bucket jest pusty")
    except Exception as e:
        print(f"[ERROR] Blad podczas listowania obiektow: {e}")
        raise
    
    print("\n[SUCCESS] Wszystkie testy zakonczone pomyslnie!")
    print("MinIO API jest dostepne i dziala poprawnie.")
    
except EndpointConnectionError as e:
    print(f"\n[ERROR] Blad polaczenia z endpointem: {e}")
    print(f"Sprawdz czy {MINIO_ENDPOINT} jest dostepny")
    sys.exit(1)
except NoCredentialsError as e:
    print(f"\n[ERROR] Blad poswiadczen: {e}")
    print("Sprawdz czy MINIO_ACCESS_KEY i MINIO_SECRET_KEY sa ustawione w .env.dev")
    sys.exit(1)
except ClientError as e:
    error_code = e.response['Error']['Code']
    error_msg = e.response['Error']['Message']
    print(f"\n[ERROR] Blad S3 API: {error_code} - {error_msg}")
    sys.exit(1)
except Exception as e:
    print(f"\n[ERROR] Nieoczekiwany blad: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
