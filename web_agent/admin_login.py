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


class AdminLoginAgent:
    """Klasa do automatycznego logowania do panelu admina Django"""

    def __init__(self, admin_url="http://localhost:8000/admin/",
                 username=None, password=None,
                 wait_timeout=10, auto_close_delay=10):
        """
        Inicjalizacja agenta logowania

        Args:
            admin_url (str): URL panelu admina
            username (str): Nazwa użytkownika (jeśli None, pobiera z env)
            password (str): Hasło (jeśli None, pobiera z env)
            wait_timeout (int): Timeout dla oczekiwania na elementy
            auto_close_delay (int): Opóźnienie przed zamknięciem przeglądarki
        """
        self.admin_url = admin_url
        self.username = username or os.getenv('DJANGO_ADMIN_USERNAME')
        self.password = password or os.getenv('DJANGO_ADMIN_PASSWORD')
        self.wait_timeout = wait_timeout
        self.auto_close_delay = auto_close_delay
        self.driver = None
        self.wait = None

    def _setup_chrome_driver(self):
        """Konfiguracja i inicjalizacja Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(
            "--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        print("Inicjalizacja Chrome WebDriver...")
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(
                service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, self.wait_timeout)

            # Ukryj fakt że to WebDriver
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            print("✅ Chrome WebDriver zainicjalizowany pomyślnie")
            return True
        except Exception as e:
            print(f"❌ Błąd inicjalizacji Chrome WebDriver: {str(e)}")
            print("Sprawdź czy ChromeDriver jest zainstalowany i dostępny w PATH")
            return False

    def _validate_credentials(self):
        """Sprawdza czy dane logowania są dostępne"""
        if not self.username or not self.password:
            print("❌ Błąd: Brak danych logowania")
            print(
                "Podaj username i password w konstruktorze lub ustaw zmienne środowiskowe:")
            print("- DJANGO_ADMIN_USERNAME")
            print("- DJANGO_ADMIN_PASSWORD")
            return False
        return True

    def _navigate_to_login_page(self):
        """Przechodzi do strony logowania"""
        print(f"Otwieranie strony logowania: {self.admin_url}")
        self.driver.get(self.admin_url)

    def _fill_login_form(self):
        """Wypełnia formularz logowania"""
        # Znajdź pole username
        username_field = self.wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )

        # Znajdź pole password
        password_field = self.driver.find_element(By.NAME, "password")

        # Wprowadź dane logowania
        print(f"Logowanie jako: {self.username}")
        username_field.clear()
        username_field.send_keys(self.username)
        print("Username wprowadzony")

        password_field.clear()
        password_field.send_keys(self.password)
        print("Password wprowadzony")

    def _submit_login_form(self):
        """Wysyła formularz logowania"""
        login_button = self.driver.find_element(
            By.CSS_SELECTOR, "input[type='submit']")
        login_button.click()
        print("Formularz logowania wysłany")

    def _verify_login_success(self):
        """Sprawdza czy logowanie się powiodło"""
        # Poczekaj na przekierowanie
        time.sleep(3)

        current_url = self.driver.current_url
        print(f"Aktualny URL: {current_url}")

        # Sprawdź czy jesteśmy w panelu admina (nie na stronie logowania)
        if "admin" in current_url and "login" not in current_url:
            print("✅ Logowanie zakończone sukcesem!")
            return True
        else:
            # Sprawdź czy nie ma błędu logowania
            try:
                error_element = self.driver.find_element(
                    By.CLASS_NAME, "errornote")
                if error_element:
                    print(f"❌ Błąd logowania: {error_element.text}")
            except Exception:
                pass
            print("❌ Logowanie nie powiodło się")
            return False

    def login(self, keep_browser_open=False):
        """
        Główna metoda logowania

        Args:
            keep_browser_open (bool): Czy pozostawić przeglądarkę otwartą

        Returns:
            bool: True jeśli logowanie się powiodło, False w przeciwnym razie
        """
        try:
            # Sprawdź dane logowania
            if not self._validate_credentials():
                return False

            # Skonfiguruj WebDriver
            if not self._setup_chrome_driver():
                return False

            # Przejdź do strony logowania
            self._navigate_to_login_page()

            # Wypełnij formularz logowania
            self._fill_login_form()

            # Wyślij formularz
            self._submit_login_form()

            # Sprawdź czy logowanie się powiodło
            login_success = self._verify_login_success()

            if not keep_browser_open:
                self.close_browser()

            return login_success

        except Exception as e:
            print(f"❌ Błąd podczas logowania: {str(e)}")
            if not keep_browser_open:
                self.close_browser()
            return False

    def close_browser(self):
        """Zamyka przeglądarkę z opóźnieniem"""
        if self.driver:
            if self.auto_close_delay > 0:
                print(
                    f"Przeglądarka zostanie zamknięta za {self.auto_close_delay} sekund...")
                time.sleep(self.auto_close_delay)
            self.driver.quit()
            self.driver = None

    def get_driver(self):
        """Zwraca instancję WebDriver (dla dalszego użycia)"""
        return self.driver

    def __enter__(self):
        """Context manager - rozpoczęcie"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - zakończenie"""
        self.close_browser()


def login_to_admin():
    """Funkcja kompatybilna wstecz - używa nowej klasy"""
    agent = AdminLoginAgent()
    return agent.login()


if __name__ == "__main__":
    # Przykład użycia klasy
    agent = AdminLoginAgent()
    success = agent.login()

    if success:
        print("Logowanie zakończone sukcesem!")
    else:
        print("Logowanie nie powiodło się!")

    # Przykład użycia z context managerem
    # with AdminLoginAgent() as agent:
    #     success = agent.login(keep_browser_open=True)
    #     if success:
    #         driver = agent.get_driver()
    #         # Wykonaj dodatkowe operacje z driver
    #         pass
