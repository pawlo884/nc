#!/usr/bin/env python
"""
Test Browser Agent - test agenta działającego w przeglądarce
"""
from web_agent.browser_agent import navigate_with_browser
import os
import sys
import django

# Dodaj ścieżkę do projektu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ustaw zmienne środowiskowe Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')

# Inicjalizuj Django
django.setup()


def test_basic_browser_navigation():
    """Test podstawowej nawigacji w przeglądarce"""
    print("=== Test Browser Agent ===")

    try:
        # Test nawigacji (headless)
        result = navigate_with_browser(
            url="https://httpbin.org/get",
            session_name="Browser Test",
            headless=True
        )

        print("✅ Nawigacja w przeglądarce udana!")
        print(f"Title: {result['title']}")
        print(f"Current URL: {result['current_url']}")
        print(f"Page source length: {result['page_source_length']}")
        print(f"Screenshot taken: {result['screenshot_taken']}")

        return True

    except Exception as e:
        print(f"❌ Błąd nawigacji w przeglądarce: {e}")
        return False


def test_browser_with_form():
    """Test wypełniania formularza"""
    print("\n=== Test Formularza ===")

    try:
        from web_agent.browser_agent import create_browser_agent

        # Utwórz agenta
        agent = create_browser_agent(
            session_name="Form Test",
            url="https://httpbin.org/forms/post",
            headless=True  # Headless dla testu
        )

        # Przejdź do strony
        result = agent.navigate_to("https://httpbin.org/forms/post")
        print(f"✅ Przeszliśmy do: {result['title']}")

        # Wypełnij formularz
        success1 = agent.type_text("input[name='custname']", "Test User")
        success2 = agent.type_text("input[name='custtel']", "123456789")
        success3 = agent.type_text(
            "input[name='custemail']", "test@example.com")

        if success1 and success2 and success3:
            print("✅ Formularz wypełniony pomyślnie")
        else:
            print("⚠️  Niektóre pola nie zostały wypełnione")

        # Screenshot
        screenshot_path = agent.take_screenshot("form_test.png")
        if screenshot_path:
            print(f"✅ Screenshot: {screenshot_path}")
        else:
            print("⚠️  Błąd screenshot")

        # Zamknij
        agent.close()

        return True

    except Exception as e:
        print(f"❌ Błąd testu formularza: {e}")
        return False


if __name__ == "__main__":
    print("Uruchamiam testy Browser Agent...")

    # Test podstawowy
    basic_success = test_basic_browser_navigation()

    # Test formularza
    form_success = test_browser_with_form()

    # Podsumowanie
    print(f"\n=== Podsumowanie ===")
    print(f"Test podstawowy: {'✅' if basic_success else '❌'}")
    print(f"Test formularza: {'✅' if form_success else '❌'}")

    if basic_success and form_success:
        print("🎉 Wszystkie testy przeszły pomyślnie!")
    else:
        print("⚠️  Niektóre testy nie przeszły.")

    print("\n💡 Uwaga: Aby zobaczyć przeglądarkę na żywo, ustaw headless=False w przykładach.")
