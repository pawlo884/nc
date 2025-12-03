#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Skrypt do uruchamiania automatyzacji z parametrami
"""
import os
import sys
import django

# Ustaw settings Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

def run_automation_with_params(brand_name, category_name=None, max_products=5):
    """
    Uruchom automatyzację dla podanej marki i kategorii
    
    Args:
        brand_name: Nazwa marki (np. 'Axami', 'DKaren')
        category_name: Nazwa kategorii (opcjonalnie)
        max_products: Maksymalna liczba produktów do przetworzenia
    """
    from django.db import connections
    from web_agent.automation.ai_processor import AIProcessor
    from web_agent.automation.browser_automation import BrowserAutomation
    from web_agent.automation.product_processor import ProductProcessor
    from web_agent.models import AutomationRun, ProductProcessingLog
    import time
    
    print("\n" + "="*70)
    print("AUTOMATYZACJA WYPELNIANIA FORMULARZY MPD")
    print("="*70)
    print(f"\nMarka: {brand_name}")
    print(f"Kategoria: {category_name if category_name else 'Wszystkie'}")
    print(f"Max produktow: {max_products}")
    print("\n" + "="*70)
    
    # Pobierz konfigurację
    base_url = os.getenv('WEB_AGENT_BASE_URL', 'http://localhost:8000')
    base_url = base_url.rstrip('/').replace('/admin', '')
    username = os.getenv('DJANGO_ADMIN_USERNAME', 'admin')
    password = os.getenv('DJANGO_ADMIN_PASSWORD', '')
    openai_key = os.getenv('OPENAI_API_KEY', '')
    
    if not password or not openai_key:
        print("\n[ERROR] Brak konfiguracji!")
        return
    
    # Utwórz AutomationRun
    run = AutomationRun.objects.create(
        status='running',
        brand_id=None,
        category_id=None,
        filters={
            'brand_name': brand_name,
            'category_name': category_name,
            'max_products': max_products
        }
    )
    print(f"\n[OK] Utworzono AutomationRun ID: {run.id}")
    
    # Pobierz produkty z bazy (dla sprawdzenia dostępności)
    print("\n=== Sprawdzanie dostepnych produktow ===")
    query = """
        SELECT p.id
        FROM product p
        LEFT JOIN brand b ON p.brand_id = b.id
        LEFT JOIN category c ON p.category_id = c.id
        WHERE p.active = true AND p.is_mapped = false
    """
    params = []
    
    if brand_name:
        query += " AND LOWER(b.name) = LOWER(%s)"
        params.append(brand_name)
    
    if category_name:
        query += " AND LOWER(c.name) LIKE LOWER(%s)"
        params.append(f"%{category_name}%")
    
    query += f" ORDER BY p.id LIMIT {max_products}"
    
    with connections['zzz_matterhorn1'].cursor() as cursor:
        cursor.execute(query, params)
        product_ids = [row[0] for row in cursor.fetchall()]
    
    print(f"[OK] Znaleziono {len(product_ids)} produktow do przetworzenia")
    
    if not product_ids:
        print("[WARNING] Brak produktow spelniajacych kryteria!")
        print(f"  Marka: {brand_name}")
        print(f"  Kategoria: {category_name if category_name else 'Wszystkie'}")
        print(f"  Active: True, is_mapped: False")
        run.status = 'completed'
        run.save()
        return
    
    print(f"[INFO] Produkty do przetworzenia: {product_ids}")
    
    # Inicjalizuj komponenty
    print("\n=== Inicjalizacja komponentow ===")
    try:
        browser = BrowserAutomation(
            base_url=base_url,
            username=username,
            password=password,
            headless=False  # WIDOCZNA PRZEGLĄDARKA
        )
        print("[OK] BrowserAutomation")
        
        ai = AIProcessor(api_key=openai_key)
        print("[OK] AIProcessor")
        
        processor = ProductProcessor(
            browser_automation=browser,
            ai_processor=ai
        )
        print("[OK] ProductProcessor")
        
    except Exception as e:
        print(f"[ERROR] Blad inicjalizacji: {e}")
        run.status = 'failed'
        run.error_message = str(e)
        run.save()
        return
    
    # Uruchom przeglądarkę
    print("\n=== Uruchamianie przegladarki ===")
    try:
        browser.start_browser()
        print("[OK] Przeglądarka uruchomiona")
        time.sleep(2)
        
        # Zaloguj się
        print("\n=== Logowanie ===")
        browser.login_to_admin()
        print("[OK] Zalogowano")
        time.sleep(2)
        
        # Przejdź do listy produktów z filtrami
        print(f"\n=== Stosowanie filtrow ===")
        filters = {
            'brand_name': brand_name,
            'category_name': category_name,
            'active': True,
            'is_mapped': False
        }
        browser.navigate_to_product_list(filters)
        print("[OK] Lista produktow z filtrami")
        time.sleep(2)
        
        # Przetwarzaj produkty
        print(f"\n{'='*70}")
        print(f"PRZETWARZANIE {len(product_ids)} PRODUKTOW")
        print(f"{'='*70}\n")
        
        for idx, product_id in enumerate(product_ids, 1):
            print(f"\n{'─'*70}")
            print(f"PRODUKT {idx}/{len(product_ids)}: ID {product_id}")
            print(f"{'─'*70}")
            
            try:
                log = ProductProcessingLog.objects.create(
                    automation_run=run,
                    product_id=product_id,
                    status='processing'
                )
                
                # Pobierz dane
                product_data = processor.get_product_from_database(product_id)
                if not product_data:
                    print(f"[WARNING] Produkt nie znaleziony w bazie")
                    log.status = 'failed'
                    log.error_message = 'Produkt nie znaleziony'
                    log.save()
                    run.products_failed += 1
                    continue
                
                log.product_name = product_data.get('name', '')[:500]
                log.save()
                
                print(f"Nazwa: {product_data.get('name', '')[:60]}...")
                
                # Pobierz warianty
                variants = processor.get_product_variants(product_id)
                print(f"Wariantow: {len(variants)}")
                
                # Przetwórz przez AI
                print("Przetwarzanie AI...")
                form_data = processor.prepare_mpd_form_data(product_data, variants)
                print("OK")
                
                # Przejdź do strony produktu
                print("Przechodzenie do strony produktu...")
                browser.navigate_to_product_change(product_id)
                time.sleep(2)
                print("OK")
                
                # Wypełnij formularz
                print("Wypelnianie formularza...")
                browser.fill_mpd_form(form_data)
                time.sleep(2)
                print("OK")
                
                # Wyślij
                print("Wysylanie...")
                browser.submit_mpd_form()
                
                # Czekaj na wynik
                result = browser.wait_for_submission_result(timeout=30)
                
                if result['success']:
                    mpd_id = result.get('mpd_product_id', 'N/A')
                    print(f"\n✓ SUKCES! MPD Product ID: {mpd_id}\n")
                    log.status = 'success'
                    log.mpd_product_id = result.get('mpd_product_id')
                    run.products_success += 1
                else:
                    print(f"\n✗ BLAD: {result.get('message', 'Unknown')}\n")
                    log.status = 'failed'
                    log.error_message = result.get('message', 'Unknown error')
                    run.products_failed += 1
                
                log.processing_data = {
                    'form_data': form_data,
                    'result': result
                }
                log.save()
                
                run.products_processed += 1
                run.save()
                
                print(f"Postep: {run.products_processed}/{len(product_ids)}")
                
                if idx < len(product_ids):
                    print("\nOczekiwanie 3 sekundy przed nastepnym produktem...")
                    time.sleep(3)
                
            except Exception as e:
                print(f"\n✗ BLAD: {e}\n")
                import traceback
                traceback.print_exc()
                
                try:
                    log.status = 'failed'
                    log.error_message = str(e)
                    log.save()
                except:
                    pass
                
                run.products_failed += 1
                run.products_processed += 1
                run.save()
        
        # Zakończ
        run.status = 'completed'
        run.save()
        
        print("\n" + "="*70)
        print("AUTOMATYZACJA ZAKONCZONA!")
        print("="*70)
        print(f"AutomationRun ID: {run.id}")
        print(f"Przetworzonych: {run.products_processed}")
        print(f"Sukcesow: {run.products_success}")
        print(f"Bledow: {run.products_failed}")
        print(f"\nWyniki: http://localhost:8000/admin/web_agent/automationrun/{run.id}/")
        print("\nPrzeglądarka pozostanie otwarta przez 10 sekund...")
        time.sleep(10)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        
        run.status = 'failed'
        run.error_message = str(e)
        run.save()
        
    finally:
        print("\n[INFO] Zamykanie przegladarki...")
        browser.close_browser()
        print("[OK] Zamknieto")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Automatyzacja wypelniania formularzy MPD')
    parser.add_argument('--brand', '-b', required=True, help='Nazwa marki (np. Axami, DKaren)')
    parser.add_argument('--category', '-c', help='Nazwa kategorii (opcjonalnie)')
    parser.add_argument('--max', '-m', type=int, default=5, help='Maksymalna liczba produktow (domyslnie 5)')
    
    args = parser.parse_args()
    
    run_automation_with_params(
        brand_name=args.brand,
        category_name=args.category,
        max_products=args.max
    )

