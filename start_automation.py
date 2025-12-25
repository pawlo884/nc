#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prosty skrypt do uruchomienia automatyzacji przez Django shell
"""
import os
import sys
import django

# Załaduj .env.dev PRZED Django
from dotenv import load_dotenv
load_dotenv('.env.dev')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

# Import funkcji
from web_agent.tasks import automate_mpd_form_filling

# Parametry
brand_id = 174  # Marko
category_id = 13  # Kostiumy Dwuczęciowe
limit = 1

print(f"🚀 Uruchamiam automatyzację:")
print(f"   Marka ID: {brand_id}")
print(f"   Kategoria ID: {category_id}")
print(f"   Limit: {limit}")

# Uruchom task (synchronicznie dla testu)
result = automate_mpd_form_filling.delay(
    brand_id=brand_id,
    category_id=category_id,
    filters={'active': True, 'is_mapped': False}
)

print(f"\n✅ Task uruchomiony! ID: {result.id}")
print(f"   Status: {result.status}")
print(f"\nMożesz sprawdzić postęp w admin: http://localhost:8000/admin/web_agent/automationrun/")

