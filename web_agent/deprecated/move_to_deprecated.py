#!/usr/bin/env python
"""Skrypt do przeniesienia starych plików do deprecated"""
import shutil
import os

# Zmień katalog roboczy na katalog skryptu
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

files_to_move = [
    'brand_automation.py',
    'browser_automation.py',
    'django_admin_automation.py',
    'run_agent.py',
    'update_task.py',
    'update_task_with_category.py',
    'DEMO_AGENT_PRODUCTS.md'
]

os.makedirs('deprecated', exist_ok=True)

moved = []
for file in files_to_move:
    if os.path.exists(file):
        try:
            shutil.move(file, os.path.join('deprecated', file))
            moved.append(file)
            print(f'✓ Przeniesiono: {file}')
        except Exception as e:
            print(f'✗ Błąd przy {file}: {e}')

print(f'\nPrzeniesiono {len(moved)}/{len(files_to_move)} plików do deprecated/')
