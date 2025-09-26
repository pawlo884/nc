#!/usr/bin/env python
from MPD.models import Products
import os
import django

# Ustaw Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings')
django.setup()


# Sprawdź produkt główny 1048 (który ma warianty 373, 374)
p1048 = Products.objects.using('MPD').filter(id=1048).first()

print(
    f'Produkt 1048: exported_to_iai={p1048.exported_to_iai if p1048 else "nie znaleziono"}')
print(f'Produkt 1048: name={p1048.name if p1048 else "nie znaleziono"}')

# Sprawdź ile produktów ma exported_to_iai=True
total_exported = Products.objects.using(
    'MPD').filter(exported_to_iai=True).count()
print(f'Łącznie produktów z exported_to_iai=True: {total_exported}')

# Sprawdź czy są produkty z exported_to_iai=False
total_not_exported = Products.objects.using(
    'MPD').filter(exported_to_iai=False).count()
print(f'Łącznie produktów z exported_to_iai=False: {total_not_exported}')
