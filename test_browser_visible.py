#!/usr/bin/env python
"""
Skrypt testowy do uruchomienia automatyzacji przeglądarki w trybie widocznym
Uruchom: python test_browser_visible.py [--brand-id ID] [--wait SECONDS]
"""
import os
import sys
import argparse
import django

# Konfiguracja Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

import asyncio
from web_agent.browser_automation import BrowserAutomation
from web_agent.brand_automation import get_brand_filter_config


async def test_browser_automation(brand_id=1, max_products=10):
    """Test automatyzacji przeglądarki w trybie widocznym"""
    print("🚀 Uruchamianie automatyzacji przeglądarki w trybie widocznym...")
    print("=" * 60)
    
    # Pobierz konfigurację dla marki
    config = get_brand_filter_config(
        brand_id=brand_id,
        base_url='http://localhost:8000',
        env_file='.env.dev',
        max_products=max_products
    )
    
    # Zmień headless na False żeby widzieć przeglądarkę
    config['headless'] = False
    
    print(f"📋 Konfiguracja:")
    print(f"   - Headless: {config['headless']}")
    print(f"   - Max products: {max_products}")
    print(f"   - Liczba akcji: {len(config['actions'])}")
    print(f"   - URL: {config['actions'][0]['url']}")
    print("=" * 60)
    print()
    
    # Utwórz instancję automatyzacji
    automation = BrowserAutomation(
        headless=config['headless'],
        browser_type='chromium'  # Używa Chrome
    )
    
    try:
        # Uruchom przeglądarkę
        print("🌐 Uruchamianie przeglądarki...")
        await automation.start()
        print("✅ Przeglądarka uruchomiona!")
        print()
        
        # Sprawdź czy CSS się ładuje przed wykonaniem akcji
        print("🔍 Sprawdzanie czy CSS się ładuje...")
        try:
            # Przejdź do strony głównej i sprawdź czy CSS jest dostępny
            await automation.navigate('http://localhost:8000/static/admin/css/base.css')
            css_content = await automation.get_page_content()
            if css_content.get('text', '').strip().startswith('/*'):
                print("✅ CSS jest dostępny!")
            else:
                print("⚠️  CSS może nie być dostępny poprawnie")
        except Exception as e:
            print(f"⚠️  Nie można sprawdzić CSS: {str(e)}")
        
        print()
        print("⚙️  Wykonywanie akcji...")
        results = await automation.execute_actions(config['actions'])
        
        # Wyświetl wyniki
        print()
        print("=" * 60)
        print("📊 WYNIKI:")
        print("=" * 60)
        for i, result in enumerate(results, 1):
            action_type = result.get('action', 'unknown')
            success = result.get('success', False)
            status = "✅" if success else "❌"
            
            print(f"{status} Akcja {i}: {action_type}")
            
            if not success:
                error = result.get('error', 'Nieznany błąd')
                print(f"   Błąd: {error}")
            else:
                action_result = result.get('result', {})
                if action_type == 'navigate':
                    print(f"   URL: {action_result.get('final_url', 'N/A')}")
                    print(f"   Tytuł: {action_result.get('title', 'N/A')}")
                elif action_type == 'evaluate':
                    print(f"   Wynik: {action_result.get('result', 'N/A')}")
        
        print()
        print("=" * 60)
        print("✅ Automatyzacja zakończona!")
        print("=" * 60)
        
        # Czekaj chwilę żeby zobaczyć wynik
        print(f"\n⏳ Automatyzacja zakończona. Przeglądarka pozostanie otwarta.")
        print("   (Zamknij ręcznie lub naciśnij Ctrl+C)")
        # Czekaj w nieskończoność - użytkownik zamknie ręcznie
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        print(f"\n❌ BŁĄD: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Zatrzymaj przeglądarkę
        print("\n🛑 Zamykanie przeglądarki...")
        await automation.stop()
        print("✅ Przeglądarka zamknięta!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Test automatyzacji przeglądarki w trybie widocznym'
    )
    parser.add_argument(
        '--brand-id',
        type=int,
        default=1,
        help='ID marki do przetestowania (domyślnie: 1)'
    )
    parser.add_argument(
        '--max-products',
        type=int,
        default=10,
        help='Maksymalna liczba produktów do przetworzenia (domyślnie: 10)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧪 TEST AUTOMATYZACJI PRZEGLĄDARKI - TRYB WIDOCZNY")
    print("=" * 60)
    print(f"   Brand ID: {args.brand_id}")
    print(f"   Max products: {args.max_products}")
    print()
    
    try:
        asyncio.run(test_browser_automation(brand_id=args.brand_id, max_products=args.max_products))
    except KeyboardInterrupt:
        print("\n\n⚠️  Przerwano przez użytkownika (Ctrl+C)")
    except Exception as e:
        print(f"\n\n❌ Błąd krytyczny: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

