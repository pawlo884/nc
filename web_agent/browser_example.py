"""
Przykład użycia Browser Agent - agent działający w przeglądarce na żywo
"""
from .browser_agent import navigate_with_browser, create_browser_agent


def example_basic_browser_navigation():
    """Przykład podstawowej nawigacji w przeglądarce"""
    try:
        # Szybka nawigacja (headless)
        result = navigate_with_browser(
            url="https://httpbin.org/get",
            session_name="Browser Test",
            headless=True
        )
        print(f"Status: {result['title']}")
        print(f"URL: {result['current_url']}")
        print(f"Content length: {result['page_source_length']}")
        return result
    except Exception as e:
        print(f"Błąd: {e}")
        return None


def example_interactive_browser():
    """Przykład interaktywnej pracy z przeglądarką"""
    try:
        # Utwórz agenta (widoczna przeglądarka)
        agent = create_browser_agent(
            session_name="Interactive Session",
            url="https://httpbin.org/forms/post",
            headless=False  # Widoczna przeglądarka
        )

        # Przejdź do strony
        result = agent.navigate_to("https://httpbin.org/forms/post")
        print(f"Przeszliśmy do: {result['title']}")

        # Poczekaj chwilę żeby zobaczyć
        import time
        time.sleep(3)

        # Wypełnij formularz
        agent.type_text("input[name='custname']", "Jan Kowalski")
        agent.type_text("input[name='custtel']", "123456789")
        agent.type_text("input[name='custemail']", "jan@example.com")

        # Zrób screenshot
        screenshot_path = agent.take_screenshot("form_filled.png")
        print(f"Screenshot: {screenshot_path}")

        # Poczekaj chwilę
        time.sleep(2)

        # Zamknij przeglądarkę
        agent.close()

        return result

    except Exception as e:
        print(f"Błąd: {e}")
        return None


def example_google_search():
    """Przykład wyszukiwania w Google"""
    try:
        agent = create_browser_agent(
            session_name="Google Search",
            url="https://www.google.com",
            headless=False
        )

        # Przejdź do Google
        agent.navigate_to("https://www.google.com")

        # Wpisz wyszukiwanie
        agent.type_text("input[name='q']", "Python Django")

        # Kliknij przycisk wyszukiwania
        agent.click_element("input[name='btnK']")

        # Poczekaj na wyniki
        agent.wait_for_element("#search", timeout=10)

        # Pobierz pierwszy wynik
        first_result = agent.get_element_text("h3", selector_type="css")
        print(f"Pierwszy wynik: {first_result}")

        # Screenshot wyników
        screenshot_path = agent.take_screenshot("google_results.png")
        print(f"Screenshot wyników: {screenshot_path}")

        # Zamknij
        agent.close()

        return first_result

    except Exception as e:
        print(f"Błąd: {e}")
        return None


if __name__ == "__main__":
    print("=== Przykład podstawowej nawigacji ===")
    example_basic_browser_navigation()

    print("\n=== Przykład interaktywnej przeglądarki ===")
    example_interactive_browser()

    print("\n=== Przykład wyszukiwania Google ===")
    example_google_search()
