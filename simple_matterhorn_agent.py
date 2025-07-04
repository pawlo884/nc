#!/usr/bin/env python
"""
Uproszczony agent do strony produktów Matterhorn - bez importu modeli Django
"""
import logging
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import django
import os
import sys
from django.conf import settings

# Dodaj ścieżkę do projektu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ustaw zmienne środowiskowe Django PRZED importem django!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.base')

# Tymczasowo ustaw bazę danych na SQLite
os.environ.setdefault('DJANGO_DB_ENGINE', 'django.db.backends.sqlite3')
os.environ.setdefault('DJANGO_DB_NAME', 'db.sqlite3')

# Tymczasowo skonfiguruj bazę danych
if not settings.configured:
    from django.conf import settings
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'db.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'web_agent',
        ],
        SECRET_KEY='django-insecure-temp-key-for-agent',
        DEBUG=True,
    )

django.setup()

logger = logging.getLogger(__name__)


class SimpleMatterhornAgent:
    """Uproszczony agent do strony produktów Matterhorn"""

    def __init__(self, headless: bool = False):
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

            print("✅ Przeglądarka została uruchomiona")

        except Exception as e:
            print(f"❌ Błąd podczas uruchamiania przeglądarki: {str(e)}")
            raise Exception(
                f"Błąd podczas uruchamiania przeglądarki: {str(e)}")

    def navigate_to_matterhorn_products(self, brand: str = "Lupo Line",
                                        category_name: str = "Kostiumy Dwuczęściowe") -> dict:
        """
        Przechodzi do strony produktów Matterhorn

        Args:
            brand: Marka produktów
            category_name: Kategoria produktów

        Returns:
            Dane strony
        """
        try:
            # Buduj URL z filtrami
            url = f"http://localhost:8000/admin/matterhorn/products/"
            params = []

            if brand:
                params.append(f"brand={brand.replace(' ', '+')}")
            if category_name:
                params.append(
                    f"category_name={category_name.replace(' ', '+')}")

            if params:
                url += "?" + "&".join(params)

            print(f"🌐 Przechodzę do: {url}")

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
                screenshot_path = f"screenshots/matterhorn_products_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_path)
                result_data['screenshot_path'] = screenshot_path
                print(f"📸 Screenshot: {screenshot_path}")
            except Exception as e:
                print(f"⚠️  Błąd screenshot: {str(e)}")

            print("✅ Pomyślnie przejście do strony produktów")
            return result_data

        except Exception as e:
            error_msg = f"Błąd podczas przechodzenia do strony produktów: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)

    def get_products_data(self) -> list:
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

            print(f"📊 Pobrano dane {len(products)} produktów")
            return products

        except Exception as e:
            print(f"❌ Błąd podczas pobierania danych produktów: {str(e)}")
            return []

    def close(self):
        """Zamyka przeglądarkę"""
        if self.driver:
            self.driver.quit()
            print("🔒 Przeglądarka została zamknięta")


def main():
    """Główna funkcja"""
    print("🚀 Uruchamiam uproszczonego agenta dla strony produktów Matterhorn...")
    print("📍 URL: http://localhost:8000/admin/matterhorn/products/?brand=Lupo+Line&category_name=Kostiumy+Dwuczęściowe")

    try:
        # Utwórz agenta
        agent = SimpleMatterhornAgent(headless=False)  # Widoczna przeglądarka

        # Przejdź do strony produktów
        result = agent.navigate_to_matterhorn_products(
            brand="Lupo Line",
            category_name="Kostiumy Dwuczęściowe"
        )

        # Pobierz dane produktów
        products = agent.get_products_data()
        result['products'] = products

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
        if products:
            print(f"\n📋 Lista produktów ({len(products)}):")
            for i, product in enumerate(products[:5], 1):  # Pierwsze 5
                print(
                    f"  {i}. ID: {product['id']} | {product['name']} | {product['brand']}")

            if len(products) > 5:
                print(f"  ... i {len(products) - 5} więcej")

        # Poczekaj chwilę żeby zobaczyć
        print("\n⏳ Czekam 5 sekund przed zamknięciem...")
        time.sleep(5)

        # Zamknij przeglądarkę
        agent.close()

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
