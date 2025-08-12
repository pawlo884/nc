#!/usr/bin/env python
"""
Ultra prosty agent - tylko Selenium, bez Django
"""
import time
import os
from dotenv import load_dotenv
import asyncio
from urllib.parse import quote
from agents import Agent, Runner
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# Załaduj zmienne środowiskowe z .env.dev
load_dotenv('.env.dev')

agent_mpd_name = Agent(
    name="Modyfikujesz nazwę produktu",
    instructions="""
    Jesteś ekspertem we wprowadzaniu danych. Zmieniasz opis produktu według schematu w zależności od tego co jest w opisie.
    Przykłady:
    - Kostium dwuczęściowy Figi 1 Kąpielowe Model Amelia Big Multicolor - Lupo Line ---> Figi kąpielowe Amelia Big

    """,
    model="gpt-4o-mini",
    tools=[]
)

agent_mpd_description = Agent(
    name="Modyfikujesz opis produktu",
    instructions="""
    Jesteś ekspertem we wprowadzaniu danych. Zmieniasz nieznacznie opis produktu.

    """,
    model="gpt-4o-mini",
    tools=[]
)

agent_mpd_attributes = Agent(
    name="Dodajesz atrybuty produktu",
    instructions="""
    Jesteś ekspertem we wprowadzaniu danych. Dodajesz atrybuty produktu.
    """,
    model="gpt-4o-mini",
    tools=[]
)


class UltraSimpleAgent:
    """Ultra prosty agent - tylko przeglądarka"""

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

    def login_to_admin(self, username: str, password: str) -> bool:
        """
        Loguje się do Django Admin

        Args:
            username: Nazwa użytkownika
            password: Hasło

        Returns:
            True jeśli logowanie udane
        """
        try:
            print(f"🔐 Próba logowania jako: {username}")

            # Przejdź do strony logowania
            login_url = "http://localhost:8000/admin/login/"
            self.driver.get(login_url)

            # Poczekaj na formularz logowania
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "id_username"))
            )

            # Wpisz dane logowania
            username_field = self.driver.find_element(By.ID, "id_username")
            password_field = self.driver.find_element(By.ID, "id_password")

            username_field.clear()
            username_field.send_keys(username)

            password_field.clear()
            password_field.send_keys(password)

            # Kliknij przycisk logowania
            login_button = self.driver.find_element(
                By.CSS_SELECTOR, "input[type='submit']")
            login_button.click()

            # Sprawdź czy logowanie się udało
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "user-tools"))
                )
                print("✅ Pomyślnie zalogowano do Django Admin")
                return True
            except:
                print("❌ Logowanie nie powiodło się - sprawdź dane logowania")
                return False

        except Exception as e:
            print(f"❌ Błąd podczas logowania: {str(e)}")
            return False

    def go_to_matterhorn_products_with_login(self, username: str, password: str,
                                             brand: str = "Lupo Line",
                                             category_name: str = "Kostiumy Dwuczęściowe"):
        """
        Loguje się i przechodzi do strony produktów Matterhorn

        Args:
            username: Nazwa użytkownika Django Admin
            password: Hasło Django Admin
            brand: Marka produktów
            category_name: Kategoria produktów
        """
        try:
            # Najpierw się zaloguj
            if not self.login_to_admin(username, password):
                raise Exception("Nie udało się zalogować do Django Admin")

            # Teraz przejdź do strony produktów
            return self.go_to_matterhorn_products(brand, category_name)

        except Exception as e:
            error_msg = f"Błąd podczas logowania i przechodzenia do strony: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)

    def go_to_matterhorn_products(self, brand: str = "Lupo Line",
                                  category_name: str = "Kostiumy Dwuczęściowe"):
        """
        Przechodzi do strony produktów Matterhorn

        Args:
            brand: Marka produktów
            category_name: Kategoria produktów
        """
        try:
            # Buduj URL z filtrami
            url = "http://localhost:8000/admin/matterhorn/products/"
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

            print("✅ Pomyślnie przejście do strony produktów")

            # Pobierz podstawowe informacje
            title = self.driver.title
            current_url = self.driver.current_url

            print(f"📄 Tytuł strony: {title}")
            print(f"🔗 Aktualny URL: {current_url}")

            # Sprawdź czy jesteśmy zalogowani
            try:
                self.driver.find_element(By.ID, "user-tools")
                print("🔐 Status: Zalogowany do Django Admin")
                is_logged_in = True
            except:
                print("⚠️  Status: Nie zalogowany (może wymagać logowania)")
                is_logged_in = False

            # Sprawdź czy są produkty
            try:
                products_table = self.driver.find_element(
                    By.CSS_SELECTOR, "table#result_list")
                rows = products_table.find_elements(By.CSS_SELECTOR, "tr")
                products_count = len(rows) - 1  # Pomijamy nagłówek
                print(f"📦 Znaleziono {products_count} produktów")

                # Pokaż pierwsze produkty
                if products_count > 0:
                    print("\n📋 Pierwsze produkty:")
                    # Pierwsze 5 produktów
                    for i, row in enumerate(rows[1:6], 1):
                        cells = row.find_elements(By.CSS_SELECTOR, "td")
                        if len(cells) >= 3:
                            product_id = cells[0].text.strip()
                            product_name = cells[1].text.strip()
                            product_brand = cells[2].text.strip()
                            print(
                                f"  {i}. ID: {product_id} | {product_name} | {product_brand}")

                    if products_count > 5:
                        print(f"  ... i {products_count - 5} więcej")

            except Exception as e:
                print(f"⚠️  Nie znaleziono tabeli produktów: {str(e)}")

            # Zrób screenshot
            try:
                screenshot_path = f"screenshots/matterhorn_products_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_path)
                print(f"📸 Screenshot: {screenshot_path}")
            except Exception as e:
                print(f"⚠️  Błąd screenshot: {str(e)}")

            return {
                'title': title,
                'current_url': current_url,
                'is_logged_in': is_logged_in,
                'products_count': products_count if 'products_count' in locals() else 0,
                'screenshot_path': screenshot_path if 'screenshot_path' in locals() else None
            }

        except Exception as e:
            error_msg = f"Błąd podczas przechodzenia do strony: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)

    def wait_and_close(self, seconds: int = 10):
        """
        Czeka określoną liczbę sekund i zamyka przeglądarkę

        Args:
            seconds: Liczba sekund do oczekiwania
        """
        print(f"\n⏳ Czekam {seconds} sekund przed zamknięciem...")
        time.sleep(seconds)
        self.close()

    def close(self):
        """Zamyka przeglądarkę"""
        if self.driver:
            self.driver.quit()
            print("🔒 Przeglądarka została zamknięta")

    def get_first_unmapped_product_id(self) -> str:
        """
        Pobiera ID pierwszego produktu z mapped_product_id='-' (niezamapowany) i active='true'.
        ID pobierane jest z linka w pierwszej komórce <th> w wierszu.

        Returns:
            ID produktu lub pusty string jeśli nie znaleziono
        """
        try:
            print(
                "🔍 Szukam pierwszego aktywnego produktu z mapped_product_id='-' (niezamapowany)...")

            # Znajdź tabelę produktów
            products_table = self.driver.find_element(
                By.CSS_SELECTOR, "table#result_list")
            rows = products_table.find_elements(By.CSS_SELECTOR, "tr")[
                1:]  # Pomijamy nagłówek

            for row in rows:
                th_cells = row.find_elements(By.CSS_SELECTOR, "th")
                td_cells = row.find_elements(By.CSS_SELECTOR, "td")
                print('DEBUG row:', [
                      cell.text for cell in th_cells + td_cells])
                if not th_cells or len(td_cells) < 12:
                    continue
                # ID i link
                id_cell = th_cells[0]
                try:
                    link = id_cell.find_element(By.TAG_NAME, "a")
                    href = link.get_attribute("href")
                    product_id = link.text.strip()
                except Exception as e:
                    print(f"❌ Nie udało się pobrać ID z linka: {e}")
                    continue
                active = td_cells[1].text.strip().lower()
                product_name = td_cells[2].text.strip()
                mapped_product_id = td_cells[11].text.strip()

                # Sprawdź czy produkt jest aktywny
                if active != 'true':
                    continue

                # Sprawdź czy mapped_product_id jest '-' (niezamapowany)
                if mapped_product_id == '-':
                    print(
                        f"✅ Znaleziono niezamapowany, aktywny produkt: ID={product_id}, Nazwa={product_name}, mapped_product_id='{mapped_product_id}'")
                    return product_id

            print("⚠️  Nie znaleziono aktywnego produktu z mapped_product_id='-'")
            return ""

        except Exception as e:
            print(f"❌ Błąd podczas szukania produktu: {str(e)}")
            return ""

    def get_product_details_by_id(self, product_id: str) -> dict:
        """
        Pobiera szczegóły produktu po ID

        Args:
            product_id: ID produktu

        Returns:
            Słownik z danymi produktu
        """
        try:
            print(f"📋 Pobieram szczegóły produktu ID: {product_id}")

            # Znajdź link do produktu w tabeli
            link_selector = f"a[href*='{product_id}/change/']"
            product_link = self.driver.find_element(
                By.CSS_SELECTOR, link_selector)

            # Kliknij link do produktu
            product_link.click()

            # Czekaj na załadowanie strony produktu
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "form#product_form"))
            )

            # Pobierz dane z formularza
            details = {}

            # Podstawowe pola
            fields_to_get = [
                ('name', 'id_name'),
                ('brand', 'id_brand'),
                ('category_name', 'id_category_name'),
                ('stock_total', 'id_stock_total'),
                ('price', 'id_price'),
                ('is_mapped', 'id_is_mapped'),
                ('mapped_product_id', 'id_mapped_product_id')
            ]

            for field_name, field_id in fields_to_get:
                try:
                    field = self.driver.find_element(By.ID, field_id)
                    if field.tag_name == 'input':
                        if field.get_attribute('type') == 'checkbox':
                            details[field_name] = field.is_selected()
                        else:
                            details[field_name] = field.get_attribute('value')
                    elif field.tag_name == 'select':
                        selected_option = field.find_element(
                            By.CSS_SELECTOR, "option[selected]")
                        details[field_name] = selected_option.text
                    else:
                        details[field_name] = field.text
                except:
                    details[field_name] = None

            print(f"✅ Pobrano szczegóły produktu ID: {product_id}")
            return details

        except Exception as e:
            print(
                f"❌ Błąd podczas pobierania szczegółów produktu {product_id}: {str(e)}")
            return {}

    def go_back_to_products_list(self, brand: str, category_name: str):
        """
        Wraca do listy produktów z tymi samymi filtrami.
        """
        from urllib.parse import quote
        base_url = "http://localhost:8000/admin/matterhorn/products/"
        filters = f"?brand={quote(brand)}&category_name={quote(category_name)}"
        url = f"{base_url}{filters}"
        print(f"⬅️ Powrót do listy produktów: {url}")
        self.driver.get(url)

    def go_to_product_change_page(self, product_id: str, brand: str, category_name: str):
        """
        Przechodzi do strony edycji produktu z zachowaniem filtrów.
        """
        base_url = "http://localhost:8000/admin/matterhorn/products/"
        filters = f"?_changelist_filters=brand={quote(brand)}&category_name={quote(category_name)}"
        url = f"{base_url}{product_id}/change/{filters}"
        print(f"➡️ Przechodzę do strony edycji produktu: {url}")
        self.driver.get(url)

    def expand_sidebar_panel(self):
        """
        Rozwija panel boczny na stronie produktu klikając przycisk toggle-button,
        tylko jeśli panel jest zamknięty (div.column.right-column ma klasę 'collapsed').
        Po kliknięciu czeka aż klasa 'collapsed' zniknie.
        """
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            # Czekaj na obecność panelu bocznego
            right_column = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.column.right-column"))
            )
            class_attr = right_column.get_attribute("class")
            print(f"DEBUG: class right-column przed kliknięciem: {class_attr}")
            if "collapsed" in class_attr:
                # Czekaj na widoczność przycisku
                button = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, "button.toggle-button"))
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView(true);", button)
                button.click()
                print("➡️ Kliknięto toggle-button, czekam na rozwinięcie panelu...")
                # Poczekaj aż klasa 'collapsed' zniknie
                WebDriverWait(self.driver, 10).until(
                    lambda d: "collapsed" not in d.find_element(
                        By.CSS_SELECTOR, "div.column.right-column").get_attribute("class")
                )
                print("✅ Panel boczny rozwinięty!")
            else:
                print("ℹ️ Panel boczny już był rozwinięty.")
        except Exception as e:
            print(f"⚠️  Nie udało się rozwinąć panelu bocznego: {e}")

    def get_mpd_name_field(self):
        """
        Wyszukuje element o id="mpd_name" na stronie produktu i wypisuje jego wartość.
        """
        try:
            field = self.driver.find_element(By.ID, "mpd_name")
            value = field.get_attribute("value")
            print(f"🔎 Pole mpd_name: {value}")
            return value
        except Exception as e:
            print(f"⚠️  Nie znaleziono pola mpd_name: {e}")
            return None

    def set_mpd_name_field(self, new_value):
        """
        Ustawia nową wartość w polu mpd_name na stronie produktu.
        """
        try:
            field = self.driver.find_element(By.ID, "mpd_name")
            field.clear()
            field.send_keys(new_value)
            print(f"✍️ Nowa wartość mpd_name: {new_value}")
        except Exception as e:
            print(f"⚠️  Nie udało się ustawić nowej wartości mpd_name: {e}")

    def get_mpd_description_field(self):
        try:
            field = self.driver.find_element(By.ID, "mpd_description")
            value = field.get_attribute("value")
            print(f"🔎 Pole mpd_description: {value}")
            return value
        except Exception as e:
            print(f"⚠️  Nie znaleziono pola mpd_description: {e}")
            return None

    def set_mpd_description_field(self, new_value):
        try:
            field = self.driver.find_element(By.ID, "mpd_description")
            field.clear()
            field.send_keys(new_value)
            print(f"✍️ Nowa wartość mpd_description: {new_value}")
        except Exception as e:
            print(
                f"⚠️  Nie udało się ustawić nowej wartości mpd_description: {e}")

    def set_mpd_attributes_field(self, attributes):
        """
        Zaznacza opcje w polu mpd_attributes na podstawie listy atrybutów (wartości lub tekstów).
        """
        try:
            select = self.driver.find_element(By.ID, "mpd_attributes")
            options = select.find_elements(By.TAG_NAME, "option")
            # Odznacz wszystko
            self.driver.execute_script(
                "arguments[0].selectedIndex = -1;", select)
            # Zaznacz tylko te, które są na liście
            for option in options:
                if option.text.strip() in attributes or option.get_attribute("value") in attributes:
                    self.driver.execute_script(
                        "arguments[0].selected = true;", option)
            print(f"✅ Zaznaczono atrybuty: {attributes}")
        except Exception as e:
            print(f"⚠️  Nie udało się ustawić atrybutów: {e}")

    def get_all_mpd_attributes(self):
        select = self.driver.find_element(By.ID, "mpd_attributes")
        options = select.find_elements(By.TAG_NAME, "option")
        return [option.text.strip() for option in options]


async def main():
    """Główna funkcja"""
    print("🚀 Uruchamiam ultra prostego agenta z logowaniem...")
    print("📍 URL: http://localhost:8000/admin/matterhorn/products/?brand=Lupo+Line&category_name=Kostiumy+Dwuczęściowe")

    # Pobierz dane logowania z .env.dev
    username = os.getenv('DJANGO_ADMIN_USERNAME')
    password = os.getenv('DJANGO_ADMIN_PASSWORD')

    if not username or not password:
        print("❌ Brak danych logowania w .env.dev")
        print("   Upewnij się, że masz ustawione DJANGO_ADMIN_USERNAME i DJANGO_ADMIN_PASSWORD")
        return None

    print(f"👤 Logowanie jako: {username}")

    try:
        # Utwórz agenta (widoczna przeglądarka)
        selenium_agent = UltraSimpleAgent(headless=False)

        # Zaloguj się i przejdź do strony produktów
        result = selenium_agent.go_to_matterhorn_products_with_login(
            username=username,
            password=password,
            brand="Lupo Line",
            category_name="Kostiumy Dwuczęściowe"
        )

        print("\n✅ Agent zakończył pracę!")
        print(f"📄 Tytuł: {result['title']}")
        print(f"🔗 URL: {result['current_url']}")
        print(f"🔐 Zalogowany: {result['is_logged_in']}")
        print(f"📦 Produkty: {result['products_count']}")

        if result.get('screenshot_path'):
            print(f"📸 Screenshot: {result['screenshot_path']}")

        # Szukaj pierwszego produktu z is_mapped=False
        print("\n🔍 Szukam pierwszego produktu do mapowania...")
        unmapped_product_id = selenium_agent.get_first_unmapped_product_id()

        if unmapped_product_id:
            print(
                f"🎯 Znaleziono produkt do mapowania: ID={unmapped_product_id}")

            # Przejdź do strony edycji produktu z filtrami
            selenium_agent.go_to_product_change_page(
                product_id=unmapped_product_id,
                brand="Lupo Line",
                category_name="Kostiumy Dwuczęściowe"
            )

            # Rozwiń panel boczny
            selenium_agent.expand_sidebar_panel()

            # Pobierz pole mpd_name
            mpd_name = selenium_agent.get_mpd_name_field()

            if mpd_name:
                # Przetwarzaj przez AI (Agent z frameworku)
                run_result = await Runner.run(agent_mpd_name, mpd_name)
                if hasattr(run_result, "output"):
                    new_value = run_result.output
                elif hasattr(run_result, "result"):
                    new_value = run_result.result
                else:
                    new_value = str(run_result)

                if isinstance(new_value, str):
                    lines = [line.strip()
                             for line in new_value.splitlines() if line.strip()]
                    # Szukaj linii, które zawierają 'Figi' lub 'Biustonosz'
                    content_lines = [
                        line for line in lines
                        if ("Figi" in line or "Biustonosz" in line)
                    ]
                    if content_lines:
                        new_value = content_lines[0]
                selenium_agent.set_mpd_name_field(new_value)

            # Pobierz pole mpd_description
            mpd_description = selenium_agent.get_mpd_description_field()
            if mpd_description:
                run_result = await Runner.run(agent_mpd_description, mpd_description)
                print("DEBUG run_result:", run_result)
                if hasattr(run_result, "output"):
                    new_value = run_result.output
                elif hasattr(run_result, "result"):
                    new_value = run_result.result
                else:
                    new_value = str(run_result)

                if isinstance(new_value, str):
                    lines = [line.rstrip() for line in new_value.splitlines()]
                    # Szukaj linii po '- Final output (str):'
                    final_output_idx = None
                    for idx, line in enumerate(lines):
                        if line.strip().startswith("- Final output"):
                            final_output_idx = idx
                            break
                    content_lines = []
                    if final_output_idx is not None:
                        for line in lines[final_output_idx+1:]:
                            if line.strip() and not line.strip().startswith("- ") and not line.strip().startswith("RunResult") and not line.strip().startswith("("):
                                content_lines.append(line.strip())
                            elif line.strip().startswith("- "):
                                break
                    if content_lines:
                        new_value = content_lines[0]
                    else:
                        new_value = mpd_description
                selenium_agent.set_mpd_description_field(new_value)

            # --- mpd_attributes ---
            mpd_description = selenium_agent.get_mpd_description_field()
            all_attributes = selenium_agent.get_all_mpd_attributes()
            if mpd_description and all_attributes:
                prompt = (
                    "Z poniższej listy atrybutów:\n"
                    + ", ".join(all_attributes) +
                    "\nwybierz tylko te, które pasują do poniższego opisu produktu (uwzględnij synonimy, odmiany, parafrazy, liczbę mnogą, itp., ale nie twórz własnych atrybutów). "
                    "Zwróć wyłącznie oryginalne teksty atrybutów z listy, oddzielone przecinkami. Nie twórz nowych atrybutów.\n"
                    "Przykład: jeśli w opisie jest 'wyższy stan', 'wysoki stan', 'figi z wysokim stanem', 'o wyższym stanie', wybierz atrybut 'wyższy stan'.\n"
                    "Opis produktu:\n"
                    + mpd_description
                )
                run_result = await Runner.run(agent_mpd_attributes, prompt)
                if hasattr(run_result, "output"):
                    attributes = run_result.output
                elif hasattr(run_result, "result"):
                    attributes = run_result.result
                else:
                    attributes = str(run_result)
                # Zamień na listę, jeśli to string
                if isinstance(attributes, str):
                    attributes = [a.strip()
                                  for a in attributes.split(",") if a.strip()]
                print("AI zwrócił atrybuty:", attributes)
                print("Dostępne atrybuty:", all_attributes)
                # Przefiltruj ignorując wielkość liter i spacje
                attributes = [
                    orig for orig in all_attributes
                    if any(orig.lower().strip() == a.lower().strip() for a in attributes)
                ]
                selenium_agent.set_mpd_attributes_field(attributes)

            # Wróć do listy produktów z filtrami
            selenium_agent.go_back_to_products_list(
                brand="Lupo Line",
                category_name="Kostiumy Dwuczęściowe"
            )
        else:
            print("⚠️  Nie znaleziono produktów do mapowania")

        # Czekaj i zamknij
        selenium_agent.wait_and_close(10)

    except Exception as e:
        print(f"❌ Błąd główny: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
