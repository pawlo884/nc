#!/usr/bin/env python
"""
Test ręcznego wywołania uploadu zdjęć dla produktu
"""
import os
import sys
import django
import requests

# Ustaw Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

from matterhorn1.models import Product

print("=" * 60)
print("🧪 TEST UPLOADU ZDJĘĆ")
print("=" * 60)
print()

# Test dla produktu 13773
product_id = 13773

try:
    product = Product.objects.get(id=product_id)
    print(f"Produkt ID: {product.id}")
    print(f"product_uid (Matterhorn): {product.product_uid}")
    print(f"mapped_product_uid (MPD): {product.mapped_product_uid}")
    print(f"is_mapped: {product.is_mapped}")
    print(f"Liczba zdjęć: {product.images.count()}")
    print()
    
    if not product.is_mapped or not product.mapped_product_uid:
        print("❌ Produkt nie jest zmapowany!")
        sys.exit(1)
    
    # Wywołaj endpoint uploadu zdjęć
    print(f"Wywołuję endpoint: /admin/matterhorn1/product/upload-images/{product_id}/")
    
    # Musimy być zalogowani - użyjemy Django test client
    from django.test import Client
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    client = Client()
    
    # Utwórz superusera jeśli nie istnieje
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    
    # Zaloguj się
    client.force_login(admin_user)
    
    # Wywołaj endpoint
    response = client.post(f'/admin/matterhorn1/product/upload-images/{product_id}/')
    
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    
except Product.DoesNotExist:
    print(f"❌ Produkt {product_id} nie istnieje!")
except Exception as e:
    print(f"❌ Błąd: {str(e)}")
    import traceback
    traceback.print_exc()

print("=" * 60)

