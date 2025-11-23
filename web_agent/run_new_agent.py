#!/usr/bin/env python
"""
Skrypt do uruchomienia nowego agenta
Użycie: python web_agent/run_new_agent.py --task-id 2
"""
import os
import sys
import django
import asyncio

# Konfiguracja Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

import argparse
from web_agent.models import WebAgentTask
from web_agent.agent import Agent


def build_products_url(base_url: str, brand_id: int = None, category_id: int = None, 
                      active: bool = True, is_mapped: bool = False) -> str:
    """Buduje URL do listy produktów z filtrami"""
    url = f'{base_url}/admin/matterhorn1/product/'
    params = []
    
    if brand_id:
        params.append(f'brand__id__exact={brand_id}')
    if category_id:
        params.append(f'category__id__exact={category_id}')
    if active is not None:
        params.append(f'active__exact={1 if active else 0}')
    if is_mapped is not None:
        params.append(f'is_mapped__exact={1 if is_mapped else 0}')
    
    if params:
        url += '?' + '&'.join(params)
    
    return url


async def main():
    parser = argparse.ArgumentParser(description='Uruchom nowego agenta web')
    parser.add_argument('--task-id', type=int, default=2, help='ID zadania (domyślnie: 2)')
    parser.add_argument('--headless', action='store_true', help='Uruchom w trybie headless')
    
    args = parser.parse_args()
    
    # Pobierz zadanie
    task = WebAgentTask.objects.using('zzz_web_agent').get(id=args.task_id)
    
    print('=' * 80)
    print('URUCHAMIANIE NOWEGO AGENTA')
    print('=' * 80)
    print(f'Zadanie: {task.name}')
    print(f'URL: {task.url}')
    print(f'Headless: {args.headless}')
    print('=' * 80)
    print('')
    
    # Pobierz parametry z konfiguracji
    config = task.config
    base_url = task.url.split('/admin')[0] if '/admin' in task.url else task.url
    max_products = config.get('max_products', 10)
    brand_id = task.brand_id
    category_id = config.get('category_id')
    active = config.get('active', True)
    is_mapped = config.get('is_mapped', False)
    
    # Zbuduj URL produktów
    products_url = build_products_url(
        base_url=base_url,
        brand_id=brand_id,
        category_id=category_id,
        active=active,
        is_mapped=is_mapped
    )
    
    print(f'Base URL: {base_url}')
    print(f'Products URL: {products_url}')
    print(f'Max products: {max_products}')
    print('')
    print('Uruchamianie agenta...')
    print('')
    
    # Utwórz i uruchom agenta
    agent = Agent(headless=args.headless)
    
    try:
        result = await agent.execute_django_admin_product_mapping(
            base_url=base_url,
            products_url=products_url,
            max_products=max_products
        )
        
        print('')
        print('=' * 80)
        print('WYNIKI')
        print('=' * 80)
        print(f'Sukces: {result["success"]}')
        print(f'Workflow wykonane: {result["workflows_executed"]}')
        print(f'Całkowite akcje: {result["total_actions"]}')
        print(f'Udane akcje: {result["successful_actions"]}')
        print(f'Nieudane akcje: {result["failed_actions"]}')
        print('=' * 80)
        
        # Zaktualizuj zadanie
        task.status = 'completed' if result['success'] else 'failed'
        task.result = result
        task.save()
        
    except Exception as e:
        print(f'Błąd: {e}')
        import traceback
        traceback.print_exc()
        
        task.status = 'failed'
        task.error_message = str(e)
        task.save()
        
    finally:
        await agent.stop()


if __name__ == '__main__':
    asyncio.run(main())

