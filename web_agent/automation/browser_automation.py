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
import math

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
        self._original_product_name = None  # Przechowuje oryginalną nazwę przed edycją
        # Usuń /admin/ z końca URL jeśli jest
        base_url = base_url.rstrip('/').replace('/admin', '')
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        logger.info(f"BrowserAutomation zainicjalizowany dla {self.base_url}")

    def start_browser(self):
        """Uruchomienie przeglądarki Chrome"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(
                '--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option(
                'useAutomationExtension', False)

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(
                service=service, options=chrome_options)
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
            login_button = self.driver.find_element(
                By.CSS_SELECTOR, 'input[type="submit"]')
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
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "a[href='/admin/matterhorn1/product/']"))
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
                        filter_panel = self.driver.find_element(
                            By.ID, "changelist-filter")

                        # Sprawdź czy sekcja "brand" jest zwinięta - jeśli tak, rozwiń ją
                        try:
                            # Szukaj nagłówka sekcji z "brand" (może być "Pokaż ilości po brand" lub podobne)
                            # Spróbuj różne selektory
                            brand_sections = filter_panel.find_elements(
                                By.XPATH, ".//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'brand') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'marka')]")
                            if not brand_sections:
                                # Spróbuj znaleźć przez aria-labelledby lub inne atrybuty
                                brand_sections = filter_panel.find_elements(
                                    By.XPATH, ".//*[contains(translate(@aria-labelledby, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'brand') or contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'brand')]")

                            if not brand_sections:
                                # Spróbuj znaleźć wszystkie h3 w panelu i kliknąć w ten który zawiera "brand" lub "marka"
                                all_h3 = filter_panel.find_elements(
                                    By.TAG_NAME, "h3")
                                for h3 in all_h3:
                                    h3_text = h3.text.lower()
                                    if 'brand' in h3_text or 'marka' in h3_text:
                                        brand_sections = [h3]
                                        break

                            print(
                                f"[DEBUG] Znaleziono {len(brand_sections)} sekcji brand")

                            for section in brand_sections:
                                # Sprawdź czy sekcja jest zwinięta (collapsed)
                                try:
                                    parent = section.find_element(
                                        By.XPATH, "./..")
                                    parent_class = parent.get_attribute(
                                        'class') or ''
                                    if 'collapsed' in parent_class or 'closed' in parent_class:
                                        logger.info(
                                            "Rozwijanie sekcji filtrów brand...")
                                        section.click()
                                        time.sleep(2)
                                except Exception as e2:
                                    # Spróbuj kliknąć bezpośrednio w nagłówek
                                    logger.info(
                                        "Próba rozwinięcia sekcji brand przez kliknięcie w nagłówek...")
                                    section.click()
                                    time.sleep(2)
                        except Exception as e:
                            logger.debug(
                                f"Sekcja brand może być już rozwinięta: {e}")

                        # Filtry są w dropdownach (select) w divach z klasą "list-filter-dropdown"
                        # Struktura: <div class="list-filter-dropdown"><h3> po brand </h3><select>...</select></div>
                        brand_found = False
                        try:
                            # Znajdź div z klasą "list-filter-dropdown" który zawiera h3 z tekstem "po brand"
                            brand_dropdowns = filter_panel.find_elements(By.XPATH,
                                                                         ".//div[@class='list-filter-dropdown'][.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'brand')]]")

                            if brand_dropdowns:
                                # Znajdź select w tym divie
                                brand_selects = brand_dropdowns[0].find_elements(
                                    By.TAG_NAME, "select")
                                print(
                                    f"[DEBUG] Znaleziono {len(brand_selects)} selectów w dropdownie brand")

                            if brand_selects:
                                from selenium.webdriver.support.ui import Select
                                select = Select(brand_selects[0])
                                logger.info(
                                    f"Znaleziono dropdown brand, szukam opcji: {brand_name}")
                                print(
                                    f"[DEBUG] Znaleziono dropdown brand, szukam opcji: {brand_name}")

                                # Wypisz wszystkie opcje do debugowania
                                options = select.options
                                print(
                                    f"[DEBUG] Dostępne opcje w dropdown brand ({len(options)}):")
                                # Pierwsze 10
                                for i, opt in enumerate(options[:10]):
                                    print(f"  {i+1}. '{opt.text}'")

                                # Spróbuj wybrać po dokładnym tekście (może być "Marko (174)")
                                try:
                                    select.select_by_visible_text(brand_name)
                                    logger.info(
                                        f"Wybrano markę z dropdowna (dokładne): {brand_name}")
                                    print(
                                        f"[DEBUG] Wybrano markę z dropdowna (dokładne): {brand_name}")
                                    time.sleep(2)
                                    brand_found = True
                                except:
                                    # Spróbuj po częściowym dopasowaniu (ignoruj liczbę w nawiasach)
                                    for option in options:
                                        option_text = option.text.strip()
                                        option_text_clean = option_text.split(
                                            '(')[0].strip()

                                        if brand_name.lower() == option_text_clean.lower():
                                            select.select_by_visible_text(
                                                option_text)
                                            logger.info(
                                                f"Wybrano markę z dropdowna: {option_text}")
                                            time.sleep(2)
                                            brand_found = True
                                            break

                                    if not brand_found:
                                        # Spróbuj częściowe dopasowanie
                                        for option in options:
                                            option_text = option.text.strip()
                                            option_text_clean = option_text.split(
                                                '(')[0].strip()

                                            if brand_name.lower() in option_text_clean.lower():
                                                select.select_by_visible_text(
                                                    option_text)
                                                logger.info(
                                                    f"Wybrano markę z dropdowna (częściowe): {option_text}")
                                                time.sleep(2)
                                                brand_found = True
                                                break
                            else:
                                logger.warning(
                                    "Nie znaleziono dropdowna brand w panelu filtrów")
                        except Exception as e2:
                            logger.warning(
                                f"Błąd podczas wyboru marki z dropdowna: {e2}")

                        if not brand_found:
                            logger.warning(
                                f"Nie znaleziono filtra dla marki: {brand_name}")
                    except Exception as e:
                        logger.warning(
                            f"Błąd podczas klikania filtra marki: {e}")

                # Filtr kategorii - użyj dropdowna
                if filters.get('category_name'):
                    category_name = filters['category_name']
                    logger.info(f"Szukanie filtra kategorii: {category_name}")
                    print(
                        f"[DEBUG] Szukanie filtra kategorii: {category_name}")

                    try:
                        filter_panel = self.driver.find_element(
                            By.ID, "changelist-filter")
                        # Znajdź div z klasą "list-filter-dropdown" dla category
                        category_dropdowns = filter_panel.find_elements(By.XPATH,
                                                                        ".//div[@class='list-filter-dropdown'][.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'category')]]")

                        print(
                            f"[DEBUG] Znaleziono {len(category_dropdowns)} dropdownów kategorii")

                        if category_dropdowns:
                            category_selects = category_dropdowns[0].find_elements(
                                By.TAG_NAME, "select")
                            print(
                                f"[DEBUG] Znaleziono {len(category_selects)} selectów w dropdownie kategorii")

                            if category_selects:
                                from selenium.webdriver.support.ui import Select
                                select = Select(category_selects[0])

                                # Wypisz wszystkie opcje do debugowania (szukaj "kostiumy")
                                options = select.options
                                print(
                                    f"[DEBUG] Dostępne opcje w dropdown kategorii ({len(options)}):")
                                kostiumy_options = []
                                for i, opt in enumerate(options):
                                    opt_text = opt.text.strip()
                                    if 'kostiumy' in opt_text.lower() or 'kostium' in opt_text.lower():
                                        kostiumy_options.append(opt_text)
                                    if i < 10:
                                        print(f"  {i+1}. '{opt_text}'")

                                if kostiumy_options:
                                    print(
                                        f"[DEBUG] Opcje z 'kostiumy': {kostiumy_options}")

                                # Funkcja do normalizacji polskich znaków (tylko do porównań)
                                def normalize_for_comparison(text):
                                    """Normalizuje polskie znaki diakrytyczne dla porównań"""
                                    replacements = {
                                        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
                                        'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
                                        'Ą': 'a', 'Ć': 'c', 'Ę': 'e', 'Ł': 'l', 'Ń': 'n',
                                        'Ó': 'o', 'Ś': 's', 'Ź': 'z', 'Ż': 'z'
                                    }
                                    text_lower = text.lower()
                                    for old, new in replacements.items():
                                        text_lower = text_lower.replace(
                                            old, new)
                                    return text_lower

                                # Funkcja do obliczania podobieństwa słów (uwzględnia różnice w pisowni)
                                def word_similarity(word1, word2):
                                    """Oblicza podobieństwo między dwoma słowami"""
                                    w1 = normalize_for_comparison(word1)
                                    w2 = normalize_for_comparison(word2)

                                    # Dokładne dopasowanie po normalizacji
                                    if w1 == w2:
                                        return 1.0

                                    # Sprawdź czy jedno słowo zawiera się w drugim
                                    if w1 in w2 or w2 in w1:
                                        return 0.8

                                    # Oblicz podobieństwo na podstawie wspólnych liter
                                    common_chars = set(w1) & set(w2)
                                    all_chars = set(w1) | set(w2)

                                    if not all_chars:
                                        return 0.0

                                    return len(common_chars) / len(all_chars)

                                # Funkcja do obliczania podobieństwa z preferencją dla dokładniejszych dopasowań
                                def calculate_similarity(query, option):
                                    """Oblicza podobieństwo z preferencją dla opcji zawierających wszystkie słowa z zapytania"""
                                    # Podziel na słowa (bez normalizacji dla porównań słowo-słowo)
                                    query_words = [
                                        w for w in query.lower().split() if len(w) > 1]
                                    option_words = [
                                        w for w in option.lower().split() if len(w) > 1]

                                    if not query_words or not option_words:
                                        return 0.0

                                    # Dla każdego słowa z zapytania znajdź najlepsze dopasowanie w opcji
                                    total_similarity = 0.0
                                    matched_words = set()

                                    for q_word in query_words:
                                        best_match_score = 0.0
                                        best_match_word = None

                                        for o_word in option_words:
                                            if o_word in matched_words:
                                                continue

                                            similarity = word_similarity(
                                                q_word, o_word)
                                            if similarity > best_match_score:
                                                best_match_score = similarity
                                                best_match_word = o_word

                                        if best_match_word:
                                            matched_words.add(best_match_word)

                                        total_similarity += best_match_score

                                    # Średnie podobieństwo
                                    avg_similarity = total_similarity / \
                                        len(query_words) if query_words else 0.0

                                    # Bonus jeśli wszystkie słowa z zapytania mają dobre dopasowanie
                                    if avg_similarity > 0.7:
                                        avg_similarity = min(
                                            1.0, avg_similarity + 0.2)

                                    return avg_similarity

                                # Spróbuj znaleźć opcję z kategorią używając podobieństwa z preferencją dla dokładnych dopasowań
                                category_found = False
                                best_match = None
                                best_similarity = -1.0

                                print(
                                    f"[DEBUG] Szukanie kategorii '{category_name}' w {len(options)} opcjach...")

                                for option in options:
                                    option_text = option.text.strip()
                                    option_text_clean = option_text.split(
                                        '(')[0].strip()

                                    # Pomiń opcję "Wszystko"
                                    if option_text_clean.lower() in ['wszystko', 'all', '']:
                                        continue

                                    similarity = calculate_similarity(
                                        category_name, option_text_clean)

                                    # Wypisz szczegóły dla opcji z "kostiumy"
                                    if 'kostiumy' in option_text_clean.lower():
                                        print(
                                            f"[DEBUG] '{option_text_clean}': similarity={similarity:.3f}")

                                    if similarity > best_similarity:
                                        best_similarity = similarity
                                        best_match = option_text

                                # Wybierz najlepsze dopasowanie (nawet jeśli similarity jest niskie, ale wybierz najlepsze)
                                if best_match and best_similarity > 0:
                                    select.select_by_visible_text(best_match)
                                    logger.info(
                                        f"Wybrano kategorię z dropdowna (similarity: {best_similarity:.2f}): {best_match}")
                                    print(
                                        f"[DEBUG] Wybrano kategorię z dropdowna (similarity: {best_similarity:.2f}): {best_match}")
                                    time.sleep(2)
                                    category_found = True
                                else:
                                    logger.warning(
                                        f"Nie znaleziono kategorii '{category_name}' w dropdownie (najlepsze podobieństwo: {best_similarity:.2f})")
                                    print(
                                        f"[DEBUG] Nie znaleziono kategorii '{category_name}' w dropdownie (najlepsze podobieństwo: {best_similarity:.2f})")
                        else:
                            logger.warning(
                                f"Nie znaleziono dropdowna dla kategorii: {category_name}")
                            print(
                                f"[DEBUG] Nie znaleziono dropdowna dla kategorii: {category_name}")
                    except Exception as e:
                        logger.warning(
                            f"Błąd podczas wyboru kategorii z dropdowna: {e}")
                        print(
                            f"[DEBUG] Błąd podczas wyboru kategorii z dropdowna: {e}")
                        import traceback
                        traceback.print_exc()

                # Filtr active - użyj dropdowna
                if filters.get('active') is not None:
                    logger.info(f"Szukanie filtra active: {filters['active']}")

                    try:
                        filter_panel = self.driver.find_element(
                            By.ID, "changelist-filter")
                        active_dropdowns = filter_panel.find_elements(By.XPATH,
                                                                      ".//div[@class='list-filter-dropdown'][.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'active')]]")

                        if active_dropdowns:
                            active_selects = active_dropdowns[0].find_elements(
                                By.TAG_NAME, "select")
                            if active_selects:
                                from selenium.webdriver.support.ui import Select
                                select = Select(active_selects[0])
                        search_text = "Tak" if filters['active'] else "Nie"
                        select.select_by_visible_text(search_text)
                        logger.info(
                            f"Wybrano active z dropdowna: {search_text}")
                        time.sleep(2)
                    except Exception as e:
                        logger.warning(
                            f"Błąd podczas wyboru active z dropdowna: {e}")

                # Filtr is_mapped - użyj dropdowna
                if filters.get('is_mapped') is not None:
                    logger.info(
                        f"Szukanie filtra is_mapped: {filters['is_mapped']}")

                    try:
                        filter_panel = self.driver.find_element(
                            By.ID, "changelist-filter")
                        mapped_dropdowns = filter_panel.find_elements(By.XPATH,
                                                                      ".//div[@class='list-filter-dropdown'][.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mapped')]]")

                        if mapped_dropdowns:
                            mapped_selects = mapped_dropdowns[0].find_elements(
                                By.TAG_NAME, "select")
                            if mapped_selects:
                                from selenium.webdriver.support.ui import Select
                                select = Select(mapped_selects[0])
                        search_text = "Tak" if filters['is_mapped'] else "Nie"
                        select.select_by_visible_text(search_text)
                        logger.info(
                            f"Wybrano is_mapped z dropdowna: {search_text}")
                        time.sleep(2)
                    except Exception as e:
                        logger.warning(
                            f"Błąd podczas wyboru is_mapped z dropdowna: {e}")

            # Czekaj na załadowanie listy produktów po zastosowaniu filtrów
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "table#result_list tbody tr"))
            )

            logger.info("Lista produktów załadowana z filtrami")
            print("[DEBUG] Lista produktów załadowana z filtrami")
            time.sleep(2)  # Daj czas na pełne załadowanie

        except Exception as e:
            logger.error(f"Błąd podczas przechodzenia do listy produktów: {e}")
            raise

    def open_first_product_from_list(self):
        """
        Otwiera pierwszy produkt z listy produktów.
        """
        try:
            logger.info("Szukanie pierwszego produktu w liście...")
            print("[DEBUG] Szukanie pierwszego produktu w liście...")

            # Znajdź wszystkie wiersze w tabeli
            rows = self.driver.find_elements(
                By.CSS_SELECTOR, "table#result_list tbody tr")

            if not rows:
                logger.warning("Brak produktów w liście")
                print("[DEBUG] Brak produktów w liście")
                return

            logger.info(f"Znaleziono {len(rows)} produktów w liście")
            print(f"[DEBUG] Znaleziono {len(rows)} produktów w liście")
            first_row = rows[0]

            # Znajdź link do produktu w pierwszym wierszu
            try:
                # Spróbuj znaleźć wszystkie linki w wierszu
                links = first_row.find_elements(By.TAG_NAME, "a")
                print(
                    f"[DEBUG] Znaleziono {len(links)} linków w pierwszym wierszu")

                if links:
                    # Znajdź link który prowadzi do strony produktu (zawiera /change/)
                    product_link = None
                    for link in links:
                        href = link.get_attribute('href') or ''
                        print(f"[DEBUG] Link href: {href[:80]}")
                        if '/change/' in href or '/product/' in href:
                            product_link = link
                            break

                    if not product_link:
                        # Jeśli nie znaleziono, użyj pierwszego linka
                        product_link = links[0]

                    logger.info(
                        f"Znaleziono link do produktu: {product_link.get_attribute('href')}")
                    print(
                        f"[DEBUG] Klikam w link: {product_link.get_attribute('href')[:80]}")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", product_link)
                    time.sleep(0.5)
                    product_link.click()
                    logger.info("Kliknięto w pierwszy produkt z listy")
                    print("[DEBUG] Kliknięto w pierwszy produkt z listy")
                    time.sleep(3)  # Czekaj na załadowanie strony produktu
                    return
                else:
                    # Jeśli nie ma linka, kliknij w cały wiersz
                    logger.info("Brak linka, klikam w cały wiersz...")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", first_row)
                    time.sleep(0.5)
                    first_row.click()
                    logger.info("Kliknięto w pierwszy wiersz produktu")
                    print("[DEBUG] Kliknięto w pierwszy wiersz produktu")
                    time.sleep(3)
            except Exception as e2:
                logger.warning(
                    f"Błąd podczas klikania w link produktu: {e2}")
                # Spróbuj kliknąć w cały wiersz jako fallback
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", first_row)
                    time.sleep(0.5)
                    first_row.click()
                    logger.info(
                        "Kliknięto w pierwszy wiersz produktu (fallback)")
                    print("[DEBUG] Kliknięto w pierwszy wiersz produktu (fallback)")
                    time.sleep(3)
                except Exception as e3:
                    logger.error(f"Błąd podczas klikania w wiersz: {e3}")
                    raise

        except Exception as e:
            logger.error(f"Błąd podczas otwierania pierwszego produktu: {e}")
            print(f"[DEBUG] Błąd podczas otwierania pierwszego produktu: {e}")
            raise

    def open_product_from_list_by_index(self, index: int = 0):
        """
        Otwiera produkt z listy o danym indeksie.
        
        Args:
            index: Indeks produktu w liście (0 = pierwszy, 1 = drugi, itd.)
        """
        try:
            logger.info(f"Szukanie produktu o indeksie {index} w liście...")
            print(f"[DEBUG] Szukanie produktu o indeksie {index} w liście...")

            # Znajdź wszystkie wiersze w tabeli
            rows = self.driver.find_elements(
                By.CSS_SELECTOR, "table#result_list tbody tr")

            if not rows:
                logger.warning("Brak produktów w liście")
                print("[DEBUG] Brak produktów w liście")
                return False

            if index >= len(rows):
                logger.warning(f"Indeks {index} poza zakresem (dostępne: {len(rows)} produktów)")
                print(f"[DEBUG] Indeks {index} poza zakresem (dostępne: {len(rows)} produktów)")
                return False

            logger.info(f"Znaleziono {len(rows)} produktów w liście, otwieram produkt o indeksie {index}")
            print(f"[DEBUG] Znaleziono {len(rows)} produktów w liście, otwieram produkt o indeksie {index}")
            
            target_row = rows[index]

            # Znajdź link do produktu w wierszu
            try:
                links = target_row.find_elements(By.TAG_NAME, "a")
                print(f"[DEBUG] Znaleziono {len(links)} linków w wierszu {index}")

                if links:
                    # Znajdź link który prowadzi do strony produktu (zawiera /change/)
                    product_link = None
                    for link in links:
                        href = link.get_attribute('href') or ''
                        if '/change/' in href or '/product/' in href:
                            product_link = link
                            break

                    if not product_link:
                        product_link = links[0]

                    logger.info(f"Znaleziono link do produktu: {product_link.get_attribute('href')}")
                    print(f"[DEBUG] Klikam w link: {product_link.get_attribute('href')[:80]}")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", product_link)
                    time.sleep(0.5)
                    product_link.click()
                    logger.info(f"Kliknięto w produkt o indeksie {index}")
                    print(f"[DEBUG] Kliknięto w produkt o indeksie {index}")
                    time.sleep(3)  # Czekaj na załadowanie strony produktu
                    return True
                else:
                    logger.warning(f"Brak linka w wierszu {index}, klikam w cały wiersz...")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", target_row)
                    time.sleep(0.5)
                    target_row.click()
                    logger.info(f"Kliknięto w wiersz produktu o indeksie {index}")
                    print(f"[DEBUG] Kliknięto w wiersz produktu o indeksie {index}")
                    time.sleep(3)
                    return True
            except Exception as e2:
                logger.warning(f"Błąd podczas klikania w link produktu: {e2}")
                return False

        except Exception as e:
            logger.error(f"Błąd podczas otwierania produktu o indeksie {index}: {e}")
            print(f"[DEBUG] Błąd podczas otwierania produktu o indeksie {index}: {e}")
            return False

    def navigate_back_to_product_list(self, preserve_filters=True, filtered_list_url=None):
        """
        Wraca do listy produktów (klika przycisk "Wróć do listy" lub przechodzi do URL listy).
        
        Args:
            preserve_filters: Jeśli True, zachowuje parametry URL z filtrami
            filtered_list_url: Opcjonalny URL listy z filtrami (jeśli podano, użyj tego zamiast parsowania)
        """
        try:
            logger.info("Wracanie do listy produktów...")
            print("[DEBUG] Wracanie do listy produktów...")

            # Jeśli mamy zapisany URL listy z filtrami, użyj go
            if filtered_list_url:
                logger.info(f"Używam zapisanego URL listy z filtrami: {filtered_list_url}")
                print(f"[DEBUG] Używam zapisanego URL listy z filtrami: {filtered_list_url}")
                self.driver.get(filtered_list_url)
                time.sleep(2)
                logger.info("Przeszłem do zapisanej listy produktów z filtrami")
                print("[DEBUG] Przeszłem do zapisanej listy produktów z filtrami")
                return True

            current_url = self.driver.current_url
            
            # Jeśli już jesteśmy na liście produktów (nie na stronie produktu), odśwież stronę
            if '/change/' not in current_url and '/matterhorn1/product/' in current_url:
                # Jesteśmy już na liście - odśwież stronę, aby zachować filtry
                self.driver.refresh()
                time.sleep(2)
                logger.info("Odświeżono listę produktów (już byliśmy na liście)")
                print("[DEBUG] Odświeżono listę produktów (już byliśmy na liście)")
                return True

            # Spróbuj znaleźć przycisk "Wróć do listy" lub link
            try:
                back_link = self.driver.find_element(By.PARTIAL_LINK_TEXT, "Wróć")
                back_link.click()
                time.sleep(2)
                logger.info("Kliknięto przycisk 'Wróć do listy'")
                print("[DEBUG] Kliknięto przycisk 'Wróć do listy'")
                return True
            except:
                # Jeśli nie ma przycisku, przejdź bezpośrednio do URL listy
                # URL produktu: /admin/matterhorn1/product/12345/change/?_changelist_filter=...
                # URL listy: /admin/matterhorn1/product/?_changelist_filter=...
                import re
                
                # Wzorzec do usunięcia ID produktu z URL
                # Przykład: http://localhost:8080/admin/matterhorn1/product/12345/change/?params
                # Wynik: http://localhost:8080/admin/matterhorn1/product/?params
                from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
                
                parsed_url = urlparse(current_url)
                path_parts = parsed_url.path.split('/')
                
                # Znajdź indeks 'product' w ścieżce
                try:
                    product_idx = path_parts.index('product')
                    # Sprawdź czy następny element to ID produktu (liczba)
                    if product_idx + 1 < len(path_parts) and path_parts[product_idx + 1].isdigit():
                        # Usuń ID produktu i wszystko po nim w ścieżce
                        new_path_parts = path_parts[:product_idx + 1]  # ['', 'admin', 'matterhorn1', 'product']
                        new_path = '/'.join(new_path_parts) + '/'
                        
                        # Zachowaj parametry URL (filtry) jeśli są
                        if preserve_filters and parsed_url.query:
                            new_url = urlunparse((
                                parsed_url.scheme,
                                parsed_url.netloc,
                                new_path,
                                parsed_url.params,
                                parsed_url.query,  # Zachowaj parametry
                                parsed_url.fragment
                            ))
                        else:
                            new_url = urlunparse((
                                parsed_url.scheme,
                                parsed_url.netloc,
                                new_path,
                                parsed_url.params,
                                '',
                                parsed_url.fragment
                            ))
                        
                        self.driver.get(new_url)
                        time.sleep(2)
                        logger.info(f"Przeszłem do listy produktów: {new_url}")
                        print(f"[DEBUG] Przeszłem do listy produktów: {new_url}")
                        return True
                except (ValueError, IndexError):
                    # Nie znaleziono 'product' w ścieżce lub problem z parsowaniem
                    pass
                
                # Fallback - sprawdź czy już jesteśmy na liście
                if '/matterhorn1/product/' in current_url and '/change/' not in current_url:
                    # Sprawdź czy URL zawiera ID produktu
                    if re.search(r'/product/\d+/', current_url):
                        # Usuń ID produktu z URL
                        new_url = re.sub(r'(/product/)\d+(/)', r'\1\2', current_url)
                        if preserve_filters and '?' in current_url:
                            # Zachowaj parametry
                            pass  # new_url już ma parametry
                        else:
                            # Usuń parametry jeśli nie chcemy ich zachować
                            new_url = new_url.split('?')[0]
                        self.driver.get(new_url)
                        time.sleep(2)
                        logger.info(f"Przeszłem do listy produktów (fallback): {new_url}")
                        print(f"[DEBUG] Przeszłem do listy produktów (fallback): {new_url}")
                        return True
                    else:
                        # Już jesteśmy na liście - odśwież stronę
                        self.driver.refresh()
                        time.sleep(2)
                        logger.info("Odświeżono listę produktów (już byliśmy na liście)")
                        print("[DEBUG] Odświeżono listę produktów (już byliśmy na liście)")
                        return True
                else:
                    # Fallback - przejdź do podstawowej listy z zachowaniem hosta
                    parsed_url = urlparse(current_url)
                    list_url = urlunparse((
                        parsed_url.scheme,
                        parsed_url.netloc,
                        '/admin/matterhorn1/product/',
                        '',
                        '',
                        ''
                    ))
                    self.driver.get(list_url)
                    time.sleep(2)
                    logger.info(f"Przeszłem do podstawowej listy produktów: {list_url}")
                    print(f"[DEBUG] Przeszłem do podstawowej listy produktów: {list_url}")
                    return True
        except Exception as e:
            logger.warning(f"Błąd podczas wracania do listy produktów: {e}")
            print(f"[DEBUG] Błąd podczas wracania do listy produktów: {e}")
            return False

    def get_product_ids_from_list(self) -> List[int]:
        """
        Pobranie ID produktów z listy.

        Returns:
            Lista ID produktów
        """
        try:
            product_ids = []

            # Znajdź wszystkie wiersze w tabeli
            rows = self.driver.find_elements(
                By.CSS_SELECTOR, "table#result_list tbody tr")

            for row in rows:
                try:
                    # Pierwsza kolumna zawiera checkbox z value=product_id
                    checkbox = row.find_element(
                        By.CSS_SELECTOR, "td input[type='checkbox']")
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
                filters_part = "&" + \
                    current_url.split("?")[1] if len(
                        current_url.split("?")) > 1 else ""

            change_url = f"{self.base_url}/admin/matterhorn1/product/{product_id}/change/{filters_part}"
            logger.info(
                f"Przechodzenie do strony produktu {product_id}: {change_url}")

            self.driver.get(change_url)
            time.sleep(2)  # Czekaj na załadowanie

            # Czekaj na załadowanie formularza
            self.wait.until(
                EC.presence_of_element_located((By.ID, "mpd-form"))
            )

            logger.info(f"Strona produktu {product_id} załadowana")

        except Exception as e:
            logger.error(
                f"Błąd podczas przechodzenia do strony produktu {product_id}: {e}")
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
                data['description'] = desc_field.get_attribute(
                    "value") or desc_field.text or ""
            except NoSuchElementException:
                data['description'] = ""

            # Pobierz markę
            try:
                brand_select = self.driver.find_element(By.ID, "id_brand")
                selected_option = brand_select.find_element(
                    By.CSS_SELECTOR, "option:checked")
                data['brand_name'] = selected_option.text
            except NoSuchElementException:
                data['brand_name'] = ""

            # Pobierz kategorię
            try:
                category_select = self.driver.find_element(
                    By.ID, "id_category")
                selected_option = category_select.find_element(
                    By.CSS_SELECTOR, "option:checked")
                data['category_name'] = selected_option.text
            except NoSuchElementException:
                data['category_name'] = ""

            logger.info(
                f"Pobrano dane produktu: {data.get('name', 'Unknown')}")
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
                short_desc_field = self.driver.find_element(
                    By.ID, "mpd_short_description")
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
                    logger.warning(
                        f"Nie znaleziono marki: {form_data['brand_name']}")

            # Grupa rozmiarowa
            if 'size_category' in form_data and form_data['size_category']:
                size_select = self.driver.find_element(
                    By.ID, "mpd_size_category")
                select = Select(size_select)
                try:
                    select.select_by_visible_text(form_data['size_category'])
                    time.sleep(0.5)
                except:
                    logger.warning(
                        f"Nie znaleziono grupy rozmiarowej: {form_data['size_category']}")

            # Główny kolor
            if 'main_color_id' in form_data and form_data['main_color_id']:
                color_select = self.driver.find_element(By.ID, "main_color_id")
                select = Select(color_select)
                try:
                    select.select_by_value(str(form_data['main_color_id']))
                    time.sleep(0.5)
                except:
                    logger.warning(
                        f"Nie znaleziono koloru: {form_data['main_color_id']}")

            # Kolor producenta
            if 'producer_color_name' in form_data and form_data['producer_color_name']:
                producer_color_field = self.driver.find_element(
                    By.ID, "producer_color_name")
                producer_color_field.clear()
                producer_color_field.send_keys(
                    form_data['producer_color_name'])
                time.sleep(0.5)

            # Kod producenta
            if 'producer_code' in form_data and form_data['producer_code']:
                producer_code_field = self.driver.find_element(
                    By.ID, "producer_code")
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
                    logger.warning(
                        f"Nie znaleziono jednostki: {form_data['unit_id']}")

            # Atrybuty (multi-select)
            if 'attributes' in form_data and form_data['attributes']:
                attributes_select = self.driver.find_element(
                    By.ID, "mpd_attributes")
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
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", submit_button)
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

    def update_product_name(self, ai_processor=None):
        """
        Edycja nazwy produktu w polu mpd_name używając AI i struktury Pydantic.

        Args:
            ai_processor: Instancja AIProcessor do ulepszania nazwy. Jeśli None, tworzy nową.
        """
        try:
            logger.info("Rozpoczynam edycję nazwy produktu...")
            print("[DEBUG] Rozpoczynam edycję nazwy produktu...")

            # Czekaj na załadowanie pola mpd_name
            name_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "mpd_name"))
            )

            # Pobierz obecną nazwę (przed edycją - zapisz dla późniejszego użycia)
            current_name = name_field.get_attribute("value") or ""
            logger.info(f"Obecna nazwa produktu: {current_name}")
            print(f"[DEBUG] Obecna nazwa produktu: {current_name}")

            # Zapisz oryginalną nazwę jako atrybut instancji dla późniejszego użycia
            self._original_product_name = current_name

            if not current_name or not current_name.strip():
                logger.warning("Brak nazwy produktu do przetworzenia")
                print("[DEBUG] Brak nazwy produktu do przetworzenia")
                return

            # Użyj AIProcessor do ulepszenia nazwy (ze strukturą Pydantic)
            if ai_processor is None:
                from web_agent.automation.ai_processor import AIProcessor
                ai_processor = AIProcessor()

            logger.info("Ulepszanie nazwy przez AI...")
            print("[DEBUG] Ulepszanie nazwy przez AI...")
            new_name = ai_processor.enhance_product_name(
                current_name, use_structured=True)

            if not new_name:
                raise ValueError("Ulepszona nazwa produktu jest pusta")

            logger.info(f"Nowa nazwa produktu: {new_name}")
            print(f"[DEBUG] Nowa nazwa produktu: {new_name}")

            # Wyczyść pole i wpisz nową nazwę
            # Użyj JavaScript do ustawienia wartości (bardziej niezawodne)
            self.driver.execute_script(
                "arguments[0].value = arguments[1];",
                name_field,
                new_name
            )
            time.sleep(0.3)

            # Wywołaj zdarzenia aby upewnić się, że zmiana została zarejestrowana
            self.driver.execute_script(
                """
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """,
                name_field
            )
            time.sleep(0.3)

            # Sprawdź czy wartość została ustawiona
            actual_value = self.driver.execute_script(
                "return arguments[0].value;", name_field)
            if actual_value == new_name:
                logger.info(f"Pole nazwy zostało wypełnione: {new_name}")
                print(f"[DEBUG] Pole nazwy zostało wypełnione: {new_name}")
            else:
                logger.warning(
                    f"Wartość nazwy nie została poprawnie ustawiona. Oczekiwano: {new_name}, otrzymano: {actual_value}")
                print(
                    f"[DEBUG] Wartość nazwy nie została poprawnie ustawiona. Oczekiwano: {new_name}, otrzymano: {actual_value}")
                # Spróbuj przez send_keys jako fallback
                name_field.clear()
                time.sleep(0.2)
                name_field.send_keys(new_name)
                time.sleep(0.3)

            # Nie zapisujemy - zostanie zapisane przy tworzeniu produktu w MPD
            logger.info(
                "Pole nazwy zostało wypełnione. Nie zapisuję - zostanie zapisane przy tworzeniu produktu w MPD.")
            print(
                "[DEBUG] Pole nazwy zostało wypełnione. Nie zapisuję - zostanie zapisane przy tworzeniu produktu w MPD.")

        except Exception as e:
            logger.error(f"Błąd podczas edycji nazwy produktu: {e}")
            print(f"[DEBUG] Błąd podczas edycji nazwy produktu: {e}")
            raise

    def update_producer_color(self, original_name: str, brand_id: int = None, brand_name: str = None):
        """
        Wyodrębnia kolor producenta z oryginalnej nazwy produktu i wypełnia pole producer_color_name.
        Najpierw sprawdza bazę kolorów dla danej marki i próbuje dopasować, jeśli nie znajdzie - ekstrachuje z nazwy.

        Args:
            original_name: Oryginalna nazwa produktu przed edycją (np. "Kostium dwuczęściowy Kostium kąpielowy Model Ada M-803 (1) Lilia - Marko")
            brand_id: ID marki (opcjonalne)
            brand_name: Nazwa marki (opcjonalne)
        """
        try:
            logger.info("Wyodrębnianie koloru producenta...")
            print("[DEBUG] Wyodrębnianie koloru producenta...")

            color_name = None

            # 1. NAJPIERW wyodrębnij kolor z nazwy (regex-based, NIE Pydantic)
            #    Obsługuje kolory złożone: jeśli kolor zawiera "/" (np. "Coral/Blue"), oznacza to DWA KOLORY
            logger.info("Wyodrębnianie koloru producenta z nazwy produktu...")
            print("[DEBUG] Wyodrębnianie koloru producenta z nazwy produktu...")
            print("[DEBUG] UWAGA: Jeśli kolor zawiera '/' (np. 'Coral/Blue'), oznacza to DWA KOLORY")
            color_name = self._extract_color_from_name(original_name)

            if not color_name:
                logger.warning(
                    "Nie udało się wyodrębnić koloru z nazwy produktu")
                print("[DEBUG] Nie udało się wyodrębnić koloru z nazwy produktu")
                return

            logger.info(
                f"Wyodrębniony kolor producenta z nazwy: {color_name}")
            print(
                f"[DEBUG] Wyodrębniony kolor producenta z nazwy: {color_name}")

            # 2. Sprawdź czy wyodrębniony kolor istnieje w bazie dla danej marki
            if color_name and brand_id and brand_name:
                from web_agent.models import ProducerColor
                try:
                    # Sprawdź czy dokładnie taki kolor istnieje w bazie
                    color_obj = ProducerColor.objects.get(
                        brand_id=brand_id,
                        color_name=color_name
                    )
                    # Zwiększ licznik użycia
                    color_obj.usage_count += 1
                    color_obj.save(update_fields=['usage_count', 'updated_at'])
                    logger.info(
                        f"Znaleziono kolor w bazie (dokładne dopasowanie): {color_name} (użycie #{color_obj.usage_count})")
                    print(
                        f"[INFO] Znaleziono kolor w bazie (dokładne dopasowanie): {color_name} (użycie #{color_obj.usage_count})")
                except ProducerColor.DoesNotExist:
                    # Jeśli nie istnieje, zapisz nowy kolor do bazy
                    color_obj, created = ProducerColor.objects.get_or_create(
                        brand_id=brand_id,
                        color_name=color_name,
                        defaults={'brand_name': brand_name}
                    )
                    if created:
                        logger.info(
                            f"Dodano nowy kolor do bazy: {color_name} dla marki {brand_name}")
                        print(
                            f"[INFO] Dodano nowy kolor do bazy: {color_name} dla marki {brand_name}")
                    else:
                        # Zwiększ licznik użyć
                        color_obj.usage_count += 1
                        color_obj.save(
                            update_fields=['usage_count', 'updated_at'])
                        logger.info(
                            f"Kolor już istnieje w bazie (użycie #{color_obj.usage_count})")
                        print(
                            f"[DEBUG] Kolor już istnieje w bazie (użycie #{color_obj.usage_count})")
            
            # 3. Fallback: Jeśli nie udało się wyodrębnić z nazwy, sprawdź bazę (dla pojedynczych kolorów)
            if not color_name and brand_id and brand_name:
                from web_agent.models import ProducerColor
                existing_colors = ProducerColor.objects.filter(
                    brand_id=brand_id)

                if existing_colors.exists():
                    logger.info(
                        f"Sprawdzam {existing_colors.count()} kolorów w bazie dla marki {brand_name} (fallback)...")
                    print(
                        f"[DEBUG] Sprawdzam {existing_colors.count()} kolorów w bazie dla marki {brand_name} (fallback)...")

                    # Spróbuj dopasować kolory z bazy do nazwy produktu (DOKŁADNE DOPASOWANIE)
                    # Sortuj kolory po długości (najdłuższe pierwsze) - żeby "red ferrari" było sprawdzone przed "red"
                    sorted_colors = sorted(
                        existing_colors, key=lambda x: len(x.color_name), reverse=True)
                    original_name_lower = original_name.lower()

                    import re
                    for color_obj in sorted_colors:
                        color_lower = color_obj.color_name.lower()
                        # Dokładne dopasowanie - kolor musi być osobnym słowem (nie częścią innego słowa)
                        # Używamy word boundaries (\b) w regex
                        pattern = r'\b' + re.escape(color_lower) + r'\b'
                        if re.search(pattern, original_name_lower):
                            color_name = color_obj.color_name
                            # Zwiększ licznik użyć
                            color_obj.usage_count += 1
                            color_obj.save(
                                update_fields=['usage_count', 'updated_at'])
                            logger.info(
                                f"Znaleziono kolor w bazie (fallback): {color_name} (użycie #{color_obj.usage_count})")
                            print(
                                f"[INFO] Znaleziono kolor w bazie (fallback): {color_name} (użycie #{color_obj.usage_count})")
                            break

            # Wypełnij pole producer_color_name
            try:
                producer_color_field = self.wait.until(
                    EC.presence_of_element_located(
                        (By.ID, "producer_color_name"))
                )

                # Wyczyść pole i wpisz kolor
                self.driver.execute_script(
                    "arguments[0].value = '';", producer_color_field)
                time.sleep(0.2)

                self.driver.execute_script(
                    "arguments[0].value = arguments[1];",
                    producer_color_field,
                    color_name
                )
                time.sleep(0.3)

                # Wywołaj zdarzenia
                self.driver.execute_script(
                    """
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """,
                    producer_color_field
                )
                time.sleep(0.3)

                # Zapamiętaj ostatnio wyodrębniony kolor, aby można go było użyć przy tworzeniu produktu w MPD
                self._last_extracted_producer_color = color_name

                logger.info(
                    f"Pole producer_color_name zostało wypełnione: {color_name}")
                print(
                    f"[DEBUG] Pole producer_color_name zostało wypełnione: {color_name}")

            except Exception as e:
                logger.warning(
                    f"Nie udało się wypełnić pola producer_color_name: {e}")
                print(
                    f"[DEBUG] Nie udało się wypełnić pola producer_color_name: {e}")

        except Exception as e:
            logger.warning(
                f"Błąd podczas wyodrębniania koloru producenta: {e}")
            print(f"[DEBUG] Błąd podczas wyodrębniania koloru producenta: {e}")

    def _extract_color_from_name(self, name: str) -> str:
        """
        Wyodrębnia kolor producenta z nazwy produktu.
        Kolor zwykle znajduje się przed nazwą marki (np. "Lilia - Marko" -> "Lilia")
        Obsługuje kolory złożone z "/" (np. "Seledyn/Black", "Coral/Blue")

        Args:
            name: Pełna nazwa produktu przed edycją

        Returns:
            Nazwa koloru producenta lub pusty string
        """
        if not name:
            return ""

        name = name.strip()
        logger.debug(f"_extract_color_from_name: Analizuję nazwę: {name}")
        print(f"[DEBUG] _extract_color_from_name: Analizuję nazwę: {name}")

        # Wzorce do wyodrębniania koloru (regex-based, NIE Pydantic):
        # 1. "Kolor - Marka" (np. "Lilia - Marko", "Seledyn/Black - Marko")
        #    UWAGA: Jeśli kolor zawiera "/" (np. "Coral/Blue"), oznacza to DWA KOLORY
        # 2. "(liczba) Kolor" (np. "(1) Lilia", "(2) Seledyn/Black", "(4) Coral/Blue")
        #    UWAGA: Jeśli kolor zawiera "/" (np. "Coral/Blue"), oznacza to DWA KOLORY
        # 3. Ostatnie słowo/część przed "- Marka"
        #    UWAGA: Jeśli kolor zawiera "/" (np. "Black/Pink"), oznacza to DWA KOLORY

        import re

        # Wzorzec 1: "Kolor - Marka" na końcu (obsługuje kolory z "/")
        # Dopasowuje: "Seledyn/Black", "Lilia", "Black/White", "Coral/Blue" itp.
        match = re.search(
            r'([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\/[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\/[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)*)\s*-\s*[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+$', name)
        if match:
            color = match.group(1).strip()
            logger.debug(f"_extract_color_from_name: Wzorzec 1 znalazł: {color}")
            print(f"[DEBUG] _extract_color_from_name: Wzorzec 1 znalazł: {color}")
            if len(color) > 1 and len(color) < 50:  # Rozsądna długość koloru
                return color

        # Wzorzec 2: "(liczba) Kolor" (np. "(1) Lilia", "(2) Seledyn/Black", "(4) Coral/Blue")
        # To jest najczęstszy wzorzec dla produktów z numerami wariantów
        match = re.search(
            r'\([^)]+\)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\/[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\/[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)*)\s*-\s*[A-ZĄĆĘŁŃÓŚŹŻ]', name)
        if match:
            color = match.group(1).strip()
            logger.debug(f"_extract_color_from_name: Wzorzec 2 znalazł: {color}")
            print(f"[DEBUG] _extract_color_from_name: Wzorzec 2 znalazł: {color}")
            if len(color) > 1 and len(color) < 50:
                return color

        # Wzorzec 3: Ostatnie słowo/część przed ostatnim "-" (jeśli jest)
        # Obsługuje kolory z "/" (np. "Seledyn/Black", "Coral/Blue")
        parts = name.split(' - ')
        if len(parts) >= 2:
            # Weź ostatnią część przed ostatnim "-"
            before_last_dash = parts[-2].strip()
            # Weź ostatnie słowo/część (może zawierać "/")
            words = before_last_dash.split()
            if words:
                last_word = words[-1]
                logger.debug(f"_extract_color_from_name: Wzorzec 3 - ostatnie słowo: {last_word}")
                print(f"[DEBUG] _extract_color_from_name: Wzorzec 3 - ostatnie słowo: {last_word}")
                # Sprawdź czy to wygląda na kolor (zaczyna się wielką literą, nie jest liczbą)
                # Może zawierać "/" (np. "Seledyn/Black", "Coral/Blue")
                if last_word and last_word[0].isupper() and not last_word.replace('(', '').replace(')', '').replace('/', '').isdigit():
                    if len(last_word) > 1 and len(last_word) < 50:
                        logger.debug(f"_extract_color_from_name: Wzorzec 3 zwraca: {last_word}")
                        print(f"[DEBUG] _extract_color_from_name: Wzorzec 3 zwraca: {last_word}")
                        return last_word

        logger.debug(f"_extract_color_from_name: Nie znaleziono koloru")
        print(f"[DEBUG] _extract_color_from_name: Nie znaleziono koloru")
        return ""

    def update_producer_code(self, original_name: str):
        """
        Wyodrębnia kod producenta z oryginalnej nazwy produktu i wypełnia pole producer_code.
        Pattern: M-XXX (np. M-803)

        Args:
            original_name: Oryginalna nazwa produktu przed edycją (np. "Kostium dwuczęściowy Kostium kąpielowy Model Ada M-803 (1) Lilia - Marko")
        """
        try:
            logger.info("Wyodrębnianie kodu producenta z nazwy produktu...")
            print("[DEBUG] Wyodrębnianie kodu producenta z nazwy produktu...")

            # Wyodrębnij kod producenta (pattern: M-XXX)
            producer_code = self._extract_producer_code_from_name(
                original_name)

            if not producer_code:
                logger.warning(
                    "Nie udało się wyodrębnić kodu producenta z nazwy produktu")
                print(
                    "[DEBUG] Nie udało się wyodrębnić kodu producenta z nazwy produktu")
                return

            logger.info(f"Wyodrębniony kod producenta: {producer_code}")
            print(f"[DEBUG] Wyodrębniony kod producenta: {producer_code}")

            # Wypełnij pole producer_code
            try:
                producer_code_field = self.wait.until(
                    EC.presence_of_element_located((By.ID, "producer_code"))
                )

                # Wyczyść pole i wpisz kod
                self.driver.execute_script(
                    "arguments[0].value = '';", producer_code_field)
                time.sleep(0.2)

                self.driver.execute_script(
                    "arguments[0].value = arguments[1];",
                    producer_code_field,
                    producer_code
                )
                time.sleep(0.3)

                # Wywołaj zdarzenia
                self.driver.execute_script(
                    """
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """,
                    producer_code_field
                )
                time.sleep(0.3)

                logger.info(
                    f"Pole producer_code zostało wypełnione: {producer_code}")
                print(
                    f"[DEBUG] Pole producer_code zostało wypełnione: {producer_code}")

            except Exception as e:
                logger.warning(
                    f"Nie udało się wypełnić pola producer_code: {e}")
                print(
                    f"[DEBUG] Nie udało się wypełnić pola producer_code: {e}")

        except Exception as e:
            logger.warning(f"Błąd podczas wyodrębniania kodu producenta: {e}")
            print(f"[DEBUG] Błąd podczas wyodrębniania kodu producenta: {e}")

    def _extract_producer_code_from_name(self, name: str) -> str:
        """
        Wyodrębnia kod producenta z nazwy produktu.
        Pattern: M-XXX (np. M-803, M-123, M-45)

        Args:
            name: Pełna nazwa produktu przed edycją

        Returns:
            Kod producenta (np. "M-803") lub pusty string
        """
        if not name:
            return ""

        import re

        # Wzorzec: M-XXX gdzie XXX to cyfry
        # Może być też M-XXX-YYY (np. M-803-1)
        pattern = r'\bM-\d+(?:-\d+)?\b'
        match = re.search(pattern, name, re.IGNORECASE)

        if match:
            code = match.group(0)
            # Znormalizuj do wielkich liter
            return code.upper()

        return ""

    def _process_product_name(self, name: str) -> str:
        """
        Przetwarza nazwę produktu z formatu pełnego na uproszczony.

        Przykład:
        Input: " Kostium dwuczęściowy Kostium kąpielowy Model Ada M-803 (1) Lilia - Marko "
        Output: "Kostium kąpielowy Ada"
        """
        if not name:
            return ""

        # Usuń białe znaki na początku i końcu
        name = name.strip()

        # Podziel na słowa
        words = name.split()

        # Znajdź "Kostium kąpielowy" (lub podobne)
        result_parts = []
        found_kostium_kapielowy = False
        found_model = False

        i = 0
        while i < len(words):
            word = words[i]
            word_lower = word.lower()

            # Szukaj "Kostium kąpielowy" (pomiń "Kostium dwuczęściowy")
            if word_lower == "kostium" and i + 1 < len(words):
                next_word = words[i + 1].lower()
                if next_word in ["kąpielowy", "kapielowy", "kąpielowe", "kapielowe"]:
                    if not found_kostium_kapielowy:
                        result_parts.append("Kostium")
                        result_parts.append("kąpielowy")
                        found_kostium_kapielowy = True
                        i += 2
                        continue
                elif next_word in ["dwuczęściowy", "dwuczesciowy", "dwuczęściowe", "dwuczesciowe"]:
                    # Pomiń "Kostium dwuczęściowy"
                    i += 2
                    continue

            # Szukaj "Model" i następujące po nim słowo (nazwa modelu)
            if word_lower == "model" and i + 1 < len(words):
                model_name = words[i + 1]
                # Usuń znaki specjalne z nazwy modelu jeśli są
                model_name_clean = model_name.strip('()[]{}.,;:')
                if model_name_clean and not found_model:
                    result_parts.append(model_name_clean)
                    found_model = True
                    i += 2
                    continue

            # Pomiń znaki specjalne, numery w nawiasach, marki na końcu
            if word_lower in ["-", "–", "—"]:
                # Jeśli jest "-" to prawdopodobnie kończy się marką, przestań przetwarzać
                break

            # Pomiń numery w nawiasach jak "(1)", "(2)" itp.
            if word.startswith('(') and word.endswith(')'):
                try:
                    int(word[1:-1])
                    i += 1
                    continue
                except ValueError:
                    pass

            # Pomiń kody modeli jak "M-803", "M-123" itp.
            if '-' in word and len(word) > 2 and word[0].isupper() and word[1] == '-':
                i += 1
                continue

            i += 1

        # Jeśli nie znaleziono "Kostium kąpielowy", spróbuj znaleźć "Kostium"
        if not found_kostium_kapielowy:
            for i, word in enumerate(words):
                if word.lower() == "kostium" and i + 1 < len(words):
                    next_word = words[i + 1].lower()
                    if next_word not in ["dwuczęściowy", "dwuczesciowy"]:
                        result_parts.insert(0, "Kostium")
                        if next_word not in ["kąpielowy", "kapielowy"]:
                            result_parts.append(next_word)
                        break

        # Połącz części w wynik
        result = " ".join(result_parts).strip()

        # Jeśli wynik jest pusty, zwróć oryginalną nazwę (bez białych znaków)
        if not result:
            return name.strip()

        return result

    def fill_mpd_description(self, ai_processor=None):
        """
        SCENARIUSZ CREATE, KROK 2: Wypełnia pole mpd_description w sekcji MPD.

        Pobiera opis produktu z głównego formularza Django (id_description) lub
        z pola mpd_description (jeśli już istnieje), ulepsza go przez AI
        i ustawia w polu mpd_description.

        Args:
            ai_processor: Instancja AIProcessor do ulepszania opisu. Jeśli None, tworzy nową.

        Returns:
            str: Ulepszony opis produktu lub None w przypadku błędu
        """
        try:
            logger.info("=" * 50)
            logger.info(
                "SCENARIUSZ CREATE, KROK 2: Wypełnianie pola mpd_description")
            logger.info("=" * 50)
            print("[DEBUG] " + "=" * 50)
            print("[DEBUG] SCENARIUSZ CREATE, KROK 2: Wypełnianie pola mpd_description")
            print("[DEBUG] " + "=" * 50)

            # KROK 0: Upewnij się, że sekcja right-column jest rozwinięta
            self._ensure_right_column_expanded()
            time.sleep(0.5)

            # KROK 2.1: Znajdź pole mpd_description w sekcji MPD
            try:
                mpd_desc_field = self.wait.until(
                    EC.presence_of_element_located((By.ID, "mpd_description"))
                )
            except Exception as e:
                logger.error(
                    f"Nie udało się znaleźć pola mpd_description: {e}")
                print(
                    f"[DEBUG] Nie udało się znaleźć pola mpd_description: {e}")
                return None

            # KROK 2.2: Pobierz obecny opis z pola mpd_description
            current_description = mpd_desc_field.get_attribute(
                "value") or mpd_desc_field.text or ""

            # KROK 2.3: Jeśli pole mpd_description jest puste, pobierz opis z formularza Django (id_description)
            if not current_description or not current_description.strip():
                try:
                    django_desc_field = self.wait.until(
                        EC.presence_of_element_located(
                            (By.ID, "id_description"))
                    )
                    current_description = django_desc_field.get_attribute(
                        "value") or django_desc_field.text or ""
                    logger.info(
                        f"Pobrano opis z formularza Django (długość: {len(current_description)})")
                    print(
                        f"[DEBUG] Pobrano opis z formularza Django (długość: {len(current_description)})")
                except Exception as e:
                    logger.warning(
                        f"Nie udało się pobrać opisu z formularza Django: {e}")
                    print(
                        f"[DEBUG] Nie udało się pobrać opisu z formularza Django: {e}")

            if not current_description or not current_description.strip():
                logger.warning("Brak opisu do ulepszenia")
                print("[DEBUG] Brak opisu do ulepszenia")
                return None

            logger.info(
                f"Obecny opis produktu (długość: {len(current_description)})")
            print(
                f"[DEBUG] Obecny opis produktu (długość: {len(current_description)})")

            # KROK 2.4: Ulepsz opis przez AI
            if ai_processor is None:
                from web_agent.automation.ai_processor import AIProcessor
                ai_processor = AIProcessor()

            logger.info("Ulepszanie opisu przez AI...")
            print("[INFO] ========================================")
            print("[INFO] ULEPSZANIE OPISU PRZEZ AI")
            print("[INFO] ========================================")
            print(
                f"[INFO] Długość oryginalnego opisu: {len(current_description)} znaków")
            print("[INFO] Wysyłam żądanie do API...")
            print("[INFO] To może zająć do 30 sekund - proszę czekać...")
            enhanced_description = ai_processor.enhance_product_description(
                current_description)
            print("[INFO] ========================================")
            print(
                f"[INFO] Opis został ulepszony! Nowa długość: {len(enhanced_description)} znaków")
            print("[INFO] ========================================")

            if not enhanced_description or enhanced_description == current_description:
                logger.warning(
                    "Opis nie został ulepszony lub jest identyczny - użyję oryginalnego opisu")
                print(
                    "[DEBUG] Opis nie został ulepszony lub jest identyczny - użyję oryginalnego opisu")
                enhanced_description = current_description

            logger.info(
                f"Ulepszona opis produktu (długość: {len(enhanced_description)})")
            print(
                f"[DEBUG] Ulepszona opis produktu (długość: {len(enhanced_description)})")

            # KROK 2.5: Ustaw wartość w polu mpd_description przez JavaScript
            # Najpierw focus na pole
            self.driver.execute_script("arguments[0].focus();", mpd_desc_field)
            time.sleep(0.2)

            # Wyczyść pole przez JavaScript
            self.driver.execute_script(
                "arguments[0].value = '';", mpd_desc_field)
            time.sleep(0.2)

            # Ustaw wartość przez JavaScript
            self.driver.execute_script(
                "arguments[0].value = arguments[1];",
                mpd_desc_field,
                enhanced_description
            )
            time.sleep(0.3)

            # Wywołaj zdarzenia, aby React zarejestrował zmianę
            self.driver.execute_script(
                """
                var field = arguments[0];
                field.dispatchEvent(new Event('input', { bubbles: true }));
                field.dispatchEvent(new Event('change', { bubbles: true }));
                field.dispatchEvent(new Event('blur', { bubbles: true }));
                """,
                mpd_desc_field
            )
            time.sleep(0.5)

            # KROK 2.6: Weryfikacja - sprawdź czy wartość została ustawiona
            actual_value = self.driver.execute_script(
                "return arguments[0].value;", mpd_desc_field)

            if not actual_value or len(actual_value) < len(enhanced_description) * 0.8:
                logger.warning(
                    f"⚠ Wartość mpd_description nie została poprawnie ustawiona. "
                    f"Oczekiwano: {len(enhanced_description)} znaków, otrzymano: {len(actual_value) if actual_value else 0} znaków")
                print(
                    f"[DEBUG] ⚠ Wartość mpd_description nie została poprawnie ustawiona. "
                    f"Oczekiwano: {len(enhanced_description)} znaków, otrzymano: {len(actual_value) if actual_value else 0} znaków")
                print(f"[DEBUG] Próbuję alternatywną metodę - send_keys")

                # Fallback: spróbuj przez send_keys
                try:
                    mpd_desc_field.clear()
                    time.sleep(0.2)
                    mpd_desc_field.send_keys(enhanced_description)
                    time.sleep(0.5)
                    # Ponownie wywołaj zdarzenia
                    self.driver.execute_script(
                        """
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                        """,
                        mpd_desc_field
                    )
                    # Sprawdź ponownie
                    actual_value = self.driver.execute_script(
                        "return arguments[0].value;", mpd_desc_field)
                    if not actual_value or len(actual_value) < len(enhanced_description) * 0.8:
                        logger.error(
                            f"Nie udało się ustawić wartości w polu mpd_description")
                        print(
                            f"[DEBUG] Nie udało się ustawić wartości w polu mpd_description")
                        return None
                    else:
                        logger.info(
                            f"✓ Pole mpd_description wypełnione przez send_keys (długość: {len(actual_value)})")
                        print(
                            f"[DEBUG] ✓ Pole mpd_description wypełnione przez send_keys (długość: {len(actual_value)})")
                except Exception as e_fallback:
                    logger.error(
                        f"Nie udało się wypełnić mpd_description przez send_keys: {e_fallback}")
                    print(
                        f"[DEBUG] Nie udało się wypełnić mpd_description przez send_keys: {e_fallback}")
                    return None
            else:
                logger.info(
                    f"✓ Pole mpd_description zostało wypełnione (długość: {len(actual_value)})")
                print(
                    f"[DEBUG] ✓ Pole mpd_description zostało wypełnione (długość: {len(actual_value)})")

            # Dodatkowe sprawdzenie - upewnij się, że wartość jest w DOM
            final_check = self.driver.execute_script(
                "return document.getElementById('mpd_description').value;")
            if not final_check or len(final_check) < len(enhanced_description) * 0.8:
                logger.warning(
                    f"⚠ Wartość nie jest w DOM. Długość: {len(final_check) if final_check else 0}")
                print(
                    f"[DEBUG] ⚠ Wartość nie jest w DOM. Długość: {len(final_check) if final_check else 0}")
            else:
                logger.info("✓ Wartość potwierdzona w DOM")
                print("[DEBUG] ✓ Wartość potwierdzona w DOM")

            time.sleep(0.5)  # Daj więcej czasu na przetworzenie

            # Zwróć ulepszony opis, aby można było użyć go do krótkiego opisu
            return enhanced_description

        except Exception as e:
            logger.error(f"Błąd podczas wypełniania pola mpd_description: {e}")
            print(
                f"[DEBUG] Błąd podczas wypełniania pola mpd_description: {e}")
            import traceback
            traceback.print_exc()
            # Zwróć None w przypadku błędu
            return None

    def update_product_description(self, ai_processor=None):
        """
        DEPRECATED: Użyj fill_mpd_description() zamiast tej metody.
        Wrapper dla kompatybilności wstecznej.
        """
        try:
            logger.warning(
                "update_product_description() jest deprecated. Uzyj fill_mpd_description()")
            print(
                "[WARNING] update_product_description() jest deprecated. Uzyj fill_mpd_description()")
        except UnicodeEncodeError:
            logger.warning(
                "update_product_description() is deprecated. Use fill_mpd_description()")
        return self.fill_mpd_description(ai_processor=ai_processor)

    def fill_mpd_short_description(self, ai_processor=None):
        """
        SCENARIUSZ CREATE, KROK 3: Wypełnia pole mpd_short_description w sekcji MPD.

        Pobiera pełny opis z pola mpd_description (które powinno być już wypełnione przez KROK 2),
        tworzy krótki opis przez AI i ustawia w polu mpd_short_description.

        Args:
            ai_processor: Instancja AIProcessor do tworzenia krótkiego opisu. Jeśli None, tworzy nową.

        Returns:
            str: Utworzony krótki opis produktu lub None w przypadku błędu
        """
        try:
            logger.info("=" * 50)
            logger.info(
                "SCENARIUSZ CREATE, KROK 3: Wypełnianie pola mpd_short_description")
            logger.info("=" * 50)
            print("[DEBUG] " + "=" * 50)
            print(
                "[DEBUG] SCENARIUSZ CREATE, KROK 3: Wypełnianie pola mpd_short_description")
            print("[DEBUG] " + "=" * 50)

            # KROK 0: Upewnij się, że sekcja right-column jest rozwinięta
            self._ensure_right_column_expanded()
            time.sleep(0.5)

            # KROK 3.1: Znajdź pole mpd_short_description w sekcji MPD
            try:
                mpd_short_desc_field = self.wait.until(
                    EC.presence_of_element_located(
                        (By.ID, "mpd_short_description"))
                )
            except Exception as e:
                logger.error(
                    f"Nie udało się znaleźć pola mpd_short_description: {e}")
                print(
                    f"[DEBUG] Nie udało się znaleźć pola mpd_short_description: {e}")
                return None

            # KROK 3.2: Pobierz pełny opis z pola mpd_description (powinno być wypełnione przez KROK 2)
            full_description = None
            try:
                mpd_desc_field = self.driver.find_element(
                    By.ID, "mpd_description")
                full_description = mpd_desc_field.get_attribute("value") or ""
                logger.info(
                    f"Pobrano pełny opis z pola mpd_description (długość: {len(full_description)})")
                print(
                    f"[DEBUG] Pobrano pełny opis z pola mpd_description (długość: {len(full_description)})")
            except Exception as e:
                logger.warning(
                    f"Nie udało się pobrać opisu z pola mpd_description: {e}")
                print(
                    f"[DEBUG] Nie udało się pobrać opisu z pola mpd_description: {e}")

            # KROK 3.3: Jeśli pole mpd_description jest puste, pobierz opis z formularza Django
            if not full_description or not full_description.strip():
                try:
                    django_desc_field = self.wait.until(
                        EC.presence_of_element_located(
                            (By.ID, "id_description"))
                    )
                    full_description = django_desc_field.get_attribute(
                        "value") or ""
                    logger.info(
                        f"Pobrano pełny opis z formularza Django (długość: {len(full_description)})")
                    print(
                        f"[DEBUG] Pobrano pełny opis z formularza Django (długość: {len(full_description)})")
                except Exception as e:
                    logger.warning(
                        f"Nie udało się pobrać opisu z formularza Django: {e}")
                    print(
                        f"[DEBUG] Nie udało się pobrać opisu z formularza Django: {e}")

            if not full_description or not full_description.strip():
                logger.warning("Brak pełnego opisu do skrócenia")
                print("[DEBUG] Brak pełnego opisu do skrócenia")
                return None

            # KROK 3.4: Utwórz krótki opis przez AI
            if ai_processor is None:
                from web_agent.automation.ai_processor import AIProcessor
                ai_processor = AIProcessor()

            logger.info("Tworzenie krótkiego opisu przez AI...")
            print("[DEBUG] Tworzenie krótkiego opisu przez AI...")
            short_description = ai_processor.create_short_description(
                full_description, max_length=250)

            if not short_description:
                logger.warning("Nie udało się utworzyć krótkiego opisu")
                print("[DEBUG] Nie udało się utworzyć krótkiego opisu")
                return None

            logger.info(
                f"Utworzony krótki opis produktu (długość: {len(short_description)})")
            print(
                f"[DEBUG] Utworzony krótki opis produktu (długość: {len(short_description)})")

            # KROK 3.5: Ustaw wartość w polu mpd_short_description przez JavaScript
            # Najpierw focus na pole
            self.driver.execute_script(
                "arguments[0].focus();", mpd_short_desc_field)
            time.sleep(0.2)

            # Wyczyść pole przez JavaScript
            self.driver.execute_script(
                "arguments[0].value = '';", mpd_short_desc_field)
            time.sleep(0.2)

            # Ustaw wartość przez JavaScript
            self.driver.execute_script(
                "arguments[0].value = arguments[1];",
                mpd_short_desc_field,
                short_description
            )
            time.sleep(0.3)

            # Wywołaj zdarzenia, aby React zarejestrował zmianę
            self.driver.execute_script(
                """
                var field = arguments[0];
                field.dispatchEvent(new Event('input', { bubbles: true }));
                field.dispatchEvent(new Event('change', { bubbles: true }));
                field.dispatchEvent(new Event('blur', { bubbles: true }));
                """,
                mpd_short_desc_field
            )
            time.sleep(0.5)

            # KROK 3.6: Weryfikacja - sprawdź czy wartość została ustawiona
            actual_value = self.driver.execute_script(
                "return arguments[0].value;", mpd_short_desc_field)

            if actual_value == short_description:
                logger.info(
                    f"✓ Pole mpd_short_description zostało wypełnione (długość: {len(actual_value)})")
                print(
                    f"[DEBUG] ✓ Pole mpd_short_description zostało wypełnione (długość: {len(actual_value)})")
                return short_description
            else:
                logger.warning(
                    f"⚠ Wartość mpd_short_description nie została poprawnie ustawiona. "
                    f"Oczekiwano: {len(short_description)} znaków, otrzymano: {len(actual_value) if actual_value else 0} znaków")
                print(
                    f"[DEBUG] ⚠ Wartość mpd_short_description nie została poprawnie ustawiona. "
                    f"Oczekiwano: {len(short_description)} znaków, otrzymano: {len(actual_value) if actual_value else 0} znaków")
                # Fallback: spróbuj przez send_keys
                try:
                    mpd_short_desc_field.clear()
                    time.sleep(0.2)
                    mpd_short_desc_field.send_keys(short_description)
                    time.sleep(0.3)
                    # Ponownie wywołaj zdarzenia
                    self.driver.execute_script(
                        """
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                        """,
                        mpd_short_desc_field
                    )
                    # Sprawdź ponownie
                    actual_value = self.driver.execute_script(
                        "return arguments[0].value;", mpd_short_desc_field)
                    if actual_value == short_description:
                        logger.info(
                            f"✓ Pole mpd_short_description wypełnione przez send_keys (długość: {len(actual_value)})")
                        print(
                            f"[DEBUG] ✓ Pole mpd_short_description wypełnione przez send_keys (długość: {len(actual_value)})")
                        return short_description
                    else:
                        logger.error(
                            f"Nie udało się ustawić wartości w polu mpd_short_description")
                        print(
                            f"[DEBUG] Nie udało się ustawić wartości w polu mpd_short_description")
                        return None
                except Exception as e_fallback:
                    logger.error(
                        f"Nie udało się wypełnić mpd_short_description przez send_keys: {e_fallback}")
                    print(
                        f"[DEBUG] Nie udało się wypełnić mpd_short_description przez send_keys: {e_fallback}")
                    return None

        except Exception as e:
            logger.error(
                f"Błąd podczas wypełniania pola mpd_short_description: {e}")
            print(
                f"[DEBUG] Błąd podczas wypełniania pola mpd_short_description: {e}")
            import traceback
            traceback.print_exc()
            return None

    def update_product_short_description(self, full_description: str, ai_processor=None):
        """
        DEPRECATED: Użyj fill_mpd_short_description() zamiast tej metody.
        Wrapper dla kompatybilności wstecznej.

        Args:
            full_description: Pełny opis produktu (ignorowany - metoda pobierze go automatycznie)
            ai_processor: Instancja AIProcessor do tworzenia krótkiego opisu. Jeśli None, tworzy nową.
        """
        try:
            logger.warning(
                "update_product_short_description() jest deprecated. Uzyj fill_mpd_short_description()")
            print(
                "[WARNING] update_product_short_description() jest deprecated. Uzyj fill_mpd_short_description()")
        except UnicodeEncodeError:
            logger.warning(
                "update_product_short_description() is deprecated. Use fill_mpd_short_description()")
        return self.fill_mpd_short_description(ai_processor=ai_processor)

    def check_if_product_is_mapped(self) -> bool:
        """
        Sprawdza czy produkt jest zmapowany do MPD.

        Returns:
            True jeśli produkt jest zmapowany, False jeśli nie
        """
        try:
            # Sprawdź czy istnieje przycisk "Utwórz nowy produkt w MPD"
            # Jeśli przycisk istnieje, produkt NIE jest zmapowany
            create_mpd_button = self.driver.find_element(
                By.ID, "create-mpd-product-btn"
            )
            logger.info(
                "Produkt nie jest zmapowany (znaleziono przycisk create-mpd-product-btn)")
            print(
                "[DEBUG] Produkt nie jest zmapowany (znaleziono przycisk create-mpd-product-btn)")
            return False
        except NoSuchElementException:
            logger.info(
                "Produkt jest już zmapowany do MPD (brak przycisku create-mpd-product-btn)")
            print(
                "[DEBUG] Produkt jest już zmapowany do MPD (brak przycisku create-mpd-product-btn)")
            return True

    def _ensure_right_column_expanded(self):
        """
        KROK 0: Upewnia się, że sekcja right-column (MPD) jest rozwinięta.
        """
        try:
            right_column = self.driver.find_element(
                By.CSS_SELECTOR, ".right-column")
            if "collapsed" in right_column.get_attribute("class"):
                toggle_button = self.driver.find_element(
                    By.CSS_SELECTOR, ".toggle-button")
                toggle_button.click()
                time.sleep(0.5)
                logger.info("Rozwinięto sekcję right-column")
                print("[DEBUG] Rozwinięto sekcję right-column")
                return True
            return False
        except Exception as e:
            logger.warning(f"Nie udało się rozwijać sekcji right-column: {e}")
            print(f"[DEBUG] Nie udało się rozwijać sekcji right-column: {e}")
            return False

    def fill_mpd_name(self, ai_processor=None):
        """
        SCENARIUSZ CREATE, KROK 1: Wypełnia pole mpd_name w sekcji MPD.

        Pobiera nazwę produktu z głównego formularza Django (id_name),
        ulepsza ją przez AI (jeśli potrzeba) i ustawia w polu mpd_name.

        Args:
            ai_processor: Instancja AIProcessor do ulepszania nazwy. Jeśli None, tworzy nową.

        Returns:
            str: Wypełniona nazwa produktu lub None w przypadku błędu
        """
        try:
            logger.info("=" * 50)
            logger.info("SCENARIUSZ CREATE, KROK 1: Wypełnianie pola mpd_name")
            logger.info("=" * 50)
            print("[DEBUG] " + "=" * 50)
            print("[DEBUG] SCENARIUSZ CREATE, KROK 1: Wypełnianie pola mpd_name")
            print("[DEBUG] " + "=" * 50)

            # KROK 0: Upewnij się, że sekcja right-column jest rozwinięta
            self._ensure_right_column_expanded()
            time.sleep(0.5)

            # KROK 1.1: Pobierz nazwę produktu z głównego formularza Django (id_name)
            try:
                django_name_field = self.wait.until(
                    EC.presence_of_element_located((By.ID, "id_name"))
                )
                original_name = django_name_field.get_attribute("value") or ""
                logger.info(
                    f"Pobrano nazwę z formularza Django: {original_name}")
                print(
                    f"[DEBUG] Pobrano nazwę z formularza Django: {original_name}")
            except Exception as e:
                logger.error(
                    f"Nie udało się pobrać nazwy z formularza Django: {e}")
                print(
                    f"[DEBUG] Nie udało się pobrać nazwy z formularza Django: {e}")
                return None

            if not original_name or not original_name.strip():
                logger.warning("Brak nazwy produktu w formularzu Django")
                print("[DEBUG] Brak nazwy produktu w formularzu Django")
                return None

            # KROK 1.2: Ulepsz nazwę przez AI (jeśli potrzeba)
            if ai_processor is None:
                from web_agent.automation.ai_processor import AIProcessor
                ai_processor = AIProcessor()

            logger.info("Ulepszanie nazwy przez AI...")
            print("[DEBUG] Ulepszanie nazwy przez AI...")
            enhanced_name = ai_processor.enhance_product_name(
                original_name, use_structured=True)

            if not enhanced_name:
                logger.warning(
                    "AI nie zwróciło ulepszonej nazwy, używam oryginalnej")
                print("[DEBUG] AI nie zwróciło ulepszonej nazwy, używam oryginalnej")
                enhanced_name = original_name

            logger.info(f"Ulepszona nazwa: {enhanced_name}")
            print(f"[DEBUG] Ulepszona nazwa: {enhanced_name}")

            # KROK 1.3: Znajdź pole mpd_name w sekcji MPD
            try:
                mpd_name_field = self.wait.until(
                    EC.presence_of_element_located((By.ID, "mpd_name"))
                )
            except Exception as e:
                logger.error(f"Nie udało się znaleźć pola mpd_name: {e}")
                print(f"[DEBUG] Nie udało się znaleźć pola mpd_name: {e}")
                return None

            # KROK 1.4: Ustaw wartość w polu mpd_name przez JavaScript
            # Używamy JavaScript, aby React widział zmianę
            self.driver.execute_script(
                """
                var field = arguments[0];
                var value = arguments[1];
                field.value = value;
                // Wywołaj zdarzenia, aby React zarejestrował zmianę
                field.dispatchEvent(new Event('input', { bubbles: true }));
                field.dispatchEvent(new Event('change', { bubbles: true }));
                field.dispatchEvent(new Event('blur', { bubbles: true }));
                """,
                mpd_name_field,
                enhanced_name
            )
            time.sleep(0.5)  # Daj czas na przetworzenie przez React

            # KROK 1.5: Weryfikacja - sprawdź czy wartość została ustawiona
            actual_value = self.driver.execute_script(
                "return arguments[0].value;", mpd_name_field)

            if actual_value == enhanced_name:
                logger.info(
                    f"✓ Pole mpd_name zostało wypełnione: {enhanced_name}")
                print(
                    f"[DEBUG] ✓ Pole mpd_name zostało wypełnione: {enhanced_name}")
                return enhanced_name
            else:
                logger.warning(
                    f"⚠ Wartość mpd_name nie została poprawnie ustawiona. "
                    f"Oczekiwano: '{enhanced_name}', otrzymano: '{actual_value}'"
                )
                print(
                    f"[DEBUG] ⚠ Wartość mpd_name nie została poprawnie ustawiona. "
                    f"Oczekiwano: '{enhanced_name}', otrzymano: '{actual_value}'"
                )
                # Fallback: spróbuj przez send_keys
                try:
                    mpd_name_field.clear()
                    mpd_name_field.send_keys(enhanced_name)
                    time.sleep(0.5)
                    # Ponownie wywołaj zdarzenia
                    self.driver.execute_script(
                        """
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                        """,
                        mpd_name_field
                    )
                    logger.info(
                        f"✓ Pole mpd_name wypełnione przez send_keys: {enhanced_name}")
                    print(
                        f"[DEBUG] ✓ Pole mpd_name wypełnione przez send_keys: {enhanced_name}")
                    return enhanced_name
                except Exception as e_fallback:
                    logger.error(
                        f"Nie udało się wypełnić mpd_name przez send_keys: {e_fallback}")
                    print(
                        f"[DEBUG] Nie udało się wypełnić mpd_name przez send_keys: {e_fallback}")
                    return None

        except Exception as e:
            logger.error(f"Błąd podczas wypełniania pola mpd_name: {e}")
            print(f"[DEBUG] Błąd podczas wypełniania pola mpd_name: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fill_mpd_brand(self):
        """
        SCENARIUSZ CREATE, KROK 5: Wypełnia markę w polu mpd_brand w sekcji MPD.

        Pobiera markę z formularza produktu Django (id_brand), normalizuje ją
        (usuwa część w nawiasach) i ustawia w polu mpd_brand przez JavaScript.

        Returns:
            str: Nazwa ustawionej marki lub None w przypadku błędu
        """
        try:
            logger.info("=" * 50)
            logger.info(
                "SCENARIUSZ CREATE, KROK 5: Wypełnianie marki w mpd_brand")
            logger.info("=" * 50)
            print("[DEBUG] " + "=" * 50)
            print("[DEBUG] SCENARIUSZ CREATE, KROK 5: Wypełnianie marki w mpd_brand")
            print("[DEBUG] " + "=" * 50)

            # KROK 0: Upewnij się, że sekcja right-column jest rozwinięta
            self._ensure_right_column_expanded()
            time.sleep(0.5)

            # KROK 5.1: Pobierz markę z formularza produktu (Django admin używa id="id_brand")
            brand_name = None
            try:
                from selenium.webdriver.support.ui import Select

                brand_select = self.driver.find_element(By.ID, "id_brand")
                select = Select(brand_select)
                selected_option = select.first_selected_option
                if selected_option and selected_option.get_attribute("value"):
                    brand_name_full = selected_option.text.strip()
                    # Usuń część w nawiasach (np. "Marko (174)" -> "Marko")
                    if '(' in brand_name_full:
                        brand_name = brand_name_full.split('(')[0].strip()
                    else:
                        brand_name = brand_name_full
                    logger.info(
                        f"Pobrano markę z formularza Django: {brand_name_full} -> {brand_name}")
                    print(
                        f"[DEBUG] Pobrano markę z formularza Django: {brand_name_full} -> {brand_name}")
                else:
                    logger.warning(
                        "Brak zaznaczonej marki w formularzu Django")
                    print("[DEBUG] Brak zaznaczonej marki w formularzu Django")
            except Exception as e:
                logger.warning(
                    f"Nie udało się pobrać marki z formularza Django: {e}")
                print(
                    f"[DEBUG] Nie udało się pobrać marki z formularza Django: {e}")
                return None

            if not brand_name:
                logger.warning("Brak nazwy marki do ustawienia")
                print("[DEBUG] Brak nazwy marki do ustawienia")
                return None

            # KROK 5.2: Znajdź pole mpd_brand w sekcji MPD
            try:
                mpd_brand_select = self.wait.until(
                    EC.presence_of_element_located(
                        (By.ID, "mpd_brand"))
                )
            except Exception as e:
                logger.error(f"Nie udało się znaleźć pola mpd_brand: {e}")
                print(f"[DEBUG] Nie udało się znaleźć pola mpd_brand: {e}")
                return None

            # KROK 5.3: Znajdź wartość opcji dla marki w selectcie mpd_brand
            from selenium.webdriver.support.ui import Select
            mpd_select = Select(mpd_brand_select)

            matched_value = None
            for opt in mpd_select.options:
                text = opt.text or ""
                if text.strip().lower() == brand_name.lower():
                    matched_value = opt.get_attribute("value")
                    break
                # Fallback: porównaj bez części w nawiasach
                base = text.split('(')[0].strip().lower()
                if base == brand_name.lower():
                    matched_value = opt.get_attribute("value")
                    break

            if not matched_value:
                logger.warning(
                    f"Nie znaleziono opcji dla marki '{brand_name}' w selectcie mpd_brand")
                print(
                    f"[DEBUG] Nie znaleziono opcji dla marki '{brand_name}' w selectcie mpd_brand")
                return None

            # KROK 5.4: Wybierz markę w dropdown mpd_brand przez Select
            logger.info(
                f"Próbuję wybrać markę '{brand_name}' (value: '{matched_value}')...")
            print(
                f"[DEBUG] Próbuję wybrać markę '{brand_name}' (value: '{matched_value}')...")

            try:
                # Metoda 1: select_by_value
                mpd_select.select_by_value(matched_value)
                time.sleep(0.5)  # Daj czas na przetworzenie
                logger.info(
                    f"Wybrano markę przez Select.select_by_value: {brand_name} (value: {matched_value})")
                print(
                    f"[DEBUG] Wybrano markę przez Select.select_by_value: {brand_name} (value: {matched_value})")
            except Exception as e_select_value:
                logger.warning(
                    f"Nie udało się wybrać przez select_by_value: {e_select_value}, próbuję select_by_visible_text")
                print(
                    f"[DEBUG] Nie udało się wybrać przez select_by_value: {e_select_value}, próbuję select_by_visible_text")
                try:
                    # Metoda 2: select_by_visible_text (fallback)
                    mpd_select.select_by_visible_text(brand_name)
                    time.sleep(0.5)
                    logger.info(
                        f"Wybrano markę przez Select.select_by_visible_text: {brand_name}")
                    print(
                        f"[DEBUG] Wybrano markę przez Select.select_by_visible_text: {brand_name}")
                except Exception as e_select_text:
                    logger.warning(
                        f"Nie udało się wybrać przez select_by_visible_text: {e_select_text}, próbuję przez JavaScript")
                    print(
                        f"[DEBUG] Nie udało się wybrać przez select_by_visible_text: {e_select_text}, próbuję przez JavaScript")
                    # Metoda 3: JavaScript (fallback)
                    self.driver.execute_script(
                        """
                        var select = arguments[0];
                        var value = arguments[1];
                        select.value = value;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));
                        """,
                        mpd_brand_select,
                        matched_value
                    )
                    time.sleep(0.5)
                    logger.info(
                        f"Ustawiono markę przez JavaScript: {brand_name} (value: {matched_value})")
                    print(
                        f"[DEBUG] Ustawiono markę przez JavaScript: {brand_name} (value: {matched_value})")

            # KROK 5.5: Weryfikacja - sprawdź czy wartość została ustawiona
            # Sprawdź przez Select.all_selected_options
            try:
                selected_options = mpd_select.all_selected_options
                if selected_options and len(selected_options) > 0:
                    selected_text = selected_options[0].text.strip()
                    selected_value = selected_options[0].get_attribute("value")
                    if selected_value == matched_value:
                        logger.info(
                            f"✓ Marka została wybrana w mpd_brand: {selected_text} (value: {matched_value})")
                        print(
                            f"[DEBUG] ✓ Marka została wybrana w mpd_brand: {selected_text} (value: {matched_value})")
                        return brand_name
                    else:
                        logger.warning(
                            f"⚠ Wybrana wartość nie pasuje. Oczekiwano: '{matched_value}', otrzymano: '{selected_value}'")
                        print(
                            f"[DEBUG] ⚠ Wybrana wartość nie pasuje. Oczekiwano: '{matched_value}', otrzymano: '{selected_value}'")
                        return None
                else:
                    logger.warning(
                        "Brak zaznaczonej opcji w selectcie mpd_brand")
                    print("[DEBUG] Brak zaznaczonej opcji w selectcie mpd_brand")
                    return None
            except Exception as e_verify:
                logger.warning(
                    f"Nie udało się zweryfikować wyboru marki: {e_verify}")
                print(
                    f"[DEBUG] Nie udało się zweryfikować wyboru marki: {e_verify}")
                # Fallback: sprawdź przez get_attribute
                actual_value = mpd_brand_select.get_attribute("value")
                if actual_value == matched_value:
                    logger.info(
                        f"✓ Marka została ustawiona w mpd_brand (weryfikacja przez get_attribute): {brand_name}")
                    print(
                        f"[DEBUG] ✓ Marka została ustawiona w mpd_brand (weryfikacja przez get_attribute): {brand_name}")
                    return brand_name
                else:
                    logger.warning(
                        f"⚠ Marka nie została poprawnie ustawiona. Oczekiwano: '{matched_value}', otrzymano: '{actual_value}'")
                    print(
                        f"[DEBUG] ⚠ Marka nie została poprawnie ustawiona. Oczekiwano: '{matched_value}', otrzymano: '{actual_value}'")
                    return None

        except Exception as e:
            logger.error(f"Błąd podczas wypełniania marki w mpd_brand: {e}")
            print(f"[DEBUG] Błąd podczas wypełniania marki w mpd_brand: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fill_main_color_from_product_color(self):
        """
        KROK 7: Wypełnia główny kolor (main_color_id) na podstawie wartości z pola id_color.
        
        Pobiera wartość koloru z pola <input type="text" name="color" id="id_color">
        i znajduje odpowiednią opcję w dropdownie main_color_id, a następnie ją zaznacza.
        
        Returns:
            str: Nazwa ustawionego koloru lub None w przypadku błędu
        """
        try:
            logger.info("=" * 50)
            logger.info("KROK 7: Wypełnianie głównego koloru (main_color_id)")
            logger.info("=" * 50)
            print("[DEBUG] " + "=" * 50)
            print("[DEBUG] KROK 7: Wypełnianie głównego koloru (main_color_id)")
            print("[DEBUG] " + "=" * 50)
            
            # KROK 0: Upewnij się, że sekcja right-column jest rozwinięta
            self._ensure_right_column_expanded()
            time.sleep(0.5)
            
            # KROK 7.1: Pobierz wartość koloru z pola id_color
            color_name = None
            try:
                color_input = self.driver.find_element(By.ID, "id_color")
                color_name = color_input.get_attribute("value")
                if color_name:
                    color_name = color_name.strip()
                    logger.info(f"Pobrano kolor z pola id_color: {color_name}")
                    print(f"[DEBUG] Pobrano kolor z pola id_color: {color_name}")
                else:
                    logger.warning("Brak wartości koloru w polu id_color")
                    print("[DEBUG] Brak wartości koloru w polu id_color")
            except Exception as e:
                logger.warning(f"Nie udało się pobrać koloru z pola id_color: {e}")
                print(f"[DEBUG] Nie udało się pobrać koloru z pola id_color: {e}")
                return None
            
            if not color_name:
                logger.warning("Brak nazwy koloru do ustawienia")
                print("[DEBUG] Brak nazwy koloru do ustawienia")
                return None
            
            # KROK 7.2: Znajdź pole main_color_id w sekcji MPD
            try:
                main_color_select = self.wait.until(
                    EC.presence_of_element_located(
                        (By.ID, "main_color_id"))
                )
            except Exception as e:
                logger.error(f"Nie udało się znaleźć pola main_color_id: {e}")
                print(f"[DEBUG] Nie udało się znaleźć pola main_color_id: {e}")
                return None
            
            # KROK 7.3: Znajdź wartość opcji dla koloru w selectcie main_color_id
            from selenium.webdriver.support.ui import Select
            color_select = Select(main_color_select)
            
            matched_value = None
            matched_text = None
            for opt in color_select.options:
                text = opt.text or ""
                opt_value = opt.get_attribute("value")
                
                # Pomiń opcję pustą
                if not opt_value:
                    continue
                
                # Porównaj nazwę koloru (case-insensitive)
                if text.strip().lower() == color_name.lower():
                    matched_value = opt_value
                    matched_text = text.strip()
                    break
                # Fallback: porównaj bez części w nawiasach
                base = text.split('(')[0].strip().lower()
                if base == color_name.lower():
                    matched_value = opt_value
                    matched_text = text.strip()
                    break
            
            if not matched_value:
                logger.warning(
                    f"Nie znaleziono opcji dla koloru '{color_name}' w selectcie main_color_id")
                print(
                    f"[DEBUG] Nie znaleziono opcji dla koloru '{color_name}' w selectcie main_color_id")
                return None
            
            # KROK 7.4: Wybierz kolor w dropdown main_color_id przez Select
            logger.info(
                f"Próbuję wybrać kolor '{color_name}' (value: '{matched_value}', text: '{matched_text}')...")
            print(
                f"[DEBUG] Próbuję wybrać kolor '{color_name}' (value: '{matched_value}', text: '{matched_text}')...")
            
            try:
                # Metoda 1: select_by_value
                color_select.select_by_value(matched_value)
                time.sleep(0.5)  # Daj czas na przetworzenie
                logger.info(
                    f"Wybrano kolor przez Select.select_by_value: {matched_text} (value: {matched_value})")
                print(
                    f"[DEBUG] Wybrano kolor przez Select.select_by_value: {matched_text} (value: {matched_value})")
            except Exception as e_select_value:
                logger.warning(
                    f"Nie udało się wybrać przez select_by_value: {e_select_value}, próbuję select_by_visible_text")
                print(
                    f"[DEBUG] Nie udało się wybrać przez select_by_value: {e_select_value}, próbuję select_by_visible_text")
                try:
                    # Metoda 2: select_by_visible_text (fallback)
                    color_select.select_by_visible_text(matched_text)
                    time.sleep(0.5)
                    logger.info(
                        f"Wybrano kolor przez Select.select_by_visible_text: {matched_text}")
                    print(
                        f"[DEBUG] Wybrano kolor przez Select.select_by_visible_text: {matched_text}")
                except Exception as e_select_text:
                    logger.warning(
                        f"Nie udało się wybrać przez select_by_visible_text: {e_select_text}, próbuję przez JavaScript")
                    print(
                        f"[DEBUG] Nie udało się wybrać przez select_by_visible_text: {e_select_text}, próbuję przez JavaScript")
                    # Metoda 3: JavaScript (fallback)
                    self.driver.execute_script(
                        """
                        var select = arguments[0];
                        var value = arguments[1];
                        select.value = value;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));
                        """,
                        main_color_select,
                        matched_value
                    )
                    time.sleep(0.5)
                    logger.info(
                        f"Ustawiono kolor przez JavaScript: {matched_text} (value: {matched_value})")
                    print(
                        f"[DEBUG] Ustawiono kolor przez JavaScript: {matched_text} (value: {matched_value})")
            
            # KROK 7.5: Weryfikacja - sprawdź czy wartość została ustawiona
            try:
                selected_options = color_select.all_selected_options
                if selected_options and len(selected_options) > 0:
                    selected_text = selected_options[0].text.strip()
                    selected_value = selected_options[0].get_attribute("value")
                    if selected_value == matched_value:
                        logger.info(
                            f"✓ Kolor został wybrany w main_color_id: {selected_text} (value: {matched_value})")
                        print(
                            f"[DEBUG] ✓ Kolor został wybrany w main_color_id: {selected_text} (value: {matched_value})")
                        return matched_text
                    else:
                        logger.warning(
                            f"⚠ Wybrana wartość nie pasuje. Oczekiwano: '{matched_value}', otrzymano: '{selected_value}'")
                        print(
                            f"[DEBUG] ⚠ Wybrana wartość nie pasuje. Oczekiwano: '{matched_value}', otrzymano: '{selected_value}'")
                        return None
                else:
                    logger.warning(
                        "Brak zaznaczonej opcji w selectcie main_color_id")
                    print("[DEBUG] Brak zaznaczonej opcji w selectcie main_color_id")
                    return None
            except Exception as e_verify:
                logger.warning(
                    f"Nie udało się zweryfikować wyboru koloru: {e_verify}")
                print(
                    f"[DEBUG] Nie udało się zweryfikować wyboru koloru: {e_verify}")
                # Fallback: sprawdź przez get_attribute
                actual_value = main_color_select.get_attribute("value")
                if actual_value == matched_value:
                    logger.info(
                        f"✓ Kolor został ustawiony w main_color_id (weryfikacja przez get_attribute): {matched_text}")
                    print(
                        f"[DEBUG] ✓ Kolor został ustawiony w main_color_id (weryfikacja przez get_attribute): {matched_text}")
                    return matched_text
                else:
                    logger.warning(
                        f"⚠ Kolor nie został poprawnie ustawiony. Oczekiwano: '{matched_value}', otrzymano: '{actual_value}'")
                    print(
                        f"[DEBUG] ⚠ Kolor nie został poprawnie ustawiony. Oczekiwano: '{matched_value}', otrzymano: '{actual_value}'")
                    return None
        
        except Exception as e:
            logger.error(f"Błąd podczas wypełniania głównego koloru w main_color_id: {e}")
            print(f"[DEBUG] Błąd podczas wypełniania głównego koloru w main_color_id: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fill_series_name_placeholder(self):
        """
        KROK 8: Ustawia placeholder w polu series_name (nie wypełnia faktycznej wartości).
        
        Pole series_name pozostaje puste lub z placeholderem - nie wypełniamy go faktycznie.
        
        Returns:
            bool: True jeśli operacja się powiodła, False w przypadku błędu
        """
        try:
            logger.info("=" * 50)
            logger.info("KROK 8: Ustawianie placeholder w polu series_name")
            logger.info("=" * 50)
            print("[DEBUG] " + "=" * 50)
            print("[DEBUG] KROK 8: Ustawianie placeholder w polu series_name")
            print("[DEBUG] " + "=" * 50)
            
            # KROK 0: Upewnij się, że sekcja right-column jest rozwinięta
            self._ensure_right_column_expanded()
            time.sleep(0.5)
            
            # KROK 8.1: Znajdź pole series_name
            try:
                series_field = self.wait.until(
                    EC.presence_of_element_located(
                        (By.ID, "series_name"))
                )
            except Exception as e:
                logger.warning(f"Nie udało się znaleźć pola series_name: {e}")
                print(f"[DEBUG] Nie udało się znaleźć pola series_name: {e}")
                return False
            
            # KROK 8.2: Wyczyść pole i ustaw placeholder (pole pozostaje puste)
            try:
                series_field.clear()
                # Pole pozostaje puste - to jest placeholder
                logger.info("✓ Pole series_name zostało wyczyszczone (placeholder)")
                print("[DEBUG] ✓ Pole series_name zostało wyczyszczone (placeholder)")
                time.sleep(0.3)
                return True
            except Exception as e:
                logger.warning(f"Nie udało się wyczyścić pola series_name: {e}")
                print(f"[DEBUG] Nie udało się wyczyścić pola series_name: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Błąd podczas ustawiania placeholder w polu series_name: {e}")
            print(f"[DEBUG] Błąd podczas ustawiania placeholder w polu series_name: {e}")
            import traceback
            traceback.print_exc()
            return False

    def create_mpd_product(self, ai_processor=None):
        """
        Wykonuje SCENARIUSZ CREATE - wypełnia pola produktu w MPD.

        Wykonuje TYLKO kroki 1-5 w następującej kolejności:
        1. Wypełnia pole mpd_name (SCENARIUSZ CREATE, KROK 1)
        2. Wypełnia pole mpd_description (SCENARIUSZ CREATE, KROK 2)
        3. Wypełnia pole mpd_short_description (SCENARIUSZ CREATE, KROK 3)
        4. Wypełnia atrybuty w mpd_attributes (SCENARIUSZ CREATE, KROK 4)
        5. Wypełnia markę w mpd_brand (SCENARIUSZ CREATE, KROK 5)

        UWAGA: Metoda kończy się po wykonaniu kroków 1-5.
        Dodatkowe operacje (ustawienie koloru producenta, kliknięcie przycisku)
        są zakomentowane poniżej i nie są wykonywane.

        Args:
            ai_processor: Instancja AIProcessor do ulepszania nazwy. Jeśli None, tworzy nową.
        """
        try:
            logger.info("Tworzenie produktu w MPD...")
            print("[DEBUG] Tworzenie produktu w MPD...")

            # Poczekaj chwilę, aby upewnić się, że formularz jest gotowy
            time.sleep(1)

            # ============================================================
            # PRZYGOTOWANIE: Upewnij się, że sekcja right-column jest rozwinięta
            # ============================================================
            self._ensure_right_column_expanded()

            # ============================================================
            # SCENARIUSZ CREATE - KROKI 1-5 (WYKONYWANE PO KOLEI)
            # ============================================================

            # KROK 1: Wypełnij pole mpd_name
            logger.info("=" * 60)
            logger.info("KROK 1: Wypełnianie pola mpd_name")
            logger.info("=" * 60)
            filled_name = self.fill_mpd_name(ai_processor=ai_processor)
            if not filled_name:
                logger.warning(
                    "Nie udało się wypełnić pola mpd_name, kontynuuję dalej...")
                print(
                    "[DEBUG] Nie udało się wypełnić pola mpd_name, kontynuuję dalej...")

            # KROK 2: Wypełnij pole mpd_description
            logger.info("=" * 60)
            logger.info("KROK 2: Wypełnianie pola mpd_description")
            logger.info("=" * 60)
            filled_description = self.fill_mpd_description(
                ai_processor=ai_processor)
            if not filled_description:
                logger.warning(
                    "Nie udało się wypełnić pola mpd_description, kontynuuję dalej...")
                print(
                    "[DEBUG] Nie udało się wypełnić pola mpd_description, kontynuuję dalej...")

            # KROK 3: Wypełnij pole mpd_short_description
            logger.info("=" * 60)
            logger.info("KROK 3: Wypełnianie pola mpd_short_description")
            logger.info("=" * 60)
            filled_short_description = self.fill_mpd_short_description(
                ai_processor=ai_processor)
            if not filled_short_description:
                logger.warning(
                    "Nie udało się wypełnić pola mpd_short_description, kontynuuję dalej...")
                print(
                    "[DEBUG] Nie udało się wypełnić pola mpd_short_description, kontynuuję dalej...")

            # KROK 4: Wypełnij atrybuty w mpd_attributes
            logger.info("=" * 60)
            logger.info("KROK 4: Wypełnianie atrybutów w mpd_attributes")
            logger.info("=" * 60)
            filled_attributes = self.fill_mpd_attributes(
                ai_processor=ai_processor)
            if not filled_attributes:
                logger.warning(
                    "Nie udało się wypełnić atrybutów w mpd_attributes, kontynuuję dalej...")
                print(
                    "[DEBUG] Nie udało się wypełnić atrybutów w mpd_attributes, kontynuuję dalej...")

            # Krótka pauza przed przejściem do KROKU 5, aby UI się zaktualizował
            time.sleep(0.5)

            # KROK 5: Wypełnij markę w mpd_brand
            logger.info("=" * 60)
            logger.info("KROK 5: Wypełnianie marki w mpd_brand")
            logger.info("=" * 60)
            filled_brand = self.fill_mpd_brand()
            if not filled_brand:
                logger.error(
                    "❌ BŁĄD: Nie udało się wypełnić marki w mpd_brand - PRZERWANIE WYKONANIA")
                print(
                    "[DEBUG] ❌ BŁĄD: Nie udało się wypełnić marki w mpd_brand - PRZERWANIE WYKONANIA")
                # NIE kontynuuj dalej - marka MUSI być wybrana przed kontynuacją
                return
            else:
                logger.info(
                    f"✅ KROK 5 ZAKOŃCZONY: Marka '{filled_brand}' została pomyślnie wybrana w mpd_brand")
                print(
                    f"[DEBUG] ✅ KROK 5 ZAKOŃCZONY: Marka '{filled_brand}' została pomyślnie wybrana w mpd_brand")
                # Dodatkowe opóźnienie aby upewnić się że React zarejestrował zmianę
                time.sleep(0.5)

            # ============================================================
            # KONIEC KROKÓW 1-5 - WSZYSTKIE KROKI ZAKOŃCZONE
            # Metoda kończy się tutaj - kod poniżej jest zakomentowany
            # ============================================================
            logger.info("=" * 60)
            logger.info("✅ WSZYSTKIE KROKI 1-5 ZAKOŃCZONE POMYŚLNIE")
            logger.info("=" * 60)
            print("[DEBUG] " + "=" * 60)
            print("[DEBUG] ✅ WSZYSTKIE KROKI 1-5 ZAKOŃCZONE POMYŚLNIE")
            print("[DEBUG] " + "=" * 60)
            return  # Metoda kończy się tutaj - kod poniżej jest zakomentowany i nie wykonywany

            # ============================================================
            # PONIŻEJ ZAKOMENTOWANY KOD DODATKOWY (NIE WYKONYWANY)
            # ============================================================
            # Ten kod będzie używany w przyszłości, gdy będziemy dodawać kolejne kroki.
            # Obecnie wykonują się TYLKO kroki 1-5 powyżej.
            # ============================================================

            # ZAKOMENTOWANE - KROK 6 (przyszłość): Ustaw kolor producenta w sekcji MPD
            # UWAGA: To nie jest część kroków 1-5, wykonuje się po ich zakończeniu
            # try:
            #     producer_color_field = self.driver.find_element(
            #         By.ID, "producer_color_name")
            #     producer_color_val = producer_color_field.get_attribute(
            #         "value") or ""
            #
            #     # Jeśli pole jest puste, użyj zapamiętanego koloru z update_producer_color
            #     if not producer_color_val:
            #         if hasattr(self, "_last_extracted_producer_color") and self._last_extracted_producer_color:
            #             producer_color_val = self._last_extracted_producer_color
            #             logger.info(
            #                 f"Używam zapamiętanego koloru: {producer_color_val}")
            #             print(
            #                 f"[DEBUG] Używam zapamiętanego koloru: {producer_color_val}")
            #         else:
            #             logger.warning(
            #                 "Pole producer_color_name jest puste i brak zapamiętanego koloru")
            #             print(
            #                 "[DEBUG] Pole producer_color_name jest puste i brak zapamiętanego koloru")
            #
            #     # ZAWSZE ustaw kolor przez JavaScript, aby React widział wartość (nawet jeśli już jest wypełniony)
            #     if producer_color_val:
            #         # Ustaw przez JavaScript, aby upewnić się że React widzi wartość
            #         self.driver.execute_script(
            #             """
            #             var field = arguments[0];
            #             var value = arguments[1];
            #             field.value = value;
            #             field.dispatchEvent(new Event('input', { bubbles: true }));
            #             field.dispatchEvent(new Event('change', { bubbles: true }));
            #             field.dispatchEvent(new Event('blur', { bubbles: true }));
            #             """,
            #             producer_color_field,
            #             producer_color_val
            #         )
            #         logger.info(
            #             f"Ustawiono kolor producenta w MPD przez JavaScript: {producer_color_val}")
            #         print(
            #             f"[DEBUG] Ustawiono kolor producenta w MPD przez JavaScript: {producer_color_val}")
            #         time.sleep(0.5)  # Daj więcej czasu na przetworzenie
            # except Exception as e:
            #     logger.warning(
            #         f"Nie udało się sprawdzić/ustawić koloru producenta: {e}")
            #     print(
            #         f"[DEBUG] Nie udało się sprawdzić/ustawić koloru producenta: {e}")

            # ZAKOMENTOWANE - KROK 7 (przyszłość): Kliknięcie przycisku "Utwórz nowy produkt w MPD"
            # UWAGA: To nie jest część kroków 1-5, wykonuje się po ich zakończeniu i ustawieniu koloru producenta
            # create_mpd_button = None

            # # Metoda 1: Przez ID (użyj presence_of_element_located zamiast element_to_be_clickable)
            # try:
            #     create_mpd_button = self.wait.until(
            #         EC.presence_of_element_located(
            #             (By.ID, "create-mpd-product-btn"))
            #     )
            #     logger.info("Znaleziono przycisk przez ID (presence)")
            #     print("[DEBUG] Znaleziono przycisk przez ID (presence)")
            # except:
            #     # Metoda 2: Przez XPath z ID
            #     try:
            #         create_mpd_button = self.wait.until(
            #             EC.presence_of_element_located(
            #                 (By.XPATH, "//button[@id='create-mpd-product-btn']"))
            #         )
            #         logger.info("Znaleziono przycisk przez XPath z ID")
            #         print("[DEBUG] Znaleziono przycisk przez XPath z ID")
            #     except:
            #         # Metoda 3: Przez tekst przycisku
            #         try:
            #             create_mpd_button = self.wait.until(
            #                 EC.presence_of_element_located(
            #                     (By.XPATH, "//button[contains(text(), 'Utwórz nowy produkt w MPD')]"))
            #             )
            #             logger.info("Znaleziono przycisk przez tekst")
            #             print("[DEBUG] Znaleziono przycisk przez tekst")
            #         except:
            #             # Metoda 4: Przez częściowy tekst
            #             try:
            #                 create_mpd_button = self.wait.until(
            #                     EC.presence_of_element_located(
            #                         (By.XPATH, "//button[contains(text(), 'Utwórz')]"))
            #                 )
            #                 logger.info(
            #                     "Znaleziono przycisk przez częściowy tekst")
            #                 print(
            #                     "[DEBUG] Znaleziono przycisk przez częściowy tekst")
            #             except:
            #                 raise Exception(
            #                     "Nie znaleziono przycisku 'Utwórz nowy produkt w MPD'")
            #
            # if not create_mpd_button:
            #     raise Exception("Przycisk nie został znaleziony")
            #
            # # Przewiń do przycisku
            # self.driver.execute_script(
            #     "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", create_mpd_button)
            # time.sleep(0.5)
            #
            # # Spróbuj kliknąć przycisk - najpierw standardowo, potem przez JavaScript
            # try:
            #     # Sprawdź czy przycisk jest widoczny i klikalny
            #     if create_mpd_button.is_displayed() and create_mpd_button.is_enabled():
            #         create_mpd_button.click()
            #         logger.info("Kliknięto przycisk standardowo")
            #         print("[DEBUG] Kliknięto przycisk standardowo")
            #     else:
            #         # Jeśli nie jest klikalny, użyj JavaScript
            #         self.driver.execute_script(
            #             "arguments[0].click();", create_mpd_button)
            #         logger.info("Kliknięto przycisk przez JavaScript")
            #         print("[DEBUG] Kliknięto przycisk przez JavaScript")
            # except Exception as e_click:
            #     # Fallback: użyj JavaScript do kliknięcia
            #     logger.warning(
            #         f"Błąd podczas standardowego kliknięcia: {e_click}, używam JavaScript")
            #     print(
            #         f"[DEBUG] Błąd podczas standardowego kliknięcia: {e_click}, używam JavaScript")
            #     self.driver.execute_script(
            #         "arguments[0].click();", create_mpd_button)
            #     logger.info("Kliknięto przycisk przez JavaScript (fallback)")
            #     print("[DEBUG] Kliknięto przycisk przez JavaScript (fallback)")
            # logger.info("Kliknięto przycisk 'Utwórz nowy produkt w MPD'")
            # print("[DEBUG] Kliknięto przycisk 'Utwórz nowy produkt w MPD'")
            #
            # # Poczekaj na utworzenie produktu
            # time.sleep(3)
            # logger.info("Produkt został utworzony w MPD")
            # print("[DEBUG] Produkt został utworzony w MPD")

        except Exception as e:
            logger.error(f"Błąd podczas tworzenia produktu w MPD: {e}")
            print(f"[DEBUG] Błąd podczas tworzenia produktu w MPD: {e}")
            import traceback
            traceback.print_exc()
            raise

    def save_django_form(self):
        """
        Zapisuje formularz Django (klika przycisk "Zapisz").
        """
        try:
            logger.info("Zapisywanie formularza Django...")
            print("[DEBUG] Zapisywanie formularza Django...")

            # Znajdź przycisk "Zapisz" w formularzu Django
            save_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'input[type="submit"][name="_save"]'))
            )

            # Przewiń do przycisku
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", save_button)
            time.sleep(0.5)

            # Kliknij przycisk Zapisz
            save_button.click()
            logger.info("Kliknięto przycisk 'Zapisz'")
            print("[DEBUG] Kliknięto przycisk 'Zapisz'")

            # Poczekaj na zapisanie (sprawdź czy jesteśmy na stronie z komunikatem sukcesu)
            time.sleep(2)

            # Sprawdź czy zapisanie się powiodło (URL powinien zawierać /change/ lub komunikat sukcesu)
            current_url = self.driver.current_url
            if '/change/' in current_url:
                logger.info("Zmiany zostały zapisane w formularzu Django")
                print("[DEBUG] Zmiany zostały zapisane w formularzu Django")
            else:
                logger.warning(f"Niepewny status zapisu. URL: {current_url}")
                print(f"[DEBUG] Niepewny status zapisu. URL: {current_url}")

        except Exception as e:
            logger.error(f"Błąd podczas zapisywania formularza Django: {e}")
            print(f"[DEBUG] Błąd podczas zapisywania formularza Django: {e}")
            import traceback
            traceback.print_exc()
            raise

    def check_if_product_is_mapped(self) -> bool:
        """
        Sprawdza czy produkt jest zmapowany do MPD.

        Returns:
            True jeśli produkt jest zmapowany, False jeśli nie
        """
        try:
            # Sprawdź czy istnieje przycisk "Utwórz nowy produkt w MPD"
            # Jeśli przycisk istnieje, produkt NIE jest zmapowany
            create_mpd_button = self.driver.find_element(
                By.ID, "create-mpd-product-btn"
            )
            logger.info(
                "Produkt nie jest zmapowany (znaleziono przycisk create-mpd-product-btn)")
            print(
                "[DEBUG] Produkt nie jest zmapowany (znaleziono przycisk create-mpd-product-btn)")
            return False
        except NoSuchElementException:
            logger.info(
                "Produkt jest już zmapowany do MPD (brak przycisku create-mpd-product-btn)")
            print(
                "[DEBUG] Produkt jest już zmapowany do MPD (brak przycisku create-mpd-product-btn)")
            return True

    def save_django_form(self):
        """
        Zapisuje formularz Django (klika przycisk "Zapisz").
        """
        try:
            logger.info("Zapisywanie formularza Django...")
            print("[DEBUG] Zapisywanie formularza Django...")

            # Znajdź przycisk "Zapisz" w formularzu Django
            save_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'input[type="submit"][name="_save"]'))
            )

            # Przewiń do przycisku
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", save_button)
            time.sleep(0.5)

            # Kliknij przycisk Zapisz
            save_button.click()
            logger.info("Kliknięto przycisk 'Zapisz'")
            print("[DEBUG] Kliknięto przycisk 'Zapisz'")

            # Poczekaj na zapisanie (sprawdź czy jesteśmy na stronie z komunikatem sukcesu)
            time.sleep(2)

            # Sprawdź czy zapisanie się powiodło (URL powinien zawierać /change/ lub komunikat sukcesu)
            current_url = self.driver.current_url
            if '/change/' in current_url:
                logger.info("Zmiany zostały zapisane w formularzu Django")
                print("[DEBUG] Zmiany zostały zapisane w formularzu Django")
            else:
                logger.warning(f"Niepewny status zapisu. URL: {current_url}")
                print(f"[DEBUG] Niepewny status zapisu. URL: {current_url}")

        except Exception as e:
            logger.error(f"Błąd podczas zapisywania formularza Django: {e}")
            print(f"[DEBUG] Błąd podczas zapisywania formularza Django: {e}")
            import traceback
            traceback.print_exc()
            raise

    def fill_mpd_attributes(self, ai_processor=None):
        """
        SCENARIUSZ CREATE, KROK 4: Wypełnia atrybuty w polu mpd_attributes w sekcji MPD.

        Pobiera opis z pola mpd_description (które powinno być już wypełnione przez KROK 2),
        wyciąga atrybuty z opisu przez AI i zaznacza je w polu mpd_attributes.

        Args:
            ai_processor: Instancja AIProcessor do wyciągania atrybutów. Jeśli None, tworzy nową.

        Returns:
            List[int]: Lista ID zaznaczonych atrybutów lub None w przypadku błędu
        """
        try:
            logger.info("=" * 50)
            logger.info(
                "SCENARIUSZ CREATE, KROK 4: Wypełnianie atrybutów w mpd_attributes")
            logger.info("=" * 50)
            print("[DEBUG] " + "=" * 50)
            print(
                "[DEBUG] SCENARIUSZ CREATE, KROK 4: Wypełnianie atrybutów w mpd_attributes")
            print("[DEBUG] " + "=" * 50)

            # KROK 0: Upewnij się, że sekcja right-column jest rozwinięta
            self._ensure_right_column_expanded()
            time.sleep(0.5)

            # KROK 4.1: Pobierz pełny opis z pola mpd_description (powinno być wypełnione przez KROK 2)
            full_description = None
            try:
                mpd_desc_field = self.driver.find_element(
                    By.ID, "mpd_description")
                full_description = mpd_desc_field.get_attribute("value") or ""
                logger.info(
                    f"Pobrano pełny opis z pola mpd_description (długość: {len(full_description)})")
                print(
                    f"[DEBUG] Pobrano pełny opis z pola mpd_description (długość: {len(full_description)})")
            except Exception as e:
                logger.warning(
                    f"Nie udało się pobrać opisu z pola mpd_description: {e}")
                print(
                    f"[DEBUG] Nie udało się pobrać opisu z pola mpd_description: {e}")

            # KROK 4.2: Jeśli pole mpd_description jest puste, pobierz opis z formularza Django
            if not full_description or not full_description.strip():
                try:
                    django_desc_field = self.wait.until(
                        EC.presence_of_element_located(
                            (By.ID, "id_description"))
                    )
                    full_description = django_desc_field.get_attribute(
                        "value") or ""
                    logger.info(
                        f"Pobrano pełny opis z formularza Django (długość: {len(full_description)})")
                    print(
                        f"[DEBUG] Pobrano pełny opis z formularza Django (długość: {len(full_description)})")
                except Exception as e:
                    logger.warning(
                        f"Nie udało się pobrać opisu z formularza Django: {e}")
                    print(
                        f"[DEBUG] Nie udało się pobrać opisu z formularza Django: {e}")

            if not full_description or not full_description.strip():
                logger.warning("Brak opisu do wyciągnięcia atrybutów")
                print("[DEBUG] Brak opisu do wyciągnięcia atrybutów")
                return None

            # KROK 4.3: Pobierz dostępne atrybuty z formularza
            available_attributes = self.get_available_attributes()
            if not available_attributes:
                logger.warning("Brak dostępnych atrybutów w formularzu")
                print("[DEBUG] Brak dostępnych atrybutów w formularzu")
                return None

            # KROK 4.4: Wyciągnij atrybuty z opisu przez AI
            if ai_processor is None:
                from web_agent.automation.ai_processor import AIProcessor
                ai_processor = AIProcessor()

            logger.info("Wyciąganie atrybutów z opisu przez AI...")
            print("[DEBUG] Wyciąganie atrybutów z opisu przez AI...")
            attribute_ids = ai_processor.extract_attributes_from_description(
                full_description,
                available_attributes
            )

            if not attribute_ids:
                logger.warning("Nie znaleziono atrybutów w opisie produktu")
                print("[DEBUG] Nie znaleziono atrybutów w opisie produktu")
                return None

            logger.info(
                f"Wyodrębniono {len(attribute_ids)} atrybutów: {attribute_ids}")
            print(
                f"[DEBUG] Wyodrębniono {len(attribute_ids)} atrybutów: {attribute_ids}")

            # KROK 4.5: Zaznacz atrybuty w formularzu
            self.select_attributes(attribute_ids)

            # KROK 4.6: Weryfikacja - sprawdź ile atrybutów zostało zaznaczonych
            try:
                attributes_select = self.driver.find_element(
                    By.ID, "mpd_attributes")
                selected_options = attributes_select.find_elements(
                    By.CSS_SELECTOR, "option:checked"
                )
                if len(selected_options) > 0:
                    logger.info(
                        f"✓ Zaznaczono {len(selected_options)} atrybutów w mpd_attributes")
                    print(
                        f"[DEBUG] ✓ Zaznaczono {len(selected_options)} atrybutów w mpd_attributes")
                    return attribute_ids
                else:
                    logger.warning("Nie zaznaczono żadnych atrybutów")
                    print("[DEBUG] Nie zaznaczono żadnych atrybutów")
                    return None
            except Exception as e_verify:
                logger.warning(
                    f"Nie udało się zweryfikować zaznaczonych atrybutów: {e_verify}")
                print(
                    f"[DEBUG] Nie udało się zweryfikować zaznaczonych atrybutów: {e_verify}")
                # Zwróć listę ID mimo braku weryfikacji
                return attribute_ids

        except Exception as e:
            logger.error(
                f"Błąd podczas wypełniania atrybutów w mpd_attributes: {e}")
            print(
                f"[DEBUG] Błąd podczas wypełniania atrybutów w mpd_attributes: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_available_attributes(self) -> List[Dict]:
        """
        Pobiera listę dostępnych atrybutów z formularza.

        Returns:
            Lista słowników z atrybutami [{'id': int, 'name': str}, ...]
        """
        try:
            logger.info("Pobieranie dostępnych atrybutów z formularza...")
            print("[DEBUG] Pobieranie dostępnych atrybutów z formularza...")

            # Znajdź select z atrybutami
            attributes_select = self.wait.until(
                EC.presence_of_element_located((By.ID, "mpd_attributes"))
            )

            # Pobierz wszystkie opcje
            options = attributes_select.find_elements(By.TAG_NAME, "option")

            attributes = []
            for option in options:
                attr_id = int(option.get_attribute("value"))
                attr_name = option.text.strip()
                attributes.append({'id': attr_id, 'name': attr_name})

            logger.info(f"Znaleziono {len(attributes)} dostępnych atrybutów")
            print(f"[DEBUG] Znaleziono {len(attributes)} dostępnych atrybutów")
            return attributes

        except Exception as e:
            logger.error(f"Błąd podczas pobierania atrybutów: {e}")
            print(f"[DEBUG] Błąd podczas pobierania atrybutów: {e}")
            return []

    def select_size_category(self, category_name: str = None):
        """
        Automatycznie wybiera grupę rozmiarową na podstawie kategorii produktu.
        W aktualnym workflow dla przekazanej kategorii zawsze wybieramy "bielizna".

        Args:
            category_name: Nazwa kategorii produktu (np. "Kostiumy dwuczęściowe")
        """
        try:
            from selenium.webdriver.support.ui import Select

            logger.info("Wybór grupy rozmiarowej...")
            print("[DEBUG] Wybór grupy rozmiarowej...")

            # Jeśli kategoria została przekazana z komendy, zawsze wybieramy "bielizna"
            if category_name:
                size_category = "bielizna"
                logger.info(
                    f"Kategoria '{category_name}' -> wybieram grupę rozmiarową: {size_category}")
                print(
                    f"[DEBUG] Kategoria '{category_name}' -> wybieram grupę rozmiarową: {size_category}")

                # Znajdź select z grupą rozmiarową
                size_select = self.wait.until(
                    EC.presence_of_element_located(
                        (By.ID, "mpd_size_category"))
                )

                # Wybierz opcję "bielizna"
                select = Select(size_select)
                try:
                    select.select_by_visible_text(size_category)
                    time.sleep(0.5)
                    logger.info(f"Wybrano grupę rozmiarową: {size_category}")
                    print(f"[DEBUG] Wybrano grupę rozmiarową: {size_category}")
                except Exception as e:
                    logger.warning(
                        f"Nie udało się wybrać grupy rozmiarowej '{size_category}': {e}")
                    print(
                        f"[DEBUG] Nie udało się wybrać grupy rozmiarowej '{size_category}': {e}")
            else:
                logger.info(
                    f"Brak automatycznego wyboru grupy rozmiarowej dla kategorii: {category_name}")
                print(
                    f"[DEBUG] Brak automatycznego wyboru grupy rozmiarowej dla kategorii: {category_name}")

        except Exception as e:
            logger.warning(f"Błąd podczas wyboru grupy rozmiarowej: {e}")
            print(f"[DEBUG] Błąd podczas wyboru grupy rozmiarowej: {e}")

    def select_product_path(self, path_value: str = "5"):
        """
        Zaznacza ścieżkę produktu w select mpd_paths.
        Dla kostiumów dwuczęściowych zaznacza opcję "Dwuczęściowe" (value="5").

        Args:
            path_value: Wartość opcji do zaznaczenia (domyślnie "5" dla Dwuczęściowe)
        """
        try:
            from selenium.webdriver.support.ui import Select

            logger.info("Wybór ścieżki produktu...")
            print("[DEBUG] Wybór ścieżki produktu...")

            # Znajdź select z ścieżkami produktu
            path_select = self.wait.until(
                EC.presence_of_element_located((By.ID, "mpd_paths"))
            )

            # Wybierz opcję "Dwuczęściowe" (value="5")
            select = Select(path_select)
            try:
                # Zaznacz opcję po wartości
                select.select_by_value(path_value)
                time.sleep(0.5)

                # Sprawdź czy opcja została zaznaczona
                selected_options = select.all_selected_options
                if selected_options:
                    selected_text = selected_options[0].text
                    logger.info(
                        f"Wybrano ścieżkę produktu: {selected_text} (value={path_value})")
                    print(
                        f"[DEBUG] Wybrano ścieżkę produktu: {selected_text} (value={path_value})")
                else:
                    logger.warning(
                        f"Nie udało się zaznaczyć ścieżki produktu (value={path_value})")
                    print(
                        f"[DEBUG] Nie udało się zaznaczyć ścieżki produktu (value={path_value})")
            except Exception as e:
                logger.warning(
                    f"Nie udało się wybrać ścieżki produktu '{path_value}': {e}")
                print(
                    f"[DEBUG] Nie udało się wybrać ścieżki produktu '{path_value}': {e}")

        except Exception as e:
            logger.warning(f"Błąd podczas wyboru ścieżki produktu: {e}")
            print(f"[DEBUG] Błąd podczas wyboru ścieżki produktu: {e}")

    def select_unit(self, unit_value: str = "0"):
        """
        Wybiera jednostkę produktu w select unit_id.
        Domyślnie wybiera "szt." (value="0").

        Args:
            unit_value: Wartość opcji do wyboru (domyślnie "0" dla szt.)
        """
        try:
            from selenium.webdriver.support.ui import Select

            logger.info("Wybór jednostki produktu...")
            print("[DEBUG] Wybór jednostki produktu...")

            # Znajdź select z jednostkami
            unit_select = self.wait.until(
                EC.presence_of_element_located((By.ID, "unit_id"))
            )

            # Wybierz opcję "szt." (value="0")
            select = Select(unit_select)
            try:
                # Wybierz opcję po wartości
                select.select_by_value(unit_value)
                time.sleep(0.5)

                # Sprawdź czy opcja została wybrana
                selected_option = select.first_selected_option
                if selected_option and selected_option.get_attribute("value") == unit_value:
                    selected_text = selected_option.text
                    logger.info(
                        f"Wybrano jednostkę produktu: {selected_text} (value={unit_value})")
                    print(
                        f"[DEBUG] Wybrano jednostkę produktu: {selected_text} (value={unit_value})")
                else:
                    logger.warning(
                        f"Nie udało się wybrać jednostki produktu (value={unit_value})")
                    print(
                        f"[DEBUG] Nie udało się wybrać jednostki produktu (value={unit_value})")
            except Exception as e:
                logger.warning(
                    f"Nie udało się wybrać jednostki produktu '{unit_value}': {e}")
                print(
                    f"[DEBUG] Nie udało się wybrać jednostki produktu '{unit_value}': {e}")

        except Exception as e:
            logger.warning(f"Błąd podczas wyboru jednostki produktu: {e}")
            print(f"[DEBUG] Błąd podczas wyboru jednostki produktu: {e}")

    def fill_fabric_materials(self):
        """
        Wyodrębnia materiały z sekcji "Szczegóły produktu" (size_table_html) 
        i wypełnia pola składu (materiały) w formularzu.
        """
        try:
            import re

            logger.info("Wyodrębnianie materiałów z szczegółów produktu...")
            print("[DEBUG] Wyodrębnianie materiałów z szczegółów produktu...")

            # Spróbuj rozwinąć sekcję "Szczegóły produktu" jeśli jest zwinięta
            try:
                details_heading = self.driver.find_element(
                    By.ID, "details-heading"
                )
                # Sprawdź czy sekcja jest zwinięta (sprawdź czy jest klasa "collapsed" lub podobna)
                details_section = self.driver.find_element(
                    By.CSS_SELECTOR, "fieldset[aria-labelledby='details-heading']"
                )
                # Jeśli sekcja jest ukryta, spróbuj ją rozwinąć
                if not details_section.is_displayed():
                    details_heading.click()
                    time.sleep(0.5)
            except:
                pass  # Jeśli nie znajdziemy sekcji, kontynuuj

            # Pobierz zawartość z size_table (główne źródło danych)
            size_table_html = ""
            try:
                # Spróbuj najpierw size_table (główne źródło)
                size_table_field = self.wait.until(
                    EC.presence_of_element_located(
                        (By.ID, "id_details-0-size_table"))
                )
                size_table_html = size_table_field.get_attribute("value") or ""
                if size_table_html:
                    logger.info("Pobrano dane z pola size_table")
                    print("[DEBUG] Pobrano dane z pola size_table")
            except:
                try:
                    # Spróbuj przez XPath dla size_table
                    size_table_field = self.driver.find_element(
                        By.XPATH, "//textarea[@name='details-0-size_table']"
                    )
                    size_table_html = size_table_field.get_attribute(
                        "value") or ""
                    if size_table_html:
                        logger.info("Pobrano dane z pola size_table (XPath)")
                        print("[DEBUG] Pobrano dane z pola size_table (XPath)")
                except:
                    # Fallback do size_table_html
                    try:
                        size_table_html_field = self.wait.until(
                            EC.presence_of_element_located(
                                (By.ID, "id_details-0-size_table_html"))
                        )
                        size_table_html = size_table_html_field.get_attribute(
                            "value") or ""
                        if size_table_html:
                            logger.info("Pobrano dane z pola size_table_html")
                            print("[DEBUG] Pobrano dane z pola size_table_html")
                    except:
                        try:
                            # Spróbuj przez XPath dla size_table_html
                            size_table_html_field = self.driver.find_element(
                                By.XPATH, "//textarea[@name='details-0-size_table_html']"
                            )
                            size_table_html = size_table_html_field.get_attribute(
                                "value") or ""
                            if size_table_html:
                                logger.info(
                                    "Pobrano dane z pola size_table_html (XPath)")
                                print(
                                    "[DEBUG] Pobrano dane z pola size_table_html (XPath)")
                        except:
                            # Fallback do size_table_txt
                            try:
                                size_table_txt_field = self.wait.until(
                                    EC.presence_of_element_located(
                                        (By.ID, "id_details-0-size_table_txt"))
                                )
                                size_table_html = size_table_txt_field.get_attribute(
                                    "value") or ""
                                if size_table_html:
                                    logger.info(
                                        "Pobrano dane z pola size_table_txt")
                                    print(
                                        "[DEBUG] Pobrano dane z pola size_table_txt")
                            except:
                                try:
                                    # Spróbuj przez XPath dla size_table_txt
                                    size_table_txt_field = self.driver.find_element(
                                        By.XPATH, "//textarea[@name='details-0-size_table_txt']"
                                    )
                                    size_table_html = size_table_txt_field.get_attribute(
                                        "value") or ""
                                    if size_table_html:
                                        logger.info(
                                            "Pobrano dane z pola size_table_txt (XPath)")
                                        print(
                                            "[DEBUG] Pobrano dane z pola size_table_txt (XPath)")
                                except:
                                    # Fallback: pobierz dane z bazy danych
                                    logger.info(
                                        "Pola nie znalezione w formularzu, próbuję pobrać z bazy danych...")
                                    print(
                                        "[DEBUG] Pola nie znalezione w formularzu, próbuję pobrać z bazy danych...")

                                    # Wyodrębnij ID produktu z URL
                                    current_url = self.driver.current_url
                                    product_id_match = re.search(
                                        r'/product/(\d+)/', current_url)

                                    if product_id_match:
                                        product_id = int(
                                            product_id_match.group(1))
                                        logger.info(
                                            f"Znaleziono ID produktu w URL: {product_id}")
                                        print(
                                            f"[DEBUG] Znaleziono ID produktu w URL: {product_id}")

                                        # Pobierz szczegóły produktu z bazy danych
                                        try:
                                            from django.db import connections
                                            from matterhorn1.models import Product

                                            with connections['matterhorn1'].cursor() as cursor:
                                                cursor.execute("""
                                                    SELECT pd.size_table, pd.size_table_html, pd.size_table_txt
                                                    FROM productdetails pd
                                                    INNER JOIN product p ON pd.product_id = p.id
                                                    WHERE p.id = %s
                                                """, [product_id])

                                                row = cursor.fetchone()
                                                if row:
                                                    # Priorytet: size_table > size_table_html > size_table_txt
                                                    size_table_html = row[0] or row[1] or row[2] or ""
                                                    if size_table_html:
                                                        logger.info(
                                                            "Pobrano size_table z bazy danych")
                                                        print(
                                                            "[DEBUG] Pobrano size_table z bazy danych")
                                                    else:
                                                        logger.warning(
                                                            "Brak szczegółów produktu w bazie danych")
                                                        print(
                                                            "[DEBUG] Brak szczegółów produktu w bazie danych")
                                                        return
                                                else:
                                                    logger.warning(
                                                        "Brak szczegółów produktu w bazie danych")
                                                    print(
                                                        "[DEBUG] Brak szczegółów produktu w bazie danych")
                                                    return
                                        except Exception as e_db:
                                            logger.warning(
                                                f"Błąd podczas pobierania z bazy danych: {e_db}")
                                            print(
                                                f"[DEBUG] Błąd podczas pobierania z bazy danych: {e_db}")
                                            return
                                    else:
                                        logger.warning(
                                            "Nie udało się wyodrębnić ID produktu z URL")
                                        print(
                                            "[DEBUG] Nie udało się wyodrębnić ID produktu z URL")
                                        return

            if not size_table_html:
                logger.warning("Pole size_table_html jest puste")
                print("[DEBUG] Pole size_table_html jest puste")
                return

            # Wyodrębnij materiały i procenty z HTML
            materials = self._extract_materials_from_html(size_table_html)

            if not materials:
                logger.warning("Nie udało się wyodrębnić materiałów z HTML")
                print("[DEBUG] Nie udało się wyodrębnić materiałów z HTML")
                return

            logger.info(
                f"Wyodrębniono {len(materials)} materiałów: {materials}")
            print(
                f"[DEBUG] Wyodrębniono {len(materials)} materiałów: {materials}")

            # Mapowanie nazw materiałów na wartości w select
            material_mapping = {
                "elastan": "1",
                "poliamid": "2",
                # Można dodać więcej materiałów w przyszłości
            }

            # Znajdź sekcję z materiałami
            fabric_list = self.wait.until(
                EC.presence_of_element_located((By.ID, "fabric-list"))
            )

            # Pobierz istniejące wiersze materiałów
            existing_rows = fabric_list.find_elements(
                By.CSS_SELECTOR, ".fabric-row")

            # Dodaj wiersze jeśli potrzeba
            for i, (material_name, percentage) in enumerate(materials):
                # Normalizuj nazwę materiału (lowercase)
                material_lower = material_name.lower().strip()

                # Znajdź wartość w select
                material_value = None
                for key, value in material_mapping.items():
                    if key in material_lower:
                        material_value = value
                        break

                if not material_value:
                    logger.warning(
                        f"Nie znaleziono mapowania dla materiału: {material_name}")
                    print(
                        f"[DEBUG] Nie znaleziono mapowania dla materiału: {material_name}")
                    continue

                # Użyj istniejącego wiersza lub dodaj nowy
                if i < len(existing_rows):
                    fabric_row = existing_rows[i]
                else:
                    # Kliknij "Dodaj materiał"
                    add_button = self.driver.find_element(
                        By.XPATH, "//button[contains(@onclick, 'addFabricRow')]"
                    )
                    add_button.click()
                    time.sleep(0.5)

                    # Pobierz nowo dodany wiersz
                    existing_rows = fabric_list.find_elements(
                        By.CSS_SELECTOR, ".fabric-row")
                    fabric_row = existing_rows[i]

                # Znajdź select i input w wierszu
                fabric_select = fabric_row.find_element(
                    By.CSS_SELECTOR, "select[name='fabric_component[]']")
                fabric_percentage = fabric_row.find_element(
                    By.CSS_SELECTOR, "input[name='fabric_percentage[]']")

                # Wybierz materiał
                from selenium.webdriver.support.ui import Select
                select = Select(fabric_select)
                select.select_by_value(material_value)
                time.sleep(0.3)

                # Wypełnij procent
                self.driver.execute_script(
                    "arguments[0].value = arguments[1];",
                    fabric_percentage,
                    str(percentage)
                )
                time.sleep(0.3)

                # Wywołaj zdarzenia
                self.driver.execute_script(
                    """
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """,
                    fabric_percentage
                )
                time.sleep(0.2)

                logger.info(
                    f"Wypełniono materiał: {material_name} ({percentage}%)")
                print(
                    f"[DEBUG] Wypełniono materiał: {material_name} ({percentage}%)")

            logger.info(f"Wypełniono {len(materials)} materiałów")
            print(f"[DEBUG] Wypełniono {len(materials)} materiałów")

            # Poczekaj chwilę, aby upewnić się, że formularz jest gotowy
            time.sleep(1)

        except Exception as e:
            logger.warning(f"Błąd podczas wypełniania materiałów: {e}")
            print(f"[DEBUG] Błąd podczas wypełniania materiałów: {e}")

    def _extract_materials_from_html(self, html_content: str) -> list:
        """
        Wyodrębnia materiały i procenty z HTML.

        Przykład:
        Input: "<strong>Elastan</strong> 20 % <br><strong>poliamid</strong> 80 % <br>"
        Output: [("Elastan", 20), ("poliamid", 80)]

        Args:
            html_content: Zawartość HTML z materiałami

        Returns:
            Lista tupli (nazwa_materiału, procent)
        """
        if not html_content:
            return []

        import re

        materials = []

        # Wzorzec 1: <strong>Materiał</strong> XX % (najczęstszy format)
        pattern1 = r'<strong>([^<]+)</strong>\s*(\d+)\s*%'
        matches1 = re.findall(pattern1, html_content, re.IGNORECASE)

        for material_name, percentage_str in matches1:
            try:
                percentage = int(percentage_str)
                materials.append((material_name.strip(), percentage))
            except ValueError:
                continue

        # Jeśli nie znaleziono, spróbuj wzorca bez tagów strong
        if not materials:
            # Wzorzec 2: Materiał XX % (bez HTML tagów)
            # Najpierw usuń tagi HTML
            text_content = re.sub(r'<[^>]+>', ' ', html_content)
            pattern2 = r'([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:[a-ząćęłńóśźż]+)*)\s+(\d+)\s*%'
            matches2 = re.findall(pattern2, text_content)

            # Słowa do pominięcia (nie są materiałami)
            skip_words = {
                'rozmiar', 'obwód', 'cm', 'table', 'thead', 'tbody', 'tr', 'td', 'th',
                'div', 'class', 'prod', 'data', 'table', 'striped', 'bordered', 'hover',
                'responsive', 'thead', 'tbody', 'strong', 'br', 'align', 'right'
            }

            for material_name, percentage_str in matches2:
                try:
                    material_lower = material_name.lower().strip()
                    if material_lower not in skip_words and len(material_name) > 2:
                        percentage = int(percentage_str)
                        materials.append((material_name.strip(), percentage))
                except ValueError:
                    continue

        return materials

    def select_attributes(self, attribute_ids: List[int]):
        """
        Zaznacza atrybuty w formularzu.

        Args:
            attribute_ids: Lista ID atrybutów do zaznaczenia
        """
        try:
            if not attribute_ids:
                logger.info("Brak atrybutów do zaznaczenia")
                print("[DEBUG] Brak atrybutów do zaznaczenia")
                return

            logger.info(f"Zaznaczanie {len(attribute_ids)} atrybutów...")
            print(
                f"[DEBUG] Zaznaczanie {len(attribute_ids)} atrybutów: {attribute_ids}")

            # Znajdź select z atrybutami
            attributes_select = self.wait.until(
                EC.presence_of_element_located((By.ID, "mpd_attributes"))
            )

            # Zaznacz atrybuty przez JavaScript (najbardziej niezawodne dla multiple select)
            for attr_id in attribute_ids:
                try:
                    # Znajdź opcję po value
                    option = attributes_select.find_element(
                        By.CSS_SELECTOR, f'option[value="{attr_id}"]'
                    )

                    # Zaznacz opcję przez JavaScript
                    self.driver.execute_script(
                        "arguments[0].selected = true;",
                        option
                    )

                    # Wywołaj zdarzenie change
                    self.driver.execute_script(
                        """
                        var select = arguments[0];
                        var option = arguments[1];
                        option.selected = true;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        """,
                        attributes_select,
                        option
                    )

                    logger.info(f"Zaznaczono atrybut ID: {attr_id}")
                    print(f"[DEBUG] Zaznaczono atrybut ID: {attr_id}")

                except NoSuchElementException:
                    logger.warning(f"Nie znaleziono atrybutu o ID: {attr_id}")
                    print(f"[DEBUG] Nie znaleziono atrybutu o ID: {attr_id}")
                    continue

            time.sleep(0.5)

            # Sprawdź ile atrybutów zostało zaznaczonych
            selected_options = attributes_select.find_elements(
                By.CSS_SELECTOR, "option:checked"
            )
            logger.info(f"Zaznaczono {len(selected_options)} atrybutów")
            print(f"[DEBUG] Zaznaczono {len(selected_options)} atrybutów")

        except Exception as e:
            logger.error(f"Błąd podczas zaznaczania atrybutów: {e}")
            print(f"[DEBUG] Błąd podczas zaznaczania atrybutów: {e}")
            import traceback
            traceback.print_exc()

    def handle_assign_scenario(self, brand_id=None, brand_name=None):
        """
        SCENARIUSZ ASSIGN: Obsługuje przypisanie produktu do istniejącego produktu w MPD.
        
        Sprawdza czy istnieje sekcja "Sugerowane podobne produkty w MPD" i dla każdego
        wiersza z pokryciem 100% wypełnia pola i klika przycisk "Przypisz".
        
        Args:
            brand_id: ID marki (opcjonalne, dla mapowania kolorów)
            brand_name: Nazwa marki (opcjonalne, dla mapowania kolorów)
            
        Returns:
            bool: True jeśli znaleziono i obsłużono sugerowane produkty, False jeśli nie
        """
        try:
            logger.info("=" * 50)
            logger.info("SCENARIUSZ ASSIGN: Sprawdzanie sugerowanych produktów")
            logger.info("=" * 50)
            print("[DEBUG] " + "=" * 50)
            print("[DEBUG] SCENARIUSZ ASSIGN: Sprawdzanie sugerowanych produktów")
            print("[DEBUG] " + "=" * 50)
            
            # Sprawdź czy istnieje sekcja "Sugerowane podobne produkty w MPD"
            try:
                # Szukaj nagłówka "Sugerowane podobne produkty w MPD"
                suggested_section = self.driver.find_element(
                    By.XPATH, "//h3[contains(text(), 'Sugerowane podobne produkty w MPD')]"
                )
                logger.info("Znaleziono sekcję sugerowanych produktów")
                print("[DEBUG] Znaleziono sekcję sugerowanych produktów")
            except NoSuchElementException:
                logger.info("Brak sekcji sugerowanych produktów - produkt nie ma sugerowanych mapowań")
                print("[DEBUG] Brak sekcji sugerowanych produktów - produkt nie ma sugerowanych mapowań")
                return False
            
            # Znajdź tabelę z sugerowanymi produktami
            try:
                # Tabela jest w tym samym div co nagłówek
                parent_div = suggested_section.find_element(By.XPATH, "./ancestor::div[contains(@class, 'form-row')]")
                table = parent_div.find_element(By.XPATH, ".//table")
                logger.info("Znaleziono tabelę sugerowanych produktów")
                print("[DEBUG] Znaleziono tabelę sugerowanych produktów")
            except NoSuchElementException:
                logger.warning("Nie znaleziono tabeli sugerowanych produktów")
                print("[DEBUG] Nie znaleziono tabeli sugerowanych produktów")
                return False
            
            # Znajdź wszystkie wiersze w tbody (pomijając nagłówek)
            rows = table.find_elements(By.XPATH, ".//tbody/tr")
            logger.info(f"Znaleziono {len(rows)} wierszy w tabeli sugerowanych produktów")
            print(f"[DEBUG] Znaleziono {len(rows)} wierszy w tabeli sugerowanych produktów")
            
            if not rows:
                logger.info("Brak wierszy w tabeli sugerowanych produktów")
                print("[DEBUG] Brak wierszy w tabeli sugerowanych produktów")
                return False
            
            # Przetwarzaj każdy wiersz
            for idx, row in enumerate(rows, 1):
                try:
                    logger.info(f"Przetwarzanie wiersza {idx}/{len(rows)}")
                    print(f"[DEBUG] Przetwarzanie wiersza {idx}/{len(rows)}")
                    
                    # Znajdź kolumnę "Pokrycie" (4. kolumna, indeks 3)
                    coverage_cells = row.find_elements(By.XPATH, ".//td")
                    if len(coverage_cells) < 4:
                        logger.warning(f"Wiersz {idx} nie ma wystarczającej liczby kolumn")
                        print(f"[DEBUG] Wiersz {idx} nie ma wystarczającej liczby kolumn")
                        continue
                    
                    # Kolumna "Pokrycie" to 4. kolumna (indeks 3)
                    coverage_cell = coverage_cells[3]
                    coverage_text = coverage_cell.text.strip()
                    
                    logger.info(f"Wiersz {idx}: Pokrycie = {coverage_text}")
                    print(f"[DEBUG] Wiersz {idx}: Pokrycie = {coverage_text}")
                    
                    # Sprawdź czy pokrycie = 100%
                    coverage_value = None
                    try:
                        # Usuń znak % i zamień przecinek na kropkę
                        coverage_clean = coverage_text.replace('%', '').replace(',', '.')
                        coverage_value = float(coverage_clean)
                    except ValueError:
                        logger.warning(f"Nie można sparsować pokrycia: {coverage_text}")
                        print(f"[DEBUG] Nie można sparsować pokrycia: {coverage_text}")
                        continue
                    
                    # Jeśli pokrycie nie jest 100%, pomiń ten wiersz
                    if coverage_value < 100.0:
                        logger.info(f"Wiersz {idx}: Pokrycie {coverage_value}% < 100%, pomijam")
                        print(f"[DEBUG] Wiersz {idx}: Pokrycie {coverage_value}% < 100%, pomijam")
                        continue
                    
                    logger.info(f"Wiersz {idx}: Pokrycie = 100%, wypełniam pola i przypisuję")
                    print(f"[DEBUG] Wiersz {idx}: Pokrycie = 100%, wypełniam pola i przypisuję")
                    
                    # KROK ASSIGN 1: Wypełnij główny kolor (tak jak w kroku 7)
                    try:
                        # Znajdź select głównego koloru w tym wierszu
                        main_color_select = row.find_element(By.CSS_SELECTOR, "select.main-color-select")
                        
                        # Przewiń do elementu, aby był widoczny
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                            main_color_select
                        )
                        time.sleep(0.5)
                        
                        from selenium.webdriver.support.ui import Select
                        color_select = Select(main_color_select)
                        
                        # Pobierz kolor z pola id_color (tak jak w kroku 7)
                        color_input = self.driver.find_element(By.ID, "id_color")
                        color_name = color_input.get_attribute("value")
                        if color_name:
                            color_name = color_name.strip()
                            logger.info(f"Pobrano kolor z pola id_color: {color_name}")
                            print(f"[DEBUG] Pobrano kolor z pola id_color: {color_name}")
                            
                            # Znajdź wartość opcji dla koloru
                            matched_value = None
                            for opt in color_select.options:
                                text = opt.text or ""
                                opt_value = opt.get_attribute("value")
                                if not opt_value:
                                    continue
                                if text.strip().lower() == color_name.lower():
                                    matched_value = opt_value
                                    break
                            
                            if matched_value:
                                color_select.select_by_value(matched_value)
                                logger.info(f"Wybrano główny kolor: {color_name} (value: {matched_value})")
                                print(f"[DEBUG] Wybrano główny kolor: {color_name} (value: {matched_value})")
                                time.sleep(0.3)
                    except Exception as e_color:
                        logger.warning(f"Błąd podczas wypełniania głównego koloru w wierszu {idx}: {e_color}")
                        print(f"[DEBUG] Błąd podczas wypełniania głównego koloru w wierszu {idx}: {e_color}")
                    
                    # KROK ASSIGN 2: Wypełnij kolor producenta (tak jak w kroku 8)
                    try:
                        logger.info(f"KROK ASSIGN 2: Wypełnianie koloru producenta w wierszu {idx}")
                        print(f"[DEBUG] KROK ASSIGN 2: Wypełnianie koloru producenta w wierszu {idx}")
                        
                        # Znajdź input koloru producenta w tym wierszu
                        producer_color_input = row.find_element(By.CSS_SELECTOR, "input.producer-color-input")
                        
                        # Przewiń do elementu, aby był widoczny
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                            producer_color_input
                        )
                        time.sleep(0.5)
                        
                        # Użyj tej samej logiki co w kroku 8 (update_producer_color)
                        color_name = None
                        if hasattr(self, '_original_product_name') and self._original_product_name:
                            logger.info(f"Używam oryginalnej nazwy produktu: {self._original_product_name}")
                            print(f"[DEBUG] Używam oryginalnej nazwy produktu: {self._original_product_name}")
                            original_name = self._original_product_name
                            
                            # 1. NAJPIERW wyodrębnij kolor z nazwy (regex-based, NIE Pydantic)
                            #    Obsługuje kolory złożone: jeśli kolor zawiera "/" (np. "Coral/Blue"), oznacza to DWA KOLORY
                            logger.info("Wyodrębnianie koloru producenta z nazwy produktu (ASSIGN)...")
                            print("[DEBUG] Wyodrębnianie koloru producenta z nazwy produktu (ASSIGN)...")
                            print("[DEBUG] UWAGA: Jeśli kolor zawiera '/' (np. 'Coral/Blue'), oznacza to DWA KOLORY")
                            color_name = self._extract_color_from_name(original_name)
                            
                            # 2. Sprawdź czy wyodrębniony kolor istnieje w bazie dla danej marki
                            if color_name and brand_id and brand_name:
                                from web_agent.models import ProducerColor
                                try:
                                    # Sprawdź czy dokładnie taki kolor istnieje w bazie
                                    color_obj = ProducerColor.objects.get(
                                        brand_id=brand_id,
                                        color_name=color_name
                                    )
                                    # Zwiększ licznik użycia
                                    color_obj.usage_count += 1
                                    color_obj.save(update_fields=['usage_count', 'updated_at'])
                                    logger.info(f"Znaleziono kolor w bazie (dokładne dopasowanie): {color_name} (użycie #{color_obj.usage_count})")
                                    print(f"[DEBUG] Znaleziono kolor w bazie (dokładne dopasowanie): {color_name} (użycie #{color_obj.usage_count})")
                                except ProducerColor.DoesNotExist:
                                    # Jeśli nie istnieje, zapisz nowy kolor do bazy
                                    color_obj, created = ProducerColor.objects.get_or_create(
                                        brand_id=brand_id,
                                        color_name=color_name,
                                        defaults={'brand_name': brand_name}
                                    )
                                    if created:
                                        logger.info(f"Dodano nowy kolor do bazy: {color_name} dla marki {brand_name}")
                                        print(f"[DEBUG] Dodano nowy kolor do bazy: {color_name} dla marki {brand_name}")
                            
                            # 3. Fallback: Jeśli nie udało się wyodrębnić z nazwy, sprawdź bazę (dla pojedynczych kolorów)
                            if not color_name and brand_id and brand_name:
                                from web_agent.models import ProducerColor
                                existing_colors = ProducerColor.objects.filter(brand_id=brand_id)
                                
                                if existing_colors.exists():
                                    import re
                                    sorted_colors = sorted(existing_colors, key=lambda x: len(x.color_name), reverse=True)
                                    original_name_lower = original_name.lower()
                                    
                                    for color_obj in sorted_colors:
                                        color_lower = color_obj.color_name.lower()
                                        pattern = r'\b' + re.escape(color_lower) + r'\b'
                                        if re.search(pattern, original_name_lower):
                                            color_name = color_obj.color_name
                                            color_obj.usage_count += 1
                                            color_obj.save(update_fields=['usage_count', 'updated_at'])
                                            logger.info(f"Znaleziono kolor w bazie (fallback): {color_name}")
                                            print(f"[DEBUG] Znaleziono kolor w bazie (fallback): {color_name}")
                                            break
                            
                            # 3. Mapowanie kolorów z BrandConfig
                            if color_name and brand_id:
                                try:
                                    from web_agent.models import BrandConfig
                                    brand_config = BrandConfig.objects.get(brand_id=brand_id)
                                    if brand_config and brand_config.color_mapping:
                                        color_mapping = brand_config.color_mapping
                                        color_name_lower = color_name.lower().strip()
                                        for original, mapped in color_mapping.items():
                                            if original.lower().strip() == color_name_lower:
                                                color_name = mapped
                                                logger.info(f"Zmapowano kolor: '{color_name}' -> '{mapped}'")
                                                break
                                except Exception:
                                    pass
                            
                            # 4. Wypełnij pole
                            if color_name:
                                # Wyczyść przez JavaScript
                                self.driver.execute_script(
                                    "arguments[0].value = '';",
                                    producer_color_input
                                )
                                time.sleep(0.2)
                                
                                # Wypełnij pole
                                try:
                                    producer_color_input.send_keys(color_name)
                                except Exception as e_send:
                                    # Jeśli send_keys nie działa, użyj JavaScript
                                    logger.warning(f"send_keys nie działa, używam JavaScript: {e_send}")
                                    print(f"[DEBUG] send_keys nie działa, używam JavaScript: {e_send}")
                                    self.driver.execute_script(
                                        "arguments[0].value = arguments[1];",
                                        producer_color_input,
                                        color_name
                                    )
                                
                                time.sleep(0.2)
                                
                                # Wywołaj zdarzenia
                                self.driver.execute_script(
                                    """
                                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                                    """,
                                    producer_color_input
                                )
                                time.sleep(0.3)
                                
                                logger.info(f"Wypełniono kolor producenta: {color_name}")
                                print(f"[DEBUG] Wypełniono kolor producenta: {color_name}")
                    except Exception as e_prod_color:
                        logger.warning(f"Błąd podczas wypełniania koloru producenta w wierszu {idx}: {e_prod_color}")
                        print(f"[DEBUG] Błąd podczas wypełniania koloru producenta w wierszu {idx}: {e_prod_color}")
                    
                    # KROK ASSIGN 3: Wypełnij kod producenta (tak jak w kroku 9)
                    try:
                        logger.info(f"KROK ASSIGN 3: Wypełnianie kodu producenta w wierszu {idx}")
                        print(f"[DEBUG] KROK ASSIGN 3: Wypełnianie kodu producenta w wierszu {idx}")
                        
                        # Znajdź input kodu producenta w tym wierszu
                        producer_code_input = row.find_element(By.CSS_SELECTOR, "input.producer-code-input")
                        
                        # Przewiń do elementu, aby był widoczny
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                            producer_code_input
                        )
                        time.sleep(0.5)
                        
                        # Użyj tej samej logiki co w kroku 9 (_extract_producer_code_from_name)
                        if hasattr(self, '_original_product_name') and self._original_product_name:
                            logger.info(f"Używam oryginalnej nazwy produktu do wyodrębnienia kodu: {self._original_product_name}")
                            print(f"[DEBUG] Używam oryginalnej nazwy produktu do wyodrębnienia kodu: {self._original_product_name}")
                            producer_code = self._extract_producer_code_from_name(self._original_product_name)
                            if producer_code:
                                # Wyczyść i wypełnij przez JavaScript (bardziej niezawodne)
                                self.driver.execute_script(
                                    "arguments[0].value = '';",
                                    producer_code_input
                                )
                                time.sleep(0.2)
                                producer_code_input.send_keys(producer_code)
                                time.sleep(0.3)
                                logger.info(f"Wypełniono kod producenta: {producer_code}")
                                print(f"[DEBUG] Wypełniono kod producenta: {producer_code}")
                    except Exception as e_code:
                        logger.warning(f"Błąd podczas wypełniania kodu producenta w wierszu {idx}: {e_code}")
                        print(f"[DEBUG] Błąd podczas wypełniania kodu producenta w wierszu {idx}: {e_code}")
                    
                    # KROK ASSIGN 4: Kliknij przycisk "Przypisz"
                    try:
                        logger.info(f"KROK ASSIGN 4: Kliknięcie przycisku 'Przypisz' w wierszu {idx}")
                        print(f"[DEBUG] KROK ASSIGN 4: Kliknięcie przycisku 'Przypisz' w wierszu {idx}")
                        
                        assign_button = row.find_element(By.CSS_SELECTOR, "button.assign-mapping-btn")
                        mpd_product_id = assign_button.get_attribute("data-mpd-id")
                        logger.info(f"Klikam przycisk 'Przypisz' dla produktu MPD ID: {mpd_product_id}")
                        print(f"[DEBUG] Klikam przycisk 'Przypisz' dla produktu MPD ID: {mpd_product_id}")
                        
                        # Przewiń do przycisku, aby był widoczny
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                            assign_button
                        )
                        time.sleep(0.5)
                        
                        # Spróbuj kliknąć normalnie
                        try:
                            assign_button.click()
                        except Exception as e_click:
                            # Jeśli zwykłe kliknięcie nie działa, użyj JavaScript
                            logger.warning(f"Zwykłe kliknięcie nie działa, używam JavaScript: {e_click}")
                            print(f"[DEBUG] Zwykłe kliknięcie nie działa, używam JavaScript: {e_click}")
                            self.driver.execute_script("arguments[0].click();", assign_button)
                        
                        time.sleep(3)  # Czekaj na przetworzenie i ewentualne przekierowanie
                        
                        logger.info(f"✓ Przypisano produkt do MPD ID: {mpd_product_id}")
                        print(f"[DEBUG] ✓ Przypisano produkt do MPD ID: {mpd_product_id}")
                        
                        # Po przypisaniu, sprawdź czy jesteśmy na stronie produktu czy już na liście
                        # Jeśli jesteśmy na stronie produktu, wróć do listy
                        # Uwaga: filtered_list_url będzie przekazany przez run_automation.py
                        try:
                            current_url = self.driver.current_url
                            logger.info(f"URL po przypisaniu: {current_url}")
                            print(f"[DEBUG] URL po przypisaniu: {current_url}")
                            if '/change/' in current_url:
                                logger.info("Po przypisaniu - wracam do listy produktów")
                                print("[DEBUG] Po przypisaniu - wracam do listy produktów")
                                # Użyj zapisanego URL jeśli jest dostępny (przekazany przez parametr)
                                # Jeśli nie, użyj domyślnej metody
                                if hasattr(self, '_saved_filtered_list_url') and self._saved_filtered_list_url:
                                    self.navigate_back_to_product_list(filtered_list_url=self._saved_filtered_list_url)
                                else:
                                    self.navigate_back_to_product_list()
                                time.sleep(2)
                            else:
                                logger.info("Po przypisaniu - już jesteśmy na liście produktów")
                                print("[DEBUG] Po przypisaniu - już jesteśmy na liście produktów")
                        except Exception as e_nav:
                            logger.warning(f"Błąd podczas nawigacji po przypisaniu: {e_nav}")
                            print(f"[DEBUG] Błąd podczas nawigacji po przypisaniu: {e_nav}")
                        
                        # Po przypisaniu, przerwij pętlę (tylko pierwszy produkt z 100% pokryciem)
                        return True
                        
                    except Exception as e_button:
                        logger.warning(f"Błąd podczas klikania przycisku 'Przypisz' w wierszu {idx}: {e_button}")
                        print(f"[DEBUG] Błąd podczas klikania przycisku 'Przypisz' w wierszu {idx}: {e_button}")
                
                except Exception as e_row:
                    logger.warning(f"Błąd podczas przetwarzania wiersza {idx}: {e_row}")
                    print(f"[DEBUG] Błąd podczas przetwarzania wiersza {idx}: {e_row}")
                    continue
            
            logger.info("Nie znaleziono wiersza z pokryciem 100%")
            print("[DEBUG] Nie znaleziono wiersza z pokryciem 100%")
            return False
            
        except Exception as e:
            logger.error(f"Błąd podczas obsługi scenariusza ASSIGN: {e}")
            print(f"[DEBUG] Błąd podczas obsługi scenariusza ASSIGN: {e}")
            import traceback
            traceback.print_exc()
            return False
    

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
