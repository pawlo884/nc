#!/usr/bin/env python
"""
Skrypt do aktualizacji zadania agenta z kategorią "Kostiumy dwuczęściowe"
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from web_agent.models import WebAgentTask
from web_agent.brand_automation import create_brand_automation_task_config
from matterhorn1.models import Category

# Znajdź kategorię "Kostiumy dwuczęściowe"
category = Category.objects.using('matterhorn1').filter(
    name__icontains='dwuczęściowe'
).first()

if not category:
    category = Category.objects.using('matterhorn1').filter(
        name__icontains='dwuczesciowe'
    ).first()

if not category:
    print('❌ Nie znaleziono kategorii "Kostiumy dwuczęściowe"')
    print('Dostępne kategorie z "dwuczęściowe":')
    cats = Category.objects.using('matterhorn1').filter(
        name__icontains='dwuczęściowe'
    ) | Category.objects.using('matterhorn1').filter(
        name__icontains='dwuczesciowe'
    )
    for cat in cats[:10]:
        print(f'  - {cat.name} (ID: {cat.id})')
    sys.exit(1)

print('='*80)
print('AKTUALIZACJA ZADANIA Z KATEGORIĄ')
print('='*80)
print('')
print(f'Kategoria: {category.name} (ID: {category.id})')
print('')

# Pobierz zadanie
task = WebAgentTask.objects.using('zzz_web_agent').get(id=2)

print(f'Aktualne zadanie: {task.name}')
print(f'  Liczba akcji: {len(task.config.get("actions", []))}')
print('')

# Utwórz pełną konfigurację dla Marko z kategorią
print('Tworzenie pełnej konfiguracji dla:')
print('  - Marka: Marko (ID: 28)')
print(f'  - Kategoria: {category.name} (ID: {category.id})')
print('  - Filtry: active=True, is_mapped=False')
print('  - URL: http://localhost:8000')
print('  - Headless: False')
print('')

new_config = create_brand_automation_task_config(
    brand_id=28,
    brand_name='Marko',
    category_id=category.id,
    category_name=category.name,
    active=True,
    is_mapped=False,
    base_url='http://localhost:8000',
    max_products=5  # Tylko 5 produktów
)

# Zaktualizuj zadanie
task.name = new_config['name']
task.url = new_config['url']
task.config = new_config['config']
task.brand_id = new_config['brand_id']
task.brand_name = new_config['brand_name']
task.status = 'pending'
task.save()

print('✅ Zadanie zaktualizowane!')
print('')
print('Nowa konfiguracja:')
print(f'  Nazwa: {task.name}')
print(f'  Liczba akcji: {len(task.config.get("actions", []))}')
print(f'  Headless: {task.config.get("headless", True)}')
print('')
print('Zadanie zawiera teraz pełną pętlę przetwarzania produktów z kategorią!')
print('='*80)

