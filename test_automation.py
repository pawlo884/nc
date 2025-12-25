#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Skrypt testowy dla automatyzacji web_agent
"""
import os
import sys
import django

# Ustaw settings Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

from django.db import connections
from web_agent.automation.ai_processor import AIProcessor
from web_agent.automation.browser_automation import BrowserAutomation
from web_agent.automation.product_processor import ProductProcessor
from web_agent.models import AutomationRun, ProductProcessingLog

def test_config():
    """Test konfiguracji"""
    print("=== Test konfiguracji ===\n")
    
    base_url = os.getenv('WEB_AGENT_BASE_URL', 'http://localhost:8000')
    base_url = base_url.rstrip('/').replace('/admin', '')
    username = os.getenv('DJANGO_ADMIN_USERNAME', 'admin')
    password = os.getenv('DJANGO_ADMIN_PASSWORD', '')
    openai_key = os.getenv('OPENAI_API_KEY', '')
    
    print(f"[OK] BASE_URL: {base_url}")
    print(f"[OK] USERNAME: {username}")
    print(f"[OK] PASSWORD: {'SET' if password else 'NOT SET'}")
    print(f"[OK] OPENAI_KEY: {'SET' if openai_key else 'NOT SET'}")
    
    if not password or not openai_key:
        print("\n[ERROR] Brakuje konfiguracji!")
        return False
    
    return True

def test_ai():
    """Test AI Processor"""
    print("\n=== Test AI Processor ===")
    try:
        ai = AIProcessor()
        test_text = "Piekna sukienka letnia"
        result = ai.create_short_description(test_text)
        print(f"[OK] AI dziala")
        print(f"  Input: {test_text}")
        print(f"  Output: {result[:100]}...")
        return True
    except Exception as e:
        print(f"[ERROR] Blad AI: {e}")
        return False

def get_test_products(limit=2):
    """Pobierz produkty do testu"""
    print(f"\n=== Pobieranie {limit} produktów do testu ===")
    with connections['zzz_matterhorn1'].cursor() as cursor:
        cursor.execute("""
            SELECT p.id, p.name, b.name as brand
            FROM product p
            LEFT JOIN brand b ON p.brand_id = b.id
            WHERE p.active = true AND p.is_mapped = false
            ORDER BY p.id
            LIMIT %s
        """, [limit])
        products = cursor.fetchall()
    
    print(f"[OK] Znaleziono {len(products)} produktow:")
    for prod in products:
        # Bezpieczne wyświetlanie - zamiana problematycznych znaków
        name = prod[1][:50].encode('ascii', 'replace').decode('ascii')
        print(f"  - ID {prod[0]}: {name}")
    
    return [p[0] for p in products]

def test_browser_automation():
    """Test automatyzacji przeglądarki (bez uruchamiania)"""
    print("\n=== Test inicjalizacji BrowserAutomation ===")
    try:
        base_url = os.getenv('WEB_AGENT_BASE_URL', 'http://localhost:8000').rstrip('/').replace('/admin', '')
        username = os.getenv('DJANGO_ADMIN_USERNAME', 'admin')
        password = os.getenv('DJANGO_ADMIN_PASSWORD', '')
        
        browser = BrowserAutomation(
            base_url=base_url,
            username=username,
            password=password,
            headless=False
        )
        print(f"[OK] BrowserAutomation zainicjalizowany")
        return True
    except Exception as e:
        print(f"[ERROR] Blad: {e}")
        return False

def run_mini_test():
    """Uruchom mini test - tylko AI, bez przeglądarki"""
    print("\n" + "="*60)
    print("MINI TEST - Tylko przetwarzanie AI (bez przeglądarki)")
    print("="*60)
    
    # Utwórz AutomationRun
    run = AutomationRun.objects.create(
        status='running',
        brand_id=None,
        category_id=None,
        filters={'test': True}
    )
    print(f"\n[OK] Utworzono AutomationRun ID: {run.id}")
    
    # Pobierz 1 produkt
    product_ids = get_test_products(limit=1)
    
    if not product_ids:
        print("❌ Brak produktów do testu")
        return
    
    product_id = product_ids[0]
    
    # Pobierz dane produktu
    print(f"\n=== Przetwarzanie produktu ID {product_id} ===")
    from web_agent.automation.product_processor import ProductProcessor
    
    # Tylko AI bez przeglądarki
    try:
        ai = AIProcessor()
        
        # Pobierz produkt z bazy
        with connections['zzz_matterhorn1'].cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.name, p.description, b.name as brand
                FROM product p
                LEFT JOIN brand b ON p.brand_id = b.id
                WHERE p.id = %s
            """, [product_id])
            row = cursor.fetchone()
        
        if not row:
            print(f"[ERROR] Produkt {product_id} nie znaleziony")
            return
        
        print(f"\nOryginalny produkt:")
        # Bezpieczne wyświetlanie
        nazwa = row[1].encode('ascii', 'replace').decode('ascii') if row[1] else ''
        opis = row[2][:100].encode('ascii', 'replace').decode('ascii') if row[2] else '(brak)'
        marka = row[3].encode('ascii', 'replace').decode('ascii') if row[3] else ''
        print(f"  Nazwa: {nazwa}")
        print(f"  Opis: {opis}...")
        print(f"  Marka: {marka}")
        
        # Przetwórz przez AI
        print(f"\n=== Przetwarzanie przez AI ===")
        processed = ai.process_product_data({
            'name': row[1],
            'description': row[2] or '',
            'brand_name': row[3] or ''
        })
        
        print(f"\nPo przetworzeniu przez AI:")
        print(f"  Nazwa: {processed['name']}")
        print(f"  Opis: {processed['description'][:100]}...")
        print(f"  Krótki opis: {processed.get('short_description', '')[:100]}...")
        
        # Zapisz log
        log = ProductProcessingLog.objects.create(
            automation_run=run,
            product_id=product_id,
            product_name=row[1],
            status='success',
            processing_data=processed
        )
        
        run.products_processed = 1
        run.products_success = 1
        run.status = 'completed'
        run.save()
        
        print(f"\n[OK] Test zakonczony sukcesem!")
        print(f"  AutomationRun ID: {run.id}")
        print(f"  ProductLog ID: {log.id}")
        print(f"\nSprawdz w admin: http://localhost:8000/admin/web_agent/")
        
    except Exception as e:
        print(f"[ERROR] Blad podczas testu: {e}")
        import traceback
        traceback.print_exc()
        
        run.status = 'failed'
        run.error_message = str(e)
        run.save()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("TEST AUTOMATYZACJI WEB_AGENT")
    print("="*60)
    
    # Testy wstępne
    if not test_config():
        sys.exit(1)
    
    if not test_ai():
        sys.exit(1)
    
    test_browser_automation()
    
    # Mini test - automatyczne uruchomienie
    print("\n\n" + "="*60)
    print("Uruchamiam mini test (przetwarzanie 1 produktu przez AI)")
    print("To nie uruchomi przeglądarki, tylko przetworzy dane przez AI")
    print("="*60)
    
    run_mini_test()

