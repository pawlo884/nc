from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DjangoAdminAgent:
    """Specjalistyczny agent do obsługi Django Admin"""

    def __init__(self, admin_url: str = "http://localhost:8000/admin/",
                 username: str = None, password: str = None, headless: bool = False):
        self.admin_url = admin_url
        self.username = username
        self.password = password
        self.driver = None
        self.headless = headless
        self._setup_driver()

    def _setup_driver(self):
        """Konfiguruje driver przeglądarki"""
        try:
            chrome_options = Options()

            # Ustawienia headless
            if self.headless:
                chrome_options.add_argument("--headless")

            # Dodatkowe opcje dla stabilności
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            # User agent
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

            # Inicjalizacja driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(
                service=service, options=chrome_options)

            # Ustaw timeout
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)

            self._log_action(
                "Przeglądarka Django Admin została uruchomiona", 'INFO')

        except Exception as e:
            error_msg = f"Błąd podczas uruchamiania przeglądarki: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            raise Exception(error_msg)

    def login_to_admin(self) -> bool:
        """
        Loguje się do Django Admin

        Returns:
            True jeśli logowanie udane
        """
        try:
            if not self.username or not self.password:
                self._log_action("Brak danych logowania", 'WARNING')
                return False

            self._log_action("Próba logowania do Django Admin", 'INFO')

            # Przejdź do strony logowania
            self.driver.get(f"{self.admin_url}login/")

            # Poczekaj na formularz logowania
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "id_username"))
            )

            # Wpisz dane logowania
            username_field = self.driver.find_element(By.ID, "id_username")
            password_field = self.driver.find_element(By.ID, "id_password")

            username_field.clear()
            username_field.send_keys(self.username)

            password_field.clear()
            password_field.send_keys(self.password)

            # Kliknij przycisk logowania
            login_button = self.driver.find_element(
                By.CSS_SELECTOR, "input[type='submit']")
            login_button.click()

            # Sprawdź czy logowanie się udało
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "user-tools"))
            )

            self._log_action("Pomyślnie zalogowano do Django Admin", 'INFO')
            return True

        except Exception as e:
            error_msg = f"Błąd podczas logowania: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return False

    def navigate_to_products_page(self, brand: str = None, category_name: str = None) -> Dict[str, Any]:
        """
        Przechodzi do strony produktów z filtrami

        Args:
            brand: Filtr marki
            category_name: Filtr kategorii

        Returns:
            Dane strony
        """
        try:
            # Buduj URL z filtrami
            url = f"{self.admin_url}matterhorn/products/"
            params = []

            if brand:
                params.append(f"brand={brand.replace(' ', '+')}")
            if category_name:
                params.append(
                    f"category_name={category_name.replace(' ', '+')}")

            if params:
                url += "?" + "&".join(params)

            self._log_action(f"Przechodzę do: {url}", 'INFO')

            # Przejdź do strony
            self.driver.get(url)

            # Czekaj na załadowanie
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Sprawdź czy jesteśmy zalogowani
            try:
                self.driver.find_element(By.ID, "user-tools")
                is_logged_in = True
            except:
                is_logged_in = False

            # Pobierz dane strony
            result_data = {
                'url': url,
                'title': self.driver.title,
                'current_url': self.driver.current_url,
                'is_logged_in': is_logged_in,
                'page_source_length': len(self.driver.page_source),
                'brand_filter': brand,
                'category_filter': category_name
            }

            # Sprawdź czy są produkty
            try:
                products_table = self.driver.find_element(
                    By.CSS_SELECTOR, "table#result_list")
                result_data['products_found'] = True
                result_data['products_count'] = len(
                    products_table.find_elements(By.CSS_SELECTOR, "tr"))
            except:
                result_data['products_found'] = False
                result_data['products_count'] = 0

            # Zrób screenshot
            try:
                screenshot_path = f"screenshots/products_page_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_path)
                result_data['screenshot_path'] = screenshot_path
            except Exception as e:
                self._log_action(f"Błąd screenshot: {str(e)}", 'WARNING')

            self._log_action(
                f"Pomyślnie przejście do strony produktów", 'INFO')
            return result_data

        except Exception as e:
            error_msg = f"Błąd podczas przechodzenia do strony produktów: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            raise Exception(error_msg)

    def get_products_data(self) -> List[Dict[str, Any]]:
        """
        Pobiera dane produktów z tabeli

        Returns:
            Lista produktów z danymi
        """
        try:
            products = []

            # Znajdź tabelę produktów
            table = self.driver.find_element(
                By.CSS_SELECTOR, "table#result_list")
            rows = table.find_elements(By.CSS_SELECTOR, "tr")[
                1:]  # Pomijamy nagłówek

            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td")
                if len(cells) >= 3:
                    product_data = {
                        'id': cells[0].text.strip() if cells[0].text else '',
                        'name': cells[1].text.strip() if cells[1].text else '',
                        'brand': cells[2].text.strip() if cells[2].text else '',
                        'category': cells[3].text.strip() if len(cells) > 3 and cells[3].text else '',
                        'stock': cells[4].text.strip() if len(cells) > 4 and cells[4].text else '',
                    }
                    products.append(product_data)

            self._log_action(f"Pobrano dane {len(products)} produktów", 'INFO')
            return products

        except Exception as e:
            error_msg = f"Błąd podczas pobierania danych produktów: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return []

    def click_product_link(self, product_id: str) -> bool:
        """
        Klika link do konkretnego produktu

        Args:
            product_id: ID produktu

        Returns:
            True jeśli kliknięcie udane
        """
        try:
            # Znajdź link do produktu
            link = self.driver.find_element(
                By.CSS_SELECTOR, f"a[href*='{product_id}/change/']")
            link.click()

            # Czekaj na załadowanie strony produktu
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "form#product_form"))
            )

            self._log_action(
                f"Przeszliśmy do produktu ID: {product_id}", 'INFO')
            return True

        except Exception as e:
            error_msg = f"Błąd podczas przechodzenia do produktu {product_id}: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return False

    def get_product_details(self) -> Dict[str, Any]:
        """
        Pobiera szczegóły produktu ze strony edycji

        Returns:
            Dane produktu
        """
        try:
            details = {}

            # Pobierz podstawowe informacje
            try:
                name_field = self.driver.find_element(By.ID, "id_name")
                details['name'] = name_field.get_attribute('value')
            except:
                details['name'] = ''

            try:
                brand_field = self.driver.find_element(By.ID, "id_brand")
                details['brand'] = brand_field.get_attribute('value')
            except:
                details['brand'] = ''

            try:
                category_field = self.driver.find_element(
                    By.ID, "id_category_name")
                details['category'] = category_field.get_attribute('value')
            except:
                details['category'] = ''

            try:
                stock_field = self.driver.find_element(By.ID, "id_stock_total")
                details['stock'] = stock_field.get_attribute('value')
            except:
                details['stock'] = ''

            try:
                price_field = self.driver.find_element(By.ID, "id_price")
                details['price'] = price_field.get_attribute('value')
            except:
                details['price'] = ''

            self._log_action("Pobrano szczegóły produktu", 'INFO')
            return details

        except Exception as e:
            error_msg = f"Błąd podczas pobierania szczegółów produktu: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return {}

    def go_back_to_list(self) -> bool:
        """
        Wraca do listy produktów

        Returns:
            True jeśli powrót udany
        """
        try:
            # Kliknij link "Produkty"
            back_link = self.driver.find_element(
                By.CSS_SELECTOR, "a[href*='matterhorn/products/']")
            back_link.click()

            # Czekaj na załadowanie listy
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "table#result_list"))
            )

            self._log_action("Powrót do listy produktów", 'INFO')
            return True

        except Exception as e:
            error_msg = f"Błąd podczas powrotu do listy: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return False

    def take_screenshot(self, filename: str = None) -> str:
        """
        Robi screenshot strony

        Args:
            filename: Nazwa pliku (opcjonalnie)

        Returns:
            Ścieżka do screenshot
        """
        try:
            if not filename:
                filename = f"django_admin_{int(time.time())}.png"

            screenshot_path = f"screenshots/{filename}"
            self.driver.save_screenshot(screenshot_path)

            self._log_action(f"Zrobiono screenshot: {screenshot_path}", 'INFO')
            return screenshot_path

        except Exception as e:
            error_msg = f"Błąd podczas robienia screenshot: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return ""

    def close(self):
        """Zamyka przeglądarkę"""
        if self.driver:
            self.driver.quit()
            self._log_action(
                "Przeglądarka Django Admin została zamknięta", 'INFO')

    def _log_action(self, message: str, level: str):
        """Zapisuje log akcji"""
        logger.info(f"DjangoAdminAgent: {message}")


def create_django_admin_agent(admin_url: str = "http://localhost:8000/admin/",
                              username: str = None, password: str = None,
                              headless: bool = False) -> DjangoAdminAgent:
    """
    Tworzy nowego Django Admin agenta

    Args:
        admin_url: URL Django Admin
        username: Nazwa użytkownika
        password: Hasło
        headless: Czy uruchomić w trybie headless

    Returns:
        DjangoAdminAgent instance
    """
    return DjangoAdminAgent(admin_url, username, password, headless)


def navigate_to_matterhorn_products(brand: str = "Lupo Line",
                                    category_name: str = "Kostiumy Dwuczęściowe",
                                    username: str = None, password: str = None,
                                    headless: bool = False) -> Dict[str, Any]:
    """
    Szybka funkcja do nawigacji do strony produktów Matterhorn

    Args:
        brand: Marka produktów
        category_name: Kategoria produktów
        username: Nazwa użytkownika Django Admin
        password: Hasło Django Admin
        headless: Czy uruchomić w trybie headless

    Returns:
        Dane strony produktów
    """
    agent = create_django_admin_agent(
        admin_url="http://localhost:8000/admin/",
        username=username,
        password=password,
        headless=headless
    )

    try:
        # Spróbuj się zalogować jeśli podano dane
        if username and password:
            if not agent.login_to_admin():
                raise Exception("Nie udało się zalogować do Django Admin")

        # Przejdź do strony produktów
        result = agent.navigate_to_products_page(brand, category_name)

        # Pobierz dane produktów
        products = agent.get_products_data()
        result['products'] = products

        return result

    finally:
        agent.close()
