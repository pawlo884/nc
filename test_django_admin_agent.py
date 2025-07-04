#!/usr/bin/env python
"""
Test Django Admin Agent - test agenta do Django Admin
"""
from web_agent.django_admin_agent import navigate_to_matterhorn_products
import os
import sys
import django

# Dodaj ścieżkę do projektu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ustaw zmienne środowiskowe Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')

# Inicjalizuj Django
django.setup()


def test_matterhorn_products_navigation():
    """Test nawigacji do strony produktów Matterhorn"""
    print("=== Test Django Admin Agent ===")

    try:
        # Test nawigacji do konkretnej strony
        result = navigate_to_matterhorn_products(
            brand="Lupo Line",
            category_name="Kostiumy Dwuczęściowe",
            headless=True  # Headless dla testu
        )

        print("✅ Nawigacja do Django Admin udana!")
        print(f"URL: {result['url']}")
        print(f"Title: {result['title']}")
        print(f"Zalogowany: {result['is_logged_in']}")
        print(f"Znaleziono produkty: {result['products_found']}")
        print(f"Liczba produktów: {result['products_count']}")
        print(f"Screenshot: {result.get('screenshot_path', 'Brak')}")

        if result['products']:
            print(f"Pierwszy produkt: {result['products'][0]}")

        return True

    except Exception as e:
        print(f"❌ Błąd nawigacji: {e}")
        return False


def test_django_admin_with_login():
    """Test z logowaniem (wymaga danych logowania)"""
    print("\n=== Test z Logowaniem ===")

    # Tutaj możesz dodać dane logowania
    username = os.getenv('DJANGO_ADMIN_USERNAME')
    password = os.getenv('DJANGO_ADMIN_PASSWORD')

    if not username or not password:
        print("⚠️  Brak danych logowania w zmiennych środowiskowych")
        print("   Ustaw DJANGO_ADMIN_USERNAME i DJANGO_ADMIN_PASSWORD")
        return False

    try:
        result = navigate_to_matterhorn_products(
            brand="Lupo Line",
            category_name="Kostiumy Dwuczęściowe",
            username=username,
            password=password,
            headless=True
        )

        print("✅ Test z logowaniem udany!")
        print(f"Zalogowany: {result['is_logged_in']}")
        print(f"Liczba produktów: {result['products_count']}")

        return True

    except Exception as e:
        print(f"❌ Błąd testu z logowaniem: {e}")
        return False


def test_interactive_admin_agent():
    """Test interaktywnego agenta (widoczna przeglądarka)"""
    print("\n=== Test Interaktywny ===")

    try:
        from web_agent.django_admin_agent import create_django_admin_agent

        # Utwórz agenta (widoczna przeglądarka)
        agent = create_django_admin_agent(
            admin_url="http://localhost:8000/admin/",
            headless=False  # Widoczna przeglądarka
        )

        # Przejdź do strony produktów
        result = agent.navigate_to_products_page(
            brand="Lupo Line",
            category_name="Kostiumy Dwuczęściowe"
        )

        print(f"✅ Przeszliśmy do: {result['title']}")
        print(f"URL: {result['current_url']}")

        # Pobierz dane produktów
        products = agent.get_products_data()
        print(f"Pobrano {len(products)} produktów")

        if products:
            print(f"Pierwszy produkt: {products[0]['name']}")

        # Screenshot
        screenshot_path = agent.take_screenshot("matterhorn_products.png")
        if screenshot_path:
            print(f"✅ Screenshot: {screenshot_path}")

        # Poczekaj chwilę żeby zobaczyć
        import time
        time.sleep(3)

        # Zamknij
        agent.close()

        return True

    except Exception as e:
        print(f"❌ Błąd testu interaktywnego: {e}")
        return False


if __name__ == "__main__":
    print("Uruchamiam testy Django Admin Agent...")
    print("💡 Upewnij się, że serwer Django działa na localhost:8000")

    # Test podstawowy
    basic_success = test_matterhorn_products_navigation()

    # Test z logowaniem
    login_success = test_django_admin_with_login()

    # Test interaktywny (opcjonalny)
    interactive_success = test_interactive_admin_agent()

    # Podsumowanie
    print(f"\n=== Podsumowanie ===")
    print(f"Test podstawowy: {'✅' if basic_success else '❌'}")
    print(f"Test z logowaniem: {'✅' if login_success else '❌'}")
    print(f"Test interaktywny: {'✅' if interactive_success else '❌'}")

    if basic_success:
        print("🎉 Agent Django Admin działa poprawnie!")
    else:
        print("⚠️  Sprawdź czy serwer Django działa na localhost:8000")

    print("\n💡 Aby zobaczyć przeglądarkę na żywo, ustaw headless=False w testach.")
