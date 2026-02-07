#!/usr/bin/env python
"""
Skrypt diagnostyczny do sprawdzania połączeń z bazami danych.
Sprawdza dostępność wszystkich skonfigurowanych baz danych.
"""
import os
import sys
import time
from pathlib import Path

# Dodaj ścieżkę projektu do PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Ustaw settings przed importem Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')

import django
django.setup()

from django.conf import settings
from django.db import connections
import psycopg2
from psycopg2 import OperationalError

def check_connection(db_name, db_config):
    """Sprawdza połączenie z bazą danych."""
    print(f"\n{'='*60}")
    print(f"Sprawdzanie połączenia: {db_name}")
    print(f"{'='*60}")
    
    host = db_config.get('HOST')
    port = db_config.get('PORT')
    name = db_config.get('NAME')
    user = db_config.get('USER')
    password = db_config.get('PASSWORD', '***')
    options = db_config.get('OPTIONS', {})
    connect_timeout = options.get('connect_timeout', 5)
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {name}")
    print(f"User: {user}")
    print(f"Connect Timeout: {connect_timeout}s")
    
    # Sprawdź konfigurację retry
    retry_config = getattr(settings, 'DATABASE_RETRY_CONFIG', {})
    if retry_config:
        print(f"Retry Config:")
        print(f"  Max Retries: {retry_config.get('max_retries', 3)}")
        print(f"  Retry Delay: {retry_config.get('retry_delay', 2)}s")
        print(f"  Exponential Backoff: {retry_config.get('retry_backoff', True)}")
    else:
        print("Retry Config: Nie skonfigurowane")
    
    # Test 1: Podstawowe połączenie psycopg2
    print("\n[Test 1] Podstawowe połączenie psycopg2...")
    try:
        start_time = time.time()
        conn_params = {
            'host': host,
            'port': port,
            'database': name,
            'user': user,
            'password': password,
            'connect_timeout': connect_timeout,
        }
        # Dodaj opcje z OPTIONS
        if 'keepalives' in options:
            conn_params.update({
                'keepalives': options.get('keepalives'),
                'keepalives_idle': options.get('keepalives_idle', 60),
                'keepalives_interval': options.get('keepalives_interval', 10),
                'keepalives_count': options.get('keepalives_count', 5),
            })
        
        conn = psycopg2.connect(**conn_params)
        elapsed = time.time() - start_time
        print(f"✓ Połączenie udane! (czas: {elapsed:.2f}s)")
        
        # Wykonaj prosty test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✓ PostgreSQL Version: {version.split(',')[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except OperationalError as e:
        elapsed = time.time() - start_time
        print(f"✗ Błąd połączenia (czas próby: {elapsed:.2f}s)")
        print(f"  Błąd: {str(e)}")
        return False
    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        print(f"✗ Nieoczekiwany błąd (czas próby: {elapsed:.2f}s)")
        print(f"  Błąd: {type(e).__name__}: {str(e)}")
        return False
    
    # Test 2: Połączenie przez Django
    print("\n[Test 2] Połączenie przez Django ORM...")
    try:
        start_time = time.time()
        connection = connections[db_name]
        connection.ensure_connection()
        elapsed = time.time() - start_time
        print(f"✓ Django connection udane! (czas: {elapsed:.2f}s)")
        
        # Test query
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()
            print(f"✓ Test query udany: {result[0]}")
        
        return True
        
    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        print(f"✗ Błąd Django connection (czas próby: {elapsed:.2f}s)")
        print(f"  Błąd: {type(e).__name__}: {str(e)}")
        return False

def main():
    """Główna funkcja."""
    print("\n" + "="*60)
    print("DIAGNOSTYKA POŁĄCZEŃ Z BAZAMI DANYCH")
    print("="*60)
    
    databases = settings.DATABASES
    results = {}
    
    for db_name, db_config in databases.items():
        # Pomiń bazy testowe
        if 'test' in db_name.lower():
            continue
        
        results[db_name] = check_connection(db_name, db_config)
        time.sleep(0.5)  # Krótka przerwa między testami
    
    # Podsumowanie
    print("\n" + "="*60)
    print("PODSUMOWANIE")
    print("="*60)
    
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    
    for db_name, success in results.items():
        status = "✓ OK" if success else "✗ BŁĄD"
        print(f"{status:8} - {db_name}")
    
    print(f"\nPomyślne połączenia: {successful}/{total}")
    
    if successful < total:
        print("\n⚠️  Uwaga: Niektóre bazy danych są niedostępne!")
        print("   Sprawdź:")
        print("   1. Czy serwer PostgreSQL jest uruchomiony")
        print("   2. Czy firewall pozwala na połączenia")
        print("   3. Czy dane dostępowe są poprawne")
        print("   4. Czy zwiększenie connect_timeout pomaga")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

