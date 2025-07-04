"""
Przykład użycia Web Agent
"""
from .agent import connect_to_website


def example_basic_connection():
    """Przykład podstawowego połączenia ze stroną"""
    try:
        # Szybkie połączenie
        result = connect_to_website(
            url="https://httpbin.org/get",
            session_name="Test Session"
        )
        print(f"Status: {result['status_code']}")
        print(f"Title: {result['title']}")
        print(f"Content length: {result['content_length']}")
        return result
    except Exception as e:
        print(f"Błąd: {e}")
        return None


def example_with_custom_headers():
    """Przykład z custom headers"""
    try:
        result = connect_to_website(
            url="https://httpbin.org/headers",
            session_name="Custom Headers Session",
            headers={
                'Accept': 'application/json',
                'X-Custom-Header': 'test-value'
            }
        )
        print(f"Status: {result['status_code']}")
        return result
    except Exception as e:
        print(f"Błąd: {e}")
        return None


def example_with_proxy():
    """Przykład z proxy (wymaga działającego proxy)"""
    try:
        result = connect_to_website(
            url="https://httpbin.org/ip",
            session_name="Proxy Session",
            proxy="http://proxy.example.com:8080"  # Przykład
        )
        print(f"Status: {result['status_code']}")
        return result
    except Exception as e:
        print(f"Błąd: {e}")
        return None


if __name__ == "__main__":
    print("=== Przykład podstawowego połączenia ===")
    example_basic_connection()

    print("\n=== Przykład z custom headers ===")
    example_with_custom_headers()
