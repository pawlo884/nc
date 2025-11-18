#!/usr/bin/env python
"""Test wywołania AI"""
from web_agent.brand_automation import get_brand_filter_config
from web_agent.browser_automation import BrowserAutomation
import asyncio
import sys
import os
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()


async def test_ai_call():
    print("=" * 60)
    print("TEST WYWOŁANIA AI")
    print("=" * 60)

    config = get_brand_filter_config(
        brand_id=28,
        base_url='http://localhost:8000',
        env_file='.env.dev'
    )
    config['headless'] = False

    automation = BrowserAutomation(headless=False)
    await automation.start()

    # Znajdź akcję evaluate z ai_request_prepared
    for i, action in enumerate(config['actions']):
        if action.get('type') == 'evaluate':
            expr = action.get('expression', '')
            if 'ai_request_prepared' in expr:
                print(f"\nZnaleziono akcję evaluate na pozycji {i}")
                print(f"Wywołuję evaluate...")
                try:
                    result = await automation.evaluate(expr)
                    print(f"Wynik: {result}")
                    print(f"Typ: {type(result)}")
                    if isinstance(result, dict):
                        print(
                            f"ai_request_prepared: {result.get('ai_request_prepared')}")
                        print(
                            f"original_text obecny: {bool(result.get('original_text'))}")
                        if result.get('ai_request_prepared'):
                            print(
                                "\n✅ Żądanie AI przygotowane! Sprawdzam wywołanie funkcji...")
                            from web_agent.brand_automation import edit_description_with_ai
                            original_text = result.get('original_text', '')
                            if original_text:
                                print(
                                    f"Wywołuję edit_description_with_ai z tekstem długości {len(original_text)}...")
                                edited = edit_description_with_ai(
                                    original_description=original_text,
                                    product_name=result.get(
                                        'product_name', ''),
                                    brand_name=result.get('brand_name', '')
                                )
                                print(
                                    f"Wynik edycji: długość {len(edited)} znaków")
                                print(
                                    f"Pierwsze 200 znaków: {edited[:200]}...")
                except Exception as e:
                    print(f"Błąd: {e}")
                    import traceback
                    traceback.print_exc()
                break

    await automation.stop()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(test_ai_call())
    except KeyboardInterrupt:
        print("\nPrzerwano przez użytkownika")
    except Exception as e:
        print(f"\nBłąd: {e}")
        import traceback
        traceback.print_exc()
