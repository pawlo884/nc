#!/usr/bin/env python
"""
Skrypt do bezpośredniego uruchomienia agenta z widoczną przeglądarką
Użycie: python web_agent/run_agent.py --task-id 2
"""
import os
import sys
import django

# Konfiguracja Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

import argparse
from web_agent.models import WebAgentTask
from web_agent.tasks import start_web_agent_task

def main():
    parser = argparse.ArgumentParser(description='Uruchom agenta web z widoczną przeglądarką')
    parser.add_argument('--task-id', type=int, default=2, help='ID zadania (domyślnie: 2)')
    parser.add_argument('--headless', action='store_true', help='Uruchom w trybie headless')
    
    args = parser.parse_args()
    
    # Pobierz zadanie
    task = WebAgentTask.objects.using('zzz_web_agent').get(id=args.task_id)
    
    # Ustaw headless w konfiguracji
    if not args.headless:
        task.config['headless'] = False
        task.save()
        print(f'Ustawiono headless=False dla zadania {args.task_id}')
    
    print('=' * 80)
    print('URUCHAMIANIE AGENTA')
    print('=' * 80)
    print(f'Zadanie: {task.name}')
    print(f'URL: {task.url}')
    print(f'Headless: {task.config.get("headless", True)}')
    print('=' * 80)
    print('')
    print('Przeglądarka Playwright będzie widoczna!')
    print('Możesz obserwować jak agent działa...')
    print('')
    print('Uruchamianie...')
    print('')
    
    # Uruchom zadanie
    try:
        result = start_web_agent_task(task.id)
        task.refresh_from_db()
        
        print('')
        print('=' * 80)
        print(f'Status: {task.status}')
        print(f'Zakończono: {task.completed_at}')
        if task.error_message:
            print(f'Błąd: {task.error_message}')
        print('=' * 80)
        
    except Exception as e:
        print(f'❌ Błąd: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

