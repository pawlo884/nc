#!/usr/bin/env python
"""
Skrypt do aktualizacji zadania agenta - pełna konfiguracja
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from web_agent.models import WebAgentTask
from web_agent.brand_automation import create_brand_automation_task_config

# Pobierz zadanie
task = WebAgentTask.objects.using('zzz_web_agent').get(id=2)

print('='*80)
print('AKTUALIZACJA ZADANIA - PEŁNA KONFIGURACJA')
print('='*80)
print('')
print(f'Aktualne zadanie: {task.name}')
print(f'  Liczba akcji: {len(task.config.get("actions", []))}')
print('')

# Utwórz pełną konfigurację dla Marko
print('Tworzenie pełnej konfiguracji dla:')
print('  - Marka: Marko (ID: 28)')
print('  - Filtry: active=True, is_mapped=False')
print('  - URL: http://localhost:8080')
print('  - Headless: False')
print('')

new_config = create_brand_automation_task_config(
    brand_id=28,
    brand_name='Marko',
    active=True,
    is_mapped=False,
    base_url='http://localhost:8080',
    max_products=10
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
print(f'  Max products: {task.config.get("max_products", "nie ustawione")}')
print('')
print('Zadanie zawiera teraz pełną pętlę przetwarzania produktów!')
print('='*80)


