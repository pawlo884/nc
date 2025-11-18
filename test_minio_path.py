#!/usr/bin/env python
"""
Test sprawdzający ścieżki w MinIO dla produktów
"""
import os
import sys
import django

# Ustaw Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

from django.conf import settings
from matterhorn1.defs_db import MINIO_BUCKET, MINIO_ENDPOINT, MINIO_PUBLIC_URL
import boto3
from botocore.exceptions import ClientError

print("=" * 60)
print("🧪 TEST ŚCIEŻEK W MINIO")
print("=" * 60)
print(f"Bucket: {MINIO_BUCKET}")
print(f"Endpoint: {MINIO_ENDPOINT}")
print(f"Public URL: {MINIO_PUBLIC_URL}")
print(f"DEBUG: {settings.DEBUG}")
print()

# Sprawdź folder (MPD_test w dev, MPD w prod)
is_production = not settings.DEBUG if hasattr(settings, 'DEBUG') else False
bucket_folder = "MPD" if is_production else "MPD_test"
print(f"Środowisko: {'produkcyjne' if is_production else 'testowe'}")
print(f"Folder w bucketcie: {bucket_folder}")
print()

# Inicjalizacja klienta S3
s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=os.getenv('MINIO_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('MINIO_SECRET_KEY'),
    region_name=os.getenv('DO_SPACES_REGION', 'us-east-1')
)

# Sprawdź strukturę folderów w bucketcie
print(f"📁 Sprawdzanie struktury folderów w bucketcie '{MINIO_BUCKET}':")
print()

try:
    # Listuj obiekty w folderze MPD_test
    response = s3_client.list_objects_v2(
        Bucket=MINIO_BUCKET,
        Prefix=f"{bucket_folder}/",
        MaxKeys=50
    )
    
    if 'Contents' in response:
        print(f"✅ Znaleziono {len(response['Contents'])} obiektów w folderze '{bucket_folder}/':")
        print()
        
        # Grupuj po produktach
        products = {}
        for obj in response['Contents']:
            key = obj['Key']
            # Format: MPD_test/{product_id}/{filename}
            parts = key.split('/')
            if len(parts) >= 3:
                product_id = parts[1]
                filename = parts[2]
                if product_id not in products:
                    products[product_id] = []
                products[product_id].append({
                    'filename': filename,
                    'size': obj['Size'],
                    'modified': obj['LastModified']
                })
        
        print(f"📦 Znaleziono {len(products)} produktów z zdjęciami:")
        print()
        for product_id, images in sorted(products.items())[:10]:  # Pokaż pierwsze 10
            print(f"  Produkt {product_id}: {len(images)} zdjęć")
            for img in images[:3]:  # Pokaż pierwsze 3 zdjęcia
                print(f"    - {img['filename']} ({img['size']} bajtów)")
            if len(images) > 3:
                print(f"    ... i {len(images) - 3} więcej")
            print()
    else:
        print(f"ℹ️  Folder '{bucket_folder}/' jest pusty lub nie istnieje")
        print()
        
        # Sprawdź czy są inne foldery
        response_all = s3_client.list_objects_v2(
            Bucket=MINIO_BUCKET,
            Delimiter='/',
            MaxKeys=100
        )
        
        if 'CommonPrefixes' in response_all:
            print(f"📁 Dostępne foldery w bucketcie:")
            for prefix in response_all['CommonPrefixes']:
                print(f"  - {prefix['Prefix']}")
        
except ClientError as e:
    error_code = e.response.get('Error', {}).get('Code', '')
    error_message = e.response.get('Error', {}).get('Message', str(e))
    print(f"❌ Błąd listowania obiektów: {error_code} - {error_message}")

print("=" * 60)

