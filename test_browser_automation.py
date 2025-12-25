#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test pełnej automatyzacji z widoczną przeglądarką
"""
import os
import sys
import django
import time

# Ustaw settings Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

from django.db import connections
from web_agent.automation.ai_processor import AIProcessor
from web_agent.automation.browser_automation import BrowserAutomation
from web_agent.automation.product_processor import ProductProcessor
from web_agent.models import AutomationRun, ProductProcessingLog

def run_browser_test():
    """Uruchom test z widoczną przeglądarką"""
    print("\n" + "="*70)
    print("TEST AUTOMATYZACJI Z WIDOCZNA PRZEGLADARKA")
    print("="*70)
    print("\nUWAGA: Przeglądarka Chrome zostanie uruchomiona.")
    print("NIE ZAMYKAJ OKNA PRZEGLADARKI!")
    print("\nAutomatyzacja wykona:")
    print("1. Uruchomienie Chrome")
    print("2. Logowanie do admin Django")
    print("3. Przejście do listy produktów")
    print("4. Pobranie produktów (ograniczone do 2)")
    print("5. Dla każdego produktu:")
    print("   - Pobranie danych z bazy")
    print("   - Przetworzenie przez AI")
    print("   - Przejście do strony produktu")
    print("   - Wypełnienie formularza MPD")
    print("   - Wysłanie formularza")
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
        filters={'test': True, 'limit': 2}
    )
    print(f"\n[OK] Utworzono AutomationRun ID: {run.id}")
    
    # Pobierz produkty do testu (tylko 2)
    print("\n=== Pobieranie produktow do testu ===")
    with connections['zzz_matterhorn1'].cursor() as cursor:
        cursor.execute("""
            SELECT p.id
            FROM product p
            WHERE p.active = true AND p.is_mapped = false
            ORDER BY p.id
            LIMIT 2
        """)
        product_ids = [row[0] for row in cursor.fetchall()]
    
    print(f"[OK] Wybrano {len(product_ids)} produktow: {product_ids}")
    
    if not product_ids:
        print("[ERROR] Brak produktow do testu")
        run.status = 'failed'
        run.error_message = 'Brak produktów'
        run.save()
        return
    
    # Inicjalizuj komponenty
    print("\n=== Inicjalizacja komponentow ===")
    try:
        browser = BrowserAutomation(
            base_url=base_url,
            username=username,
            password=password,
            headless=False  # WIDOCZNA PRZEGLĄDARKA
        )
        print("[OK] BrowserAutomation zainicjalizowany (WIDOCZNY)")
        
        ai = AIProcessor(api_key=openai_key)
        print("[OK] AIProcessor zainicjalizowany")
        
        processor = ProductProcessor(
            browser_automation=browser,
            ai_processor=ai
        )
        print("[OK] ProductProcessor zainicjalizowany")
        
    except Exception as e:
        print(f"[ERROR] Blad inicjalizacji: {e}")
        run.status = 'failed'
        run.error_message = str(e)
        run.save()
        return
    
    # Uruchom przeglądarkę
    print("\n=== Uruchamianie przegladarki Chrome ===")
    try:
        browser.start_browser()
        print("[OK] Przeglądarka uruchomiona")
        print("\nOKNO CHROME POWINNO BYC TERAZ WIDOCZNE!")
        time.sleep(2)
        
        # Zaloguj się do admin
        print("\n=== Logowanie do admin Django ===")
        browser.login_to_admin()
        print("[OK] Zalogowano do admin")
        time.sleep(2)
        
        # Przejdź do listy produktów
        print("\n=== Przechodzenie do listy produktow ===")
        filters = {
            'brand_name': 'Axami',  # Nazwa marki do filtrowania
            'active': True,
            'is_mapped': False
        }
        print(f"[INFO] Filtry: marka={filters.get('brand_name')}, active={filters['active']}, is_mapped={filters['is_mapped']}")
        browser.navigate_to_product_list(filters)
        print("[OK] Lista produktow zaladowana z filtrami")
        time.sleep(2)
        
        # Przetwarzaj produkty
        print(f"\n=== Przetwarzanie {len(product_ids)} produktow ===")
        for idx, product_id in enumerate(product_ids, 1):
            print(f"\n--- Produkt {idx}/{len(product_ids)}: ID {product_id} ---")
            
            try:
                # Utwórz log produktu
                log = ProductProcessingLog.objects.create(
                    automation_run=run,
                    product_id=product_id,
                    status='processing'
                )
                
                # Pobierz dane produktu z bazy
                product_data = processor.get_product_from_database(product_id)
                if not product_data:
                    print(f"[WARNING] Produkt {product_id} nie znaleziony w bazie")
                    log.status = 'failed'
                    log.error_message = 'Produkt nie znaleziony'
                    log.save()
                    run.products_failed += 1
                    continue
                
                log.product_name = product_data.get('name', '')
                log.save()
                
                # Pobierz warianty
                variants = processor.get_product_variants(product_id)
                print(f"[OK] Pobrano dane produktu (wariantow: {len(variants)})")
                
                # Przygotuj dane formularza (z AI)
                print("[INFO] Przetwarzanie przez AI...")
                form_data = processor.prepare_mpd_form_data(product_data, variants)
                print("[OK] Dane formularza przygotowane")
                
                # Przejdź do strony produktu
                print(f"[INFO] Przechodzenie do strony produktu {product_id}...")
                browser.navigate_to_product_change(product_id)
                time.sleep(2)
                print("[OK] Strona produktu zaladowana")
                
                # Wypełnij formularz
                print("[INFO] Wypelnianie formularza MPD...")
                browser.fill_mpd_form(form_data)
                time.sleep(2)
                print("[OK] Formularz wypelniony")
                
                # Wyślij formularz
                print("[INFO] Wysylanie formularza...")
                browser.submit_mpd_form()
                
                # Czekaj na wynik
                print("[INFO] Oczekiwanie na wynik...")
                result = browser.wait_for_submission_result(timeout=30)
                
                if result['success']:
                    print(f"[OK] Produkt {product_id} przetworzony pomyslnie!")
                    if result.get('mpd_product_id'):
                        print(f"     MPD Product ID: {result['mpd_product_id']}")
                    log.status = 'success'
                    log.mpd_product_id = result.get('mpd_product_id')
                    run.products_success += 1
                else:
                    print(f"[WARNING] Produkt {product_id} - blad: {result.get('message', 'Unknown')}")
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
                
                print(f"[INFO] Postep: {run.products_processed}/{len(product_ids)}")
                time.sleep(3)  # Pauza między produktami
                
            except Exception as e:
                print(f"[ERROR] Blad podczas przetwarzania produktu {product_id}: {e}")
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
        print("TEST ZAKONCZONY!")
        print("="*70)
        print(f"AutomationRun ID: {run.id}")
        print(f"Produktow przetworzonych: {run.products_processed}")
        print(f"Sukcesow: {run.products_success}")
        print(f"Bledow: {run.products_failed}")
        print(f"\nSprawdz wyniki: http://localhost:8000/admin/web_agent/")
        print("\nPrzeglądarka pozostanie otwarta przez 10 sekund...")
        time.sleep(10)
        
    except Exception as e:
        print(f"\n[ERROR] Blad podczas testu: {e}")
        import traceback
        traceback.print_exc()
        
        run.status = 'failed'
        run.error_message = str(e)
        run.save()
        
    finally:
        # Zamknij przeglądarkę
        print("\n[INFO] Zamykanie przegladarki...")
        browser.close_browser()
        print("[OK] Przeglądarka zamknieta")

if __name__ == '__main__':
    run_browser_test()

