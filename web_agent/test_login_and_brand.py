#!/usr/bin/env python
"""
Testowy skrypt do sprawdzenia logowania i wyboru marki Marko
Użycie: python web_agent/test_login_and_brand.py
"""
import os
import sys
import django
import asyncio

# Konfiguracja Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from web_agent.agent import Agent
from web_agent.workflows import DjangoAdminWorkflow


async def main():
    print('=' * 80)
    print('TEST: Logowanie i wybór marki Marko')
    print('=' * 80)
    print('')
    
    base_url = 'http://localhost:8000'
    
    # Sprawdź czy .env.dev istnieje
    env_file = '.env.dev'
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), env_file)
    print(f'Sprawdzam plik .env.dev: {env_path}')
    if os.path.exists(env_path):
        print('✓ Plik .env.dev istnieje')
    else:
        print(f'⚠️ Plik .env.dev nie istnieje w: {env_path}')
    
    # Utwórz agenta (widoczna przeglądarka)
    agent = Agent(headless=False)
    
    try:
        # 1. Workflow logowania
        print('1. Logowanie do Django Admin...')
        print(f'   Base URL: {base_url}')
        print(f'   Plik .env: {env_file}')
        login_workflow = DjangoAdminWorkflow.create_login_workflow(
            base_url=base_url,
            env_file=env_file
        )
        agent.add_workflow(login_workflow)
        
        # 2. Workflow nawigacji do listy produktów
        print('2. Nawigacja do listy produktów...')
        products_url = f'{base_url}/admin/matterhorn1/product/'
        print(f'   URL: {products_url}')
        products_workflow = DjangoAdminWorkflow.create_navigate_to_products_workflow(products_url)
        agent.add_workflow(products_workflow)
        
        # 3. Workflow zastosowania filtrów
        print('3. Zastosowanie filtrów: active=True, is_mapped=False...')
        filters_workflow = DjangoAdminWorkflow.create_apply_filters_workflow(
            active=True,
            is_mapped=False
        )
        agent.add_workflow(filters_workflow)
        
        # Wykonaj
        print('')
        print('Uruchamianie agenta...')
        print('(Przeglądarka będzie widoczna - możesz obserwować działanie)')
        print('')
        
        # Uruchom przeglądarkę
        await agent.start()
        print('✓ Przeglądarka uruchomiona')
        print('')
        
        result = await agent.execute()
        
        print('')
        print('=' * 80)
        print('WYNIKI')
        print('=' * 80)
        print(f'Sukces: {result["success"]}')
        print(f'Workflow wykonane: {result["workflows_executed"]}')
        print(f'Całkowite akcje: {result["total_actions"]}')
        print(f'Udane akcje: {result["successful_actions"]}')
        print(f'Nieudane akcje: {result["failed_actions"]}')
        print('')
        
        # Pokaż szczegóły wszystkich akcji
        if result.get('results'):
            print('')
            print('Szczegóły akcji:')
            for i, r in enumerate(result['results'], 1):
                status = '✓' if r.get('success') else '✗'
                action_type = r.get('action_type', 'unknown')
                error = r.get('error', '')
                print(f'  {i}. {status} {action_type}', end='')
                if error:
                    print(f' - BŁĄD: {error}')
                else:
                    print()
        
        print('=' * 80)
        
    except Exception as e:
        print(f'❌ Błąd: {e}')
        import traceback
        traceback.print_exc()
        
    finally:
        print('')
        print('Zatrzymywanie agenta...')
        await agent.stop()
        print('Gotowe!')


if __name__ == '__main__':
    asyncio.run(main())

