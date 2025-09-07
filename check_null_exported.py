#!/usr/bin/env python
from django.db import connection
from MPD.models import Products
import os
import django

# Ustaw Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings')
django.setup()


# Sprawdź ile produktów ma exported_to_iai=NULL
with connection.cursor() as cursor:
    cursor.execute(
        "SELECT COUNT(*) FROM products WHERE exported_to_iai IS NULL")
    null_count = cursor.fetchone()[0]
    print(f'Produkty z exported_to_iai=NULL: {null_count}')

    cursor.execute(
        "SELECT COUNT(*) FROM products WHERE exported_to_iai = true")
    true_count = cursor.fetchone()[0]
    print(f'Produkty z exported_to_iai=True: {true_count}')

    cursor.execute(
        "SELECT COUNT(*) FROM products WHERE exported_to_iai = false")
    false_count = cursor.fetchone()[0]
    print(f'Produkty z exported_to_iai=False: {false_count}')

    # Sprawdź produkty 373, 374, 1048
    cursor.execute(
        "SELECT id, exported_to_iai FROM products WHERE id IN (373, 374, 1048)")
    products = cursor.fetchall()
    print(f'\nProdukty 373, 374, 1048:')
    for product_id, exported_to_iai in products:
        print(f'  Produkt {product_id}: exported_to_iai={exported_to_iai}')
