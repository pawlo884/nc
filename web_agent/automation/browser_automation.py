"""
Moduł automatyzacji przeglądarki Selenium.
"""
import logging
import time
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class BrowserAutomation:
    """Klasa do automatyzacji przeglądarki Chrome"""
    
    def __init__(self, base_url: str, username: str, password: str, headless: bool = False):
        """
        Inicjalizacja automatyzacji przeglądarki.
        
        Args:
            base_url: Bazowy URL aplikacji Django (np. http://localhost:8000)
            username: Nazwa użytkownika do logowania w admin
            password: Hasło użytkownika
            headless: Czy uruchomić przeglądarkę w trybie headless
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        logger.info(f"BrowserAutomation zainicjalizowany dla {base_url}")
    
    def start_browser(self):
        """Uruchomienie przeglądarki Chrome"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            logger.info("Przeglądarka Chrome uruchomiona")
            
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania przeglądarki: {e}")
            raise
    
    def login_to_admin(self):
        """Logowanie do admin Django"""
        try:
            login_url = f"{self.base_url}/admin/login/"
            logger.info(f"Logowanie do admin: {login_url}")
            
            self.driver.get(login_url)
            time.sleep(2)  # Czekaj na załadowanie strony
            
            # Znajdź pola logowania
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            # Wypełnij dane
            username_field.clear()
            username_field.send_keys(self.username)
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Kliknij przycisk logowania
            login_button = self.driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
            login_button.click()
            
            # Czekaj na przekierowanie do admin
            self.wait.until(
                EC.presence_of_element_located((By.ID, "content"))
            )
            
            logger.info("Zalogowano do admin Django")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Błąd podczas logowania do admin: {e}")
            raise
    
    def navigate_to_product_list(self, filters: Dict = None):
        """
        Przejście do listy produktów z filtrami.
        
        Args:
            filters: Słownik z filtrami (brand_id, category_id, active, is_mapped, brand_name)
        """
        try:
            # Najpierw sprawdź czy jesteśmy na stronie głównej admina
            current_url = self.driver.current_url
            logger.info(f"Aktualny URL: {current_url}")
            
            # Jeśli jesteśmy na stronie głównej admina, kliknij w link "Produkty"
            if '/admin/' in current_url and 'matterhorn1/product' not in current_url:
                logger.info("Szukanie linku 'Produkty'...")
                try:
                    # Poszukaj linku do produktów
                    product_link = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/admin/matterhorn1/product/']"))
                    )
                    logger.info("Znaleziono link 'Produkty', klikam...")
                    product_link.click()
                    time.sleep(3)
                except:
                    # Jeśli nie znaleziono przez CSS, spróbuj przez tekst
                    logger.info("Próba znalezienia przez tekst...")
                    product_link = self.wait.until(
                        EC.element_to_be_clickable((By.LINK_TEXT, "Produkty"))
                    )
                    product_link.click()
                    time.sleep(3)
            
            # Czekaj na załadowanie strony z filtrami
            self.wait.until(
                EC.presence_of_element_located((By.ID, "changelist-filter"))
            )
            logger.info("Strona z produktami i filtrami załadowana")
            time.sleep(2)
            
            # Zastosuj filtry klikając w panelu po prawej stronie
            if filters:
                # Filtr marki - kliknij w panel filtrów
                if filters.get('brand_name'):
                    brand_name = filters['brand_name']
                    logger.info(f"Szukanie filtra marki: {brand_name}")
                    
                    try:
                        # Znajdź panel filtrów
                        filter_panel = self.driver.find_element(By.ID, "changelist-filter")
                        
                        # Znajdź link z nazwą marki w panelu filtrów
                        # Szukamy linka który zawiera nazwę marki w tekście
                        brand_links = filter_panel.find_elements(By.TAG_NAME, "a")
                        
                        for link in brand_links:
                            link_text = link.text.strip()
                            # Sprawdź czy link zawiera nazwę marki (może być format "Nazwa (123)")
                            if brand_name.lower() in link_text.lower() and 'brand__id__exact' in link.get_attribute('href'):
                                logger.info(f"Znaleziono filtr marki: {link_text}")
                                # Przewiń do elementu
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                                time.sleep(0.5)
                                # Kliknij
                                link.click()
                                logger.info(f"Kliknięto filtr marki: {brand_name}")
                                time.sleep(3)
                                break
                        else:
                            logger.warning(f"Nie znaleziono filtra dla marki: {brand_name}")
                    except Exception as e:
                        logger.warning(f"Błąd podczas klikania filtra marki: {e}")
                
                # Filtr kategorii
                if filters.get('category_name'):
                    category_name = filters['category_name']
                    logger.info(f"Szukanie filtra kategorii: {category_name}")
                    
                    try:
                        filter_panel = self.driver.find_element(By.ID, "changelist-filter")
                        category_links = filter_panel.find_elements(By.TAG_NAME, "a")
                        
                        for link in category_links:
                            link_text = link.text.strip()
                            if category_name.lower() in link_text.lower() and 'category__id__exact' in link.get_attribute('href'):
                                logger.info(f"Znaleziono filtr kategorii: {link_text}")
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                                time.sleep(0.5)
                                link.click()
                                logger.info(f"Kliknięto filtr kategorii: {category_name}")
                                time.sleep(3)
                                break
                        else:
                            logger.warning(f"Nie znaleziono filtra dla kategorii: {category_name}")
                    except Exception as e:
                        logger.warning(f"Błąd podczas klikania filtra kategorii: {e}")
                
                # Filtr active
                if filters.get('active') is not None:
                    logger.info(f"Szukanie filtra active: {filters['active']}")
                    
                    try:
                        filter_panel = self.driver.find_element(By.ID, "changelist-filter")
                        active_links = filter_panel.find_elements(By.TAG_NAME, "a")
                        
                        search_text = "Tak" if filters['active'] else "Nie"
                        
                        for link in active_links:
                            if 'active__exact' in link.get_attribute('href') and search_text in link.text:
                                logger.info(f"Znaleziono filtr active: {link.text}")
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                                time.sleep(0.5)
                                link.click()
                                logger.info(f"Kliknięto filtr active")
                                time.sleep(3)
                                break
                    except Exception as e:
                        logger.warning(f"Błąd podczas klikania filtra active: {e}")
                
                # Filtr is_mapped
                if filters.get('is_mapped') is not None:
                    logger.info(f"Szukanie filtra is_mapped: {filters['is_mapped']}")
                    
                    try:
                        filter_panel = self.driver.find_element(By.ID, "changelist-filter")
                        mapped_links = filter_panel.find_elements(By.TAG_NAME, "a")
                        
                        search_text = "Tak" if filters['is_mapped'] else "Nie"
                        
                        for link in mapped_links:
                            if 'is_mapped__exact' in link.get_attribute('href') and search_text in link.text:
                                logger.info(f"Znaleziono filtr is_mapped: {link.text}")
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                                time.sleep(0.5)
                                link.click()
                                logger.info(f"Kliknięto filtr is_mapped")
                                time.sleep(3)
                                break
                    except Exception as e:
                        logger.warning(f"Błąd podczas klikania filtra is_mapped: {e}")
            
            # Czekaj na załadowanie listy produktów po zastosowaniu filtrów
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table#result_list tbody tr"))
            )
            
            logger.info("Lista produktów załadowana z filtrami")
            
        except Exception as e:
            logger.error(f"Błąd podczas przechodzenia do listy produktów: {e}")
            raise
    
    def get_product_ids_from_list(self) -> List[int]:
        """
        Pobranie ID produktów z listy.
        
        Returns:
            Lista ID produktów
        """
        try:
            product_ids = []
            
            # Znajdź wszystkie wiersze w tabeli
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table#result_list tbody tr")
            
            for row in rows:
                try:
                    # Pierwsza kolumna zawiera checkbox z value=product_id
                    checkbox = row.find_element(By.CSS_SELECTOR, "td input[type='checkbox']")
                    product_id = int(checkbox.get_attribute("value"))
                    product_ids.append(product_id)
                except (NoSuchElementException, ValueError):
                    continue
            
            logger.info(f"Znaleziono {len(product_ids)} produktów na liście")
            return product_ids
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania ID produktów: {e}")
            return []
    
    def navigate_to_product_change(self, product_id: int):
        """
        Przejście do strony change form produktu.
        
        Args:
            product_id: ID produktu
        """
        try:
            # Pobierz aktualny URL z filtrami (jeśli są)
            current_url = self.driver.current_url
            filters_part = ""
            if "?" in current_url:
                filters_part = "&" + current_url.split("?")[1] if len(current_url.split("?")) > 1 else ""
            
            change_url = f"{self.base_url}/admin/matterhorn1/product/{product_id}/change/{filters_part}"
            logger.info(f"Przechodzenie do strony produktu {product_id}: {change_url}")
            
            self.driver.get(change_url)
            time.sleep(2)  # Czekaj na załadowanie
            
            # Czekaj na załadowanie formularza
            self.wait.until(
                EC.presence_of_element_located((By.ID, "mpd-form"))
            )
            
            logger.info(f"Strona produktu {product_id} załadowana")
            
        except Exception as e:
            logger.error(f"Błąd podczas przechodzenia do strony produktu {product_id}: {e}")
            raise
    
    def extract_product_data(self) -> Dict:
        """
        Pobranie danych produktu ze strony.
        
        Returns:
            Słownik z danymi produktu
        """
        try:
            data = {}
            
            # Pobierz nazwę produktu (z lewej kolumny)
            try:
                name_field = self.driver.find_element(By.ID, "id_name")
                data['name'] = name_field.get_attribute("value") or ""
            except NoSuchElementException:
                data['name'] = ""
            
            # Pobierz opis produktu
            try:
                desc_field = self.driver.find_element(By.ID, "id_description")
                data['description'] = desc_field.get_attribute("value") or desc_field.text or ""
            except NoSuchElementException:
                data['description'] = ""
            
            # Pobierz markę
            try:
                brand_select = self.driver.find_element(By.ID, "id_brand")
                selected_option = brand_select.find_element(By.CSS_SELECTOR, "option:checked")
                data['brand_name'] = selected_option.text
            except NoSuchElementException:
                data['brand_name'] = ""
            
            # Pobierz kategorię
            try:
                category_select = self.driver.find_element(By.ID, "id_category")
                selected_option = category_select.find_element(By.CSS_SELECTOR, "option:checked")
                data['category_name'] = selected_option.text
            except NoSuchElementException:
                data['category_name'] = ""
            
            logger.info(f"Pobrano dane produktu: {data.get('name', 'Unknown')}")
            return data
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych produktu: {e}")
            return {}
    
    def fill_mpd_form(self, form_data: Dict):
        """
        Wypełnienie formularza MPD.
        
        Args:
            form_data: Słownik z danymi do wypełnienia formularza
        """
        try:
            logger.info("Wypełnianie formularza MPD")
            
            # Nazwa produktu
            if 'name' in form_data and form_data['name']:
                name_field = self.wait.until(
                    EC.presence_of_element_located((By.ID, "mpd_name"))
                )
                name_field.clear()
                name_field.send_keys(form_data['name'])
                time.sleep(0.5)
            
            # Opis
            if 'description' in form_data and form_data['description']:
                desc_field = self.driver.find_element(By.ID, "mpd_description")
                desc_field.clear()
                desc_field.send_keys(form_data['description'])
                time.sleep(0.5)
            
            # Krótki opis
            if 'short_description' in form_data and form_data['short_description']:
                short_desc_field = self.driver.find_element(By.ID, "mpd_short_description")
                short_desc_field.clear()
                short_desc_field.send_keys(form_data['short_description'])
                time.sleep(0.5)
            
            # Marka
            if 'brand_name' in form_data and form_data['brand_name']:
                brand_select = self.driver.find_element(By.ID, "mpd_brand")
                from selenium.webdriver.support.ui import Select
                select = Select(brand_select)
                try:
                    select.select_by_visible_text(form_data['brand_name'])
                    time.sleep(0.5)
                except:
                    logger.warning(f"Nie znaleziono marki: {form_data['brand_name']}")
            
            # Grupa rozmiarowa
            if 'size_category' in form_data and form_data['size_category']:
                size_select = self.driver.find_element(By.ID, "mpd_size_category")
                select = Select(size_select)
                try:
                    select.select_by_visible_text(form_data['size_category'])
                    time.sleep(0.5)
                except:
                    logger.warning(f"Nie znaleziono grupy rozmiarowej: {form_data['size_category']}")
            
            # Główny kolor
            if 'main_color_id' in form_data and form_data['main_color_id']:
                color_select = self.driver.find_element(By.ID, "main_color_id")
                select = Select(color_select)
                try:
                    select.select_by_value(str(form_data['main_color_id']))
                    time.sleep(0.5)
                except:
                    logger.warning(f"Nie znaleziono koloru: {form_data['main_color_id']}")
            
            # Kolor producenta
            if 'producer_color_name' in form_data and form_data['producer_color_name']:
                producer_color_field = self.driver.find_element(By.ID, "producer_color_name")
                producer_color_field.clear()
                producer_color_field.send_keys(form_data['producer_color_name'])
                time.sleep(0.5)
            
            # Kod producenta
            if 'producer_code' in form_data and form_data['producer_code']:
                producer_code_field = self.driver.find_element(By.ID, "producer_code")
                producer_code_field.clear()
                producer_code_field.send_keys(form_data['producer_code'])
                time.sleep(0.5)
            
            # Nazwa serii
            if 'series_name' in form_data and form_data['series_name']:
                series_field = self.driver.find_element(By.ID, "series_name")
                series_field.clear()
                series_field.send_keys(form_data['series_name'])
                time.sleep(0.5)
            
            # Jednostka
            if 'unit_id' in form_data and form_data['unit_id']:
                unit_select = self.driver.find_element(By.ID, "unit_id")
                select = Select(unit_select)
                try:
                    select.select_by_value(str(form_data['unit_id']))
                    time.sleep(0.5)
                except:
                    logger.warning(f"Nie znaleziono jednostki: {form_data['unit_id']}")
            
            # Atrybuty (multi-select)
            if 'attributes' in form_data and form_data['attributes']:
                attributes_select = self.driver.find_element(By.ID, "mpd_attributes")
                select = Select(attributes_select)
                for attr_id in form_data['attributes']:
                    try:
                        select.select_by_value(str(attr_id))
                    except:
                        pass
                time.sleep(0.5)
            
            # Ścieżki (multi-select)
            if 'paths' in form_data and form_data['paths']:
                paths_select = self.driver.find_element(By.ID, "mpd_paths")
                select = Select(paths_select)
                for path_id in form_data['paths']:
                    try:
                        select.select_by_value(str(path_id))
                    except:
                        pass
                time.sleep(0.5)
            
            logger.info("Formularz MPD wypełniony")
            
        except Exception as e:
            logger.error(f"Błąd podczas wypełniania formularza MPD: {e}")
            raise
    
    def submit_mpd_form(self):
        """Kliknięcie przycisku 'Utwórz nowy produkt w MPD'"""
        try:
            logger.info("Klikanie przycisku 'Utwórz nowy produkt w MPD'")
            
            # Znajdź przycisk
            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "create-mpd-product-btn"))
            )
            
            # Przewiń do przycisku
            self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(0.5)
            
            # Kliknij przycisk
            submit_button.click()
            logger.info("Przycisk kliknięty")
            
        except Exception as e:
            logger.error(f"Błąd podczas klikania przycisku: {e}")
            raise
    
    def wait_for_submission_result(self, timeout: int = 30) -> Dict:
        """
        Oczekiwanie na wynik wysłania formularza.
        
        Args:
            timeout: Maksymalny czas oczekiwania w sekundach
            
        Returns:
            Słownik z wynikiem (success, message, mpd_product_id)
        """
        try:
            logger.info("Oczekiwanie na wynik wysłania formularza")
            
            # Czekaj na pojawienie się komunikatu statusu
            status_message = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, "status-message"))
            )
            
            time.sleep(2)  # Czekaj na zaktualizowanie komunikatu
            
            # Sprawdź zawartość komunikatu
            message_text = status_message.text
            message_class = status_message.get_attribute("class")
            
            result = {
                'success': 'success' in message_class,
                'message': message_text,
                'mpd_product_id': None
            }
            
            # Spróbuj wyciągnąć ID produktu MPD z komunikatu
            if result['success'] and 'ID:' in message_text:
                try:
                    # Format: "Utworzono produkt w MPD (ID: 123)"
                    import re
                    match = re.search(r'ID:\s*(\d+)', message_text)
                    if match:
                        result['mpd_product_id'] = int(match.group(1))
                except:
                    pass
            
            logger.info(f"Wynik wysłania formularza: {result}")
            return result
            
        except TimeoutException:
            logger.warning("Timeout podczas oczekiwania na wynik")
            return {'success': False, 'message': 'Timeout', 'mpd_product_id': None}
        except Exception as e:
            logger.error(f"Błąd podczas oczekiwania na wynik: {e}")
            return {'success': False, 'message': str(e), 'mpd_product_id': None}
    
    def close_browser(self):
        """Zamknięcie przeglądarki"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                self.wait = None
                logger.info("Przeglądarka zamknięta")
        except Exception as e:
            logger.error(f"Błąd podczas zamykania przeglądarki: {e}")

