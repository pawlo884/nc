#!/usr/bin/env python
"""
Skrypt do uruchomienia agenta dla strony produktów Matterhorn
"""
from web_agent.django_admin_agent import navigate_to_matterhorn_products
import django
import os
import sys

# Dodaj ścieżkę do projektu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ustaw zmienne środowiskowe Django PRZED importem django!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.base')

django.setup()


def main():
    """Główna funkcja"""
    print("🚀 Uruchamiam agenta dla strony produktów Matterhorn...")
    print("📍 URL: http://localhost:8000/admin/matterhorn/products/?brand=Lupo+Line&category_name=Kostiumy+Dwuczęściowe")

    try:
        # Dane logowania (opcjonalne)
        username = os.getenv('DJANGO_ADMIN_USERNAME')
        password = os.getenv('DJANGO_ADMIN_PASSWORD')

        if username and password:
            print(f"👤 Logowanie jako: {username}")
        else:
            print("⚠️  Brak danych logowania - dostęp bez logowania")

        # Uruchom agenta
        result = navigate_to_matterhorn_products(
            brand="Lupo Line",
            category_name="Kostiumy Dwuczęściowe",
            username=username if username else None,
            password=password if password else None,
            headless=False  # Widoczna przeglądarka
        )

        # Wyświetl wyniki
        print("\n✅ Agent zakończył pracę!")
        print(f"📄 Tytuł strony: {result['title']}")
        print(f"🔗 URL: {result['current_url']}")
        print(f"🔐 Zalogowany: {result['is_logged_in']}")
        print(f"📦 Znaleziono produkty: {result['products_found']}")
        print(f"📊 Liczba produktów: {result['products_count']}")

        if result.get('screenshot_path'):
            print(f"📸 Screenshot: {result['screenshot_path']}")

        # Wyświetl produkty
        if result['products']:
            print(f"\n📋 Lista produktów ({len(result['products'])}):")
            for i, product in enumerate(result['products'][:5], 1):  # Pierwsze 5
                print(
                    f"  {i}. ID: {product['id']} | {product['name']} | {product['brand']}")

            if len(result['products']) > 5:
                print(f"  ... i {len(result['products']) - 5} więcej")

        return result

    except Exception as e:
        print(f"❌ Błąd: {e}")
        print("\n💡 Sprawdź:")
        print("   - Czy serwer Django działa na localhost:8000")
        print("   - Czy masz zainstalowane biblioteki (selenium, webdriver-manager)")
        print("   - Czy Chrome jest zainstalowany")
        return None


if __name__ == "__main__":
    main()
