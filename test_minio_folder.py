#!/usr/bin/env python
"""
Test sprawdzający czy folder MPD_test jest używany w środowisku dev
"""
import os
import sys
import django

# Ustaw Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

from django.conf import settings
from matterhorn1.defs_db import upload_image_to_bucket_and_get_url

print("=" * 60)
print("🧪 TEST FOLDERU W ŚRODOWISKU DEV")
print("=" * 60)
print(f"DJANGO_SETTINGS_MODULE: {os.getenv('DJANGO_SETTINGS_MODULE')}")
print(f"DEBUG: {settings.DEBUG}")
print(f"Środowisko: {'DEV' if settings.DEBUG else 'PROD'}")

# Sprawdź logikę wyboru folderu
try:
    is_production = not settings.DEBUG if hasattr(settings, 'DEBUG') else False
except:
    is_production = os.getenv("DJANGO_SETTINGS_MODULE", '').endswith('.prod')

bucket_folder = "MPD" if is_production else "MPD_test"
print(f"Wybrany folder: {bucket_folder}")

if bucket_folder == "MPD_test":
    print("✅ Poprawnie wykryto środowisko DEV - używany folder MPD_test")
else:
    print(f"❌ Błędny folder: {bucket_folder} (powinien być MPD_test w dev)")

print("=" * 60)

