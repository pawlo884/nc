#!/usr/bin/env python
"""
Test sprawdzający mapped_product_uid dla produktów utworzonych przez automatyzację
"""
import os
import sys
import django

# Ustaw Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

from matterhorn1.models import Product, Brand

print("=" * 60)
print("🧪 TEST MAPOWANIA PRODUKTÓW")
print("=" * 60)
print()

# Znajdź markę Marko
try:
    marko_brand = Brand.objects.get(brand_id=28)
    print(f"Marka: {marko_brand.name} (ID: {marko_brand.id})")
except Brand.DoesNotExist:
    print("❌ Nie znaleziono marki Marko (brand_id=28)")
    sys.exit(1)

print()

# Sprawdź konkretne produkty które były przetwarzane przez automatyzację
# Z logów: 13773, 13690, 13676, 13656, 13646
product_ids = [13773, 13690, 13676, 13656, 13646, 13764, 13753, 13742, 13713, 13700]

print(f"📦 Produkty przetworzone przez automatyzację:")
print()

for product_id in product_ids:
    try:
        product = Product.objects.get(id=product_id)
        images_count = product.images.count()
        print(f"  Django ID: {product.id}")
        print(f"    product_uid (Matterhorn): {product.product_uid}")
        print(f"    Nazwa: {product.name[:60]}...")
        print(f"    Brand: {product.brand.name if product.brand else 'BRAK'}")
        print(f"    is_mapped: {product.is_mapped}")
        print(f"    mapped_product_uid (MPD): {product.mapped_product_uid}")
        print(f"    Liczba zdjęć: {images_count}")
        
        if images_count > 0:
            print(f"    Zdjęcia:")
            for img in product.images.all()[:3]:
                print(f"      - {img.image_url[:80]}...")
        
        # Sprawdź czy w MinIO są zdjęcia dla tego produktu
        if product.mapped_product_uid:
            import boto3
            from matterhorn1.defs_db import MINIO_BUCKET, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
            from django.conf import settings
            
            is_production = not settings.DEBUG if hasattr(settings, 'DEBUG') else False
            bucket_folder = "MPD" if is_production else "MPD_test"
            
            s3_client = boto3.client(
                's3',
                endpoint_url=MINIO_ENDPOINT,
                aws_access_key_id=MINIO_ACCESS_KEY,
                aws_secret_access_key=MINIO_SECRET_KEY,
                region_name=os.getenv('DO_SPACES_REGION', 'us-east-1')
            )
            
            try:
                # W MinIO ścieżka używa mapped_product_uid (UID z MPD), nie Django id
                prefix = f"{bucket_folder}/{product.mapped_product_uid}/"
                response = s3_client.list_objects_v2(
                    Bucket=MINIO_BUCKET,
                    Prefix=prefix,
                    MaxKeys=10
                )
                if 'Contents' in response:
                    print(f"    ✅ W MinIO (folder {product.mapped_product_uid}/): {len(response['Contents'])} plików")
                    for obj in response['Contents'][:3]:
                        print(f"      - {obj['Key']}")
                else:
                    print(f"    ❌ W MinIO (folder {product.mapped_product_uid}/): BRAK zdjęć")
            except Exception as e:
                print(f"    ⚠️  Błąd sprawdzania MinIO: {str(e)}")
        
        print()
    except Product.DoesNotExist:
        print(f"  ID: {product_id} - ❌ Nie znaleziono")
        print()

print("=" * 60)

