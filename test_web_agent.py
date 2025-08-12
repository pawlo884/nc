#!/usr/bin/env python
"""
Test Web Agent - prosty test połączenia ze stroną
"""
from web_agent.agent import connect_to_website
import os
import sys
import django

# Dodaj ścieżkę do projektu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ustaw zmienne środowiskowe Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')

# Inicjalizuj Django
django.setup()


def test_basic_connection():
    """Test podstawowego połączenia"""
    print("=== Test Web Agent ===")

    try:
        # Test połączenia z prostą stroną
        result = connect_to_website(
            url="https://httpbin.org/get",
            session_name="Test Session"
        )

        print("✅ Połączenie udane!")
        print(f"Status: {result['status_code']}")
        print(f"Title: {result['title']}")
        print(f"Content length: {result['content_length']}")
        print(f"Final URL: {result['final_url']}")

        return True

    except Exception as e:
        print(f"❌ Błąd połączenia: {e}")
        return False


def test_with_headers():
    """Test z custom headers"""
    print("\n=== Test z Custom Headers ===")

    try:
        result = connect_to_website(
            url="https://httpbin.org/headers",
            session_name="Headers Test",
            headers={
                'Accept': 'application/json',
                'X-Test-Header': 'test-value'
            }
        )

        print("✅ Test z headers udany!")
        print(f"Status: {result['status_code']}")

        return True

    except Exception as e:
        print(f"❌ Błąd testu z headers: {e}")
        return False


if __name__ == "__main__":
    print("Uruchamiam testy Web Agent...")

    # Test podstawowy
    basic_success = test_basic_connection()

    # Test z headers
    headers_success = test_with_headers()

    # Podsumowanie
    print(f"\n=== Podsumowanie ===")
    print(f"Test podstawowy: {'✅' if basic_success else '❌'}")
    print(f"Test z headers: {'✅' if headers_success else '❌'}")

    if basic_success and headers_success:
        print("🎉 Wszystkie testy przeszły pomyślnie!")
    else:
        print("⚠️  Niektóre testy nie przeszły.")
