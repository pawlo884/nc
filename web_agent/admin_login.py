import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe z .env.dev
# Sprawdź czy jesteśmy w katalogu web_agent czy w głównym katalogu projektu
if os.path.exists('.env.dev'):
    load_dotenv('.env.dev')
else:
    # Jeśli jesteśmy w katalogu web_agent, przejdź do katalogu nadrzędnego
    load_dotenv('../.env.dev')


def login_to_admin():
    """Automatyczne logowanie do panelu admina Django"""

    # Konfiguracja Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument(
        "--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option(
        "excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Inicjalizacja WebDriver z automatycznym zarządzaniem ChromeDriver
    print("Inicjalizacja Chrome WebDriver...")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Chrome WebDriver zainicjalizowany pomyślnie")
    except Exception as e:
        print(f"❌ Błąd inicjalizacji Chrome WebDriver: {str(e)}")
        print("Sprawdź czy ChromeDriver jest zainstalowany i dostępny w PATH")
        return False

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        # Przejdź do strony logowania
        print("Otwieranie strony logowania...")
        driver.get("http://localhost:8000/admin/")

        # Poczekaj na załadowanie strony
        wait = WebDriverWait(driver, 10)

        # Znajdź pole username
        username_field = wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )

        # Znajdź pole password
        password_field = driver.find_element(By.NAME, "password")

        # Pobierz dane logowania z zmiennych środowiskowych
        username = os.getenv('DJANGO_ADMIN_USERNAME')
        password = os.getenv('DJANGO_ADMIN_PASSWORD')

        print(f"DEBUG: Username z env: {username}")
        print(
            f"DEBUG: Password z env: {'*' * len(password) if password else 'None'}")

        if not username or not password:
            print("Błąd: Brak danych logowania w zmiennych środowiskowych")
            return False

        # Wprowadź dane logowania
        print(f"Logowanie jako: {username}")
        print("Wprowadzam username...")
        username_field.clear()
        username_field.send_keys(username)
        print("Username wprowadzony")

        print("Wprowadzam password...")
        password_field.clear()
        password_field.send_keys(password)
        print("Password wprowadzony")

        # Kliknij przycisk logowania
        print("Szukam przycisku logowania...")
        login_button = driver.find_element(
            By.CSS_SELECTOR, "input[type='submit']")
        print("Przycisk logowania znaleziony, klikam...")
        login_button.click()
        print("Przycisk logowania kliknięty")

        # Poczekaj na przekierowanie
        print("Czekam na przekierowanie po logowaniu...")
        time.sleep(3)

        # Sprawdź czy logowanie się powiodło
        current_url = driver.current_url
        print(f"Aktualny URL: {current_url}")

        # Sprawdź czy jesteśmy w panelu admina (nie na stronie logowania)
        if "admin" in current_url and "login" not in current_url:
            print("✅ Logowanie zakończone sukcesem!")
            return True
        else:
            # Sprawdź czy nie ma błędu logowania
            try:
                error_element = driver.find_element(By.CLASS_NAME, "errornote")
                if error_element:
                    print(f"❌ Błąd logowania: {error_element.text}")
            except Exception:
                pass
            print("❌ Logowanie nie powiodło się")
            return False

    except Exception as e:
        print(f"❌ Błąd podczas logowania: {str(e)}")
        return False

    finally:
        # Poczekaj 10 sekund i zamknij przeglądarkę
        print("Przeglądarka zostanie zamknięta za 10 sekund...")
        time.sleep(10)
        driver.quit()


if __name__ == "__main__":
    login_to_admin()
