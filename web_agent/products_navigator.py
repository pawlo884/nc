import time
import os
from urllib.parse import urlencode
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from admin_login import AdminLoginAgent
from lupo_line_knowledge_base import lupo_knowledge

# Próba importu OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI nie jest zainstalowane. Uruchom: pip install openai")


class ProductsNavigator:
    """Klasa do nawigacji po produktach w panelu admina"""

    def __init__(self, admin_url="http://localhost:8000/admin/",
                 username=None, password=None,
                 wait_timeout=10, auto_close_delay=10):
        """
        Inicjalizacja nawigatora produktów

        Args:
            admin_url (str): URL panelu admina
            username (str): Nazwa użytkownika
            password (str): Hasło
            wait_timeout (int): Timeout dla oczekiwania na elementy
            auto_close_delay (int): Opóźnienie przed zamknięciem przeglądarki
        """
        self.login_agent = AdminLoginAgent(
            admin_url=admin_url,
            username=username,
            password=password,
            wait_timeout=wait_timeout,
            auto_close_delay=auto_close_delay
        )
        self.base_url = admin_url.rstrip('/')
        self.is_logged_in = False

    def _ensure_logged_in(self):
        """Zapewnia że użytkownik jest zalogowany"""
        if not self.is_logged_in:
            print("Logowanie do panelu admina...")
            if not self.login_agent.login(keep_browser_open=True):
                print("❌ Nie udało się zalogować do panelu")
                return False
            self.is_logged_in = True
            print("✅ Zalogowano pomyślnie")
        return True

    def navigate_to_products(self, active=True, brand=None, category_name=None,
                             is_mapped=None, additional_params=None):
        """
        Nawiguje do strony produktów z filtrami

        Args:
            active (bool): Filtr aktywnych produktów
            brand (str): Nazwa marki do filtrowania
            category_name (str): Nazwa kategorii do filtrowania
            is_mapped (int): Status mapowania (0, 1 lub None)
            additional_params (dict): Dodatkowe parametry URL

        Returns:
            bool: True jeśli nawigacja się powiodła
        """
        try:
            # Upewnij się że jesteśmy zalogowani
            if not self._ensure_logged_in():
                return False

            # Buduj URL z filtrami
            products_url = f"{self.base_url}/admin/matterhorn/products/"
            params = {}

            if active is not None:
                params['active'] = 'true' if active else 'false'

            if brand:
                params['brand'] = brand

            if category_name:
                params['category_name'] = category_name

            if is_mapped is not None:
                params['is_mapped__exact'] = str(is_mapped)

            if additional_params:
                params.update(additional_params)

            if params:
                products_url += "?" + urlencode(params)

            print(f"Przechodzę do: {products_url}")

            # Przejdź do strony produktów
            driver = self.login_agent.get_driver()
            driver.get(products_url)

            # Poczekaj na załadowanie strony
            time.sleep(3)

            # Sprawdź czy strona się załadowała poprawnie
            current_url = driver.current_url
            print(f"Aktualny URL: {current_url}")

            if "matterhorn/products" in current_url:
                print("✅ Nawigacja do produktów zakończona sukcesem!")

                # Sprawdź czy są produkty na stronie
                self._check_products_on_page(driver)

                return True
            else:
                print("❌ Nie udało się przejść do strony produktów")
                return False

        except Exception as e:
            print(f"❌ Błąd podczas nawigacji: {str(e)}")
            return False

    def navigate_to_specific_url(self, url):
        """
        Nawiguje do konkretnego URL po zalogowaniu

        Args:
            url (str): Pełny URL do przejścia

        Returns:
            bool: True jeśli nawigacja się powiodła
        """
        try:
            # Upewnij się że jesteśmy zalogowani
            if not self._ensure_logged_in():
                return False

            print(f"Przechodzę do: {url}")

            # Przejdź do podanego URL
            driver = self.login_agent.get_driver()
            driver.get(url)

            # Poczekaj na załadowanie strony
            time.sleep(3)

            current_url = driver.current_url
            print(f"Aktualny URL: {current_url}")

            # Sprawdź czy są produkty na stronie jeśli to strona produktów
            if "matterhorn/products" in current_url:
                self._check_products_on_page(driver)

            print("✅ Nawigacja zakończona sukcesem!")

            return True

        except Exception as e:
            print(f"❌ Błąd podczas nawigacji: {str(e)}")
            return False

    def _check_products_on_page(self, driver):
        """Sprawdza liczbę produktów na stronie"""
        try:
            # Szukamy tabeli z produktami
            products_table = driver.find_elements(
                By.CSS_SELECTOR, "#result_list")
            if products_table:
                rows = driver.find_elements(
                    By.CSS_SELECTOR, "#result_list tbody tr")
                print(f"📊 Znaleziono {len(rows)} produktów na stronie")

                # Sprawdź informacje o paginacji
                try:
                    paginator = driver.find_element(By.CLASS_NAME, "paginator")
                    paginator_text = paginator.text
                    print(f"📄 Informacje o paginacji: {paginator_text}")
                except Exception:
                    print("📄 Brak informacji o paginacji")

                return len(rows)
            else:
                # Sprawdź czy jest komunikat o braku wyników
                try:
                    no_results = driver.find_element(
                        By.CSS_SELECTOR, ".results")
                    if "0 " in no_results.text or "brak" in no_results.text.lower():
                        print("📊 Brak produktów spełniających kryteria")
                    else:
                        print(
                            "📊 Strona załadowana - struktura może być inna niż oczekiwana")
                except Exception:
                    print("📊 Nie można określić liczby produktów")
                return 0

        except Exception as e:
            print(f"⚠️ Nie można sprawdzić produktów na stronie: {str(e)}")
            return 0

    def click_first_product(self):
        """Kliknie w pierwszy produkt na liście"""
        try:
            # Upewnij się że jesteśmy zalogowani
            if not self._ensure_logged_in():
                return False

            driver = self.login_agent.get_driver()

            # Sprawdź czy jesteśmy na stronie produktów
            current_url = driver.current_url
            if "matterhorn/products" not in current_url:
                print("❌ Nie jesteśmy na stronie produktów")
                return False

            # Sprawdź czy są produkty na stronie
            products_count = self._check_products_on_page(driver)
            if products_count == 0:
                print("❌ Brak produktów na stronie do kliknięcia")
                return False

            # Znajdź pierwszy link do produktu w tabeli
            try:
                # Szukamy pierwszego linku w kolumnie ID (pierwsza kolumna)
                first_product_link = driver.find_element(
                    By.CSS_SELECTOR,
                    "#result_list tbody tr:first-child th.field-id a"
                )

                product_id = first_product_link.text
                print(f"🎯 Klikam w pierwszy produkt (ID: {product_id})")

                # Kliknij w link
                first_product_link.click()

                # Poczekaj na załadowanie strony szczegółów produktu
                time.sleep(3)

                # Sprawdź czy przeszliśmy do strony szczegółów produktu
                new_url = driver.current_url
                print(f"📍 Nowy URL: {new_url}")

                if "/change/" in new_url or "/add/" in new_url:
                    print("✅ Pomyślnie przeszedłem do szczegółów pierwszego produktu!")
                    return True
                else:
                    print("❌ Nie udało się przejść do szczegółów produktu")
                    return False

            except Exception as e:
                print(
                    f"❌ Nie można znaleźć pierwszego produktu w kolumnie ID: {str(e)}")

                # Spróbuj alternatywny selektor - pierwszy link w pierwszym wierszu
                try:
                    print("🔄 Próbuję alternatywny sposób - pierwszy link w wierszu...")
                    first_product_link = driver.find_element(
                        By.CSS_SELECTOR,
                        "#result_list tbody tr:first-child a"
                    )

                    product_info = first_product_link.text or "Nieznane ID"
                    print(f"🎯 Klikam w pierwszy produkt (alt): {product_info}")

                    first_product_link.click()
                    time.sleep(3)

                    new_url = driver.current_url
                    print(f"📍 Nowy URL: {new_url}")

                    if "/change/" in new_url:
                        print(
                            "✅ Pomyślnie przeszedłem do szczegółów produktu (alternatywnie)!")
                        return True
                    else:
                        print("❌ Alternatywny sposób też nie zadziałał")
                        return False

                except Exception as alt_e:
                    print(
                        f"❌ Alternatywny sposób też nie zadziałał: {str(alt_e)}")

                    # Ostatnia próba - szukamy wszystkich linków w pierwszym wierszu
                    try:
                        print(
                            "🔄 Ostatnia próba - szukam wszystkich linków w pierwszym wierszu...")
                        all_links = driver.find_elements(
                            By.CSS_SELECTOR,
                            "#result_list tbody tr:first-child a"
                        )

                        if all_links:
                            for i, link in enumerate(all_links):
                                print(
                                    f"Link {i+1}: {link.text} -> {link.get_attribute('href')}")

                            # Kliknij pierwszy znaleziony link
                            first_link = all_links[0]
                            print(
                                f"🎯 Klikam w pierwszy znaleziony link: {first_link.text}")
                            first_link.click()
                            time.sleep(3)

                            new_url = driver.current_url
                            print(f"📍 Nowy URL: {new_url}")

                            if "/change/" in new_url:
                                print("✅ Sukces z ostatnią próbą!")
                                return True

                        print("❌ Wszystkie próby nie powiodły się")
                        return False

                    except Exception as final_e:
                        print(
                            f"❌ Ostatnia próba też nie zadziałała: {str(final_e)}")
                        return False

        except Exception as e:
            print(f"❌ Błąd podczas klikania w pierwszy produkt: {str(e)}")
            return False

    def navigate_and_click_first_product(self, active=True, brand=None, category_name=None,
                                         is_mapped=None, additional_params=None):
        """
        Nawiguje do strony produktów i kliknie w pierwszy produkt

        Args:
            active (bool): Filtr aktywnych produktów
            brand (str): Nazwa marki do filtrowania
            category_name (str): Nazwa kategorii do filtrowania
            is_mapped (int): Status mapowania (0, 1 lub None)
            additional_params (dict): Dodatkowe parametry URL

        Returns:
            bool: True jeśli cała operacja się powiodła
        """
        try:
            # Najpierw nawiguj do strony produktów
            print("🚀 Rozpoczynam nawigację do produktów...")
            if not self.navigate_to_products(active, brand, category_name, is_mapped, additional_params):
                print("❌ Nie udało się nawigować do strony produktów")
                return False

            # Następnie kliknij w pierwszy produkt
            print("🎯 Próbuję kliknąć w pierwszy produkt...")
            if not self.click_first_product():
                print("❌ Nie udało się kliknąć w pierwszy produkt")
                return False

            print("✅ Pełna operacja zakończona sukcesem!")
            return True

        except Exception as e:
            print(f"❌ Błąd podczas pełnej operacji: {str(e)}")
            return False

    def navigate_to_url_and_click_first_product(self, url):
        """
        Nawiguje do konkretnego URL i kliknie w pierwszy produkt

        Args:
            url (str): Pełny URL do przejścia

        Returns:
            bool: True jeśli cała operacja się powiodła
        """
        try:
            # Najpierw nawiguj do URL
            print("🚀 Rozpoczynam nawigację do URL...")
            if not self.navigate_to_specific_url(url):
                print("❌ Nie udało się nawigować do URL")
                return False

            # Następnie kliknij w pierwszy produkt
            print("🎯 Próbuję kliknąć w pierwszy produkt...")
            if not self.click_first_product():
                print("❌ Nie udało się kliknąć w pierwszy produkt")
                return False

            print("✅ Pełna operacja zakończona sukcesem!")
            return True

        except Exception as e:
            print(f"❌ Błąd podczas pełnej operacji: {str(e)}")
            return False

    def get_driver(self):
        """Zwraca instancję WebDriver"""
        return self.login_agent.get_driver()

    def close_browser(self):
        """Zamyka przeglądarkę"""
        self.login_agent.close_browser()
        self.is_logged_in = False

    def __enter__(self):
        """Context manager - rozpoczęcie"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - zakończenie"""
        self.close_browser()


class ProductEditor:
    """Klasa do edycji produktów w panelu admina"""

    def __init__(self, products_navigator=None):
        """
        Inicjalizacja edytora produktów

        Args:
            products_navigator (ProductsNavigator): Istniejący navigator lub None dla nowego
        """
        if products_navigator:
            self.navigator = products_navigator
            self.owned_navigator = False
        else:
            self.navigator = ProductsNavigator()
            self.owned_navigator = True

    def get_ai_optimized_title(self, current_title):
        """
        Używa AI do optymalizacji tytułu według wytycznych

        Args:
            current_title (str): Aktualny tytuł produktu

        Returns:
            str: Zoptymalizowany tytuł
        """
        # Tutaj można zintegrować z API AI (OpenAI, Claude itp.)
        # Na razie implementuję rozszerzoną logikę dla różnych wzorców produktów

        print(f"🔍 Analizuję tytuł: {current_title}")

        # Podstawowe czyszczenie tytułu
        title = current_title.strip()

        # Podziel tytuł na części (zwykle oddzielone " - ")
        parts = title.split(" - ")
        main_part = parts[0].strip() if parts else title
        brand = parts[-1].strip() if len(parts) > 1 else ""

        print(f"📝 Część główna: {main_part}")
        print(f"🏷️ Marka: {brand}")

        # Wzorce dla kostiumów dwuczęściowych
        optimized_title = None

        # 1. Kostiumy dwuczęściowe - Szorty Kąpielowe (nowy typ!)
        if self._is_szorty_swimsuit(main_part):
            optimized_title = self._optimize_szorty_title(main_part)

        # 2. Kostiumy dwuczęściowe - Figi (tolerancja na literówki)
        elif self._is_figi_swimsuit(main_part):
            optimized_title = self._optimize_figi_title(main_part)

        # 3. Kostiumy dwuczęściowy - Góra/Top/Biustonosz
        elif self._is_top_swimsuit(main_part):
            optimized_title = self._optimize_top_title(main_part)

        if optimized_title:
            print(f"✅ Zoptymalizowano tytuł: {optimized_title}")
            return optimized_title
        else:
            print(f"⚠️ Nie można zoptymalizować tytułu: {current_title}")
            return current_title

    def _extract_model_name_for_title(self, text):
        """Wyciąga nazwę modelu dla tytułu produktu (zachowuje cechy, usuwa kolory)"""
        if "Model " not in text:
            return ""

            # Sprawdź czy GDZIEKOLWIEK w tytule są słowa "Bralet" lub "Kopa"
        product_types_to_move = []
        types_to_check = ["Bralet", "Kopa"]

        for product_type in types_to_check:
            if product_type in text:
                product_types_to_move.append(product_type)

        # Znajdź część po "Model "
        model_part = text.split("Model ", 1)[1]

        # Usuń końcówkę " - Lupo Line" jeśli istnieje
        if " - Lupo Line" in model_part:
            model_part = model_part.split(" - Lupo Line")[0]

        # Lista kolorów do usunięcia (z wariantami literówek)
        colors_to_remove = [
            # Kolory angielskie
            "Multicolor", "Multcolor",  # literówka bez "i"
            "Black", "White", "Red", "Blue", "Green", "Pink", "Coral",
            "Yellow", "Orange", "Purple", "Brown", "Gray", "Grey",
            # Kolory polskie
            "Turkus", "Czarny", "Biały", "Czerwony", "Niebieski", "Zielony",
            "Różowy", "Żółty", "Pomarańczowy", "Fioletowy", "Brązowy", "Szary"
        ]

        # Podziel na słowa i usuń tylko kolory
        words = model_part.split()
        filtered_words = []

        for i, word in enumerate(words):
            # WYJĄTEK: Jeśli "Coral" jest pierwszym słowem po "Model", to jest nazwa modelu, nie kolor!
            if word == "Coral" and i == 0:
                # Zachowaj "Coral" jako nazwę modelu
                filtered_words.append(word)
            elif word not in colors_to_remove:
                # Jeśli to typ produktu który ma być przeniesiony na koniec, nie dodawaj go tutaj
                if word in product_types_to_move:
                    continue  # Pomiń - zostanie dodany na końcu
                else:
                    filtered_words.append(word)

        # Dodaj typy produktów na końcu (jeśli były przed "Model")
        if product_types_to_move:
            filtered_words.extend(product_types_to_move)

        result = " ".join(filtered_words).strip()
        return result

    def _extract_model_name(self, text):
        """Wyciąga nazwę modelu dla serii (usuwa kolory, Big/Small, typy produktu)"""
        if "Model " not in text:
            return ""

        # Znajdź część po "Model "
        model_part = text.split("Model ", 1)[1]

        # Usuń końcówkę " - Lupo Line" jeśli istnieje
        if " - Lupo Line" in model_part:
            model_part = model_part.split(" - Lupo Line")[0]

        # Lista wszystkich elementów do usunięcia z nazwy serii
        elements_to_remove = [
            # Kolory angielskie (z wariantami literówek)
            "Multicolor", "Multcolor",  # literówka bez "i"
            "Black", "White", "Red", "Blue", "Green", "Pink", "Coral",
            "Yellow", "Orange", "Purple", "Brown", "Gray", "Grey",
            # Kolory polskie
            "Turkus", "Czarny", "Biały", "Czerwony", "Niebieski", "Zielony",
            "Różowy", "Żółty", "Pomarańczowy", "Fioletowy", "Brązowy", "Szary",
            # Rozmiary (usuwane z serii!)
            "Big", "Small",
            # Typy produktów
            "Kopa", "Bralet", "Push-up", "Push", "up", "Figi", "Biustonosz",
            "Top", "Bikini", "Kostium", "Jednoczęściowy", "Dwuczęściowy", "Szorty"
        ]

        # Podziel na słowa i usuń niepotrzebne elementy
        words = model_part.split()
        filtered_words = []

        for i, word in enumerate(words):
            # WYJĄTEK: Jeśli "Coral" jest pierwszym słowem po "Model", to jest nazwa modelu, nie kolor!
            if word == "Coral" and i == 0:
                # Zachowaj "Coral" jako nazwę modelu
                filtered_words.append(word)
            elif word not in elements_to_remove:
                filtered_words.append(word)

        result = " ".join(filtered_words).strip()

        # Jeśli nie zostało nic, zwróć pusty string
        if not result:
            return ""

        return result

    def _is_figi_swimsuit(self, text):
        """Sprawdza czy to strój kąpielowy - figi (z tolerancją na literówki)"""
        text_lower = text.lower()

        # Musi zawierać podstawowe słowa kluczowe
        if "kostium dwuczęściowy" not in text_lower and "kostium dwuczęściowy" not in text:
            return False

        # Sprawdź czy to figi lub szorty kąpielowe
        has_figi = "figi" in text_lower or "Figi" in text
        has_szorty = "szorty" in text_lower or "Szorty" in text

        if not has_figi and not has_szorty:
            return False

        # Sprawdź różne warianty "kąpielowe/kąpielowy"
        swimming_variants = [
            "kąpielowe", "kąpielowy", "Kąpielowe", "Kąpielowy", "KĄPIELOWE", "KĄPIELOWY",
            # bez polskich znaków
            "kapielowe", "kapielowy", "Kapielowe", "Kapielowy", "KAPIELOWE", "KAPIELOWY"
        ]

        has_swimming_word = any(
            variant in text for variant in swimming_variants)

        print(
            f"🔍 Sprawdzam figi/szorty: kostium={True}, figi={has_figi}, szorty={has_szorty}, kąpielowe={has_swimming_word}")
        return has_swimming_word

    def _is_szorty_swimsuit(self, text):
        """Sprawdza czy to szorty kąpielowe (osobny typ produktu)"""
        text_lower = text.lower()

        # Musi zawierać podstawowe słowa kluczowe
        if "kostium dwuczęściowy" not in text_lower and "kostium dwuczęściowy" not in text:
            return False

        # Musi zawierać "szorty"
        if "szorty" not in text_lower and "Szorty" not in text:
            return False

        # Sprawdź różne warianty "kąpielowe/kąpielowy"
        swimming_variants = [
            "kąpielowe", "kąpielowy", "Kąpielowe", "Kąpielowy", "KĄPIELOWE", "KĄPIELOWY",
            # bez polskich znaków
            "kapielowe", "kapielowy", "Kapielowe", "Kapielowy", "KAPIELOWE", "KAPIELOWY"
        ]

        has_swimming_word = any(
            variant in text for variant in swimming_variants)

        print(
            f"🔍 Sprawdzam szorty: kostium={True}, szorty={True}, kąpielowe={has_swimming_word}")
        return has_swimming_word

    def _is_top_swimsuit(self, text):
        """Sprawdza czy to strój kąpielowy - góra/biustonosz (z tolerancją na literówki)"""
        text_lower = text.lower()

        # Musi zawierać podstawowe słowa kluczowe
        if "kostium dwuczęściowy" not in text_lower and "kostium dwuczęściowy" not in text:
            return False

        # Sprawdź różne warianty górnej części
        top_variants = [
            "góra", "Góra", "top", "Top", "TOP",
            "biustonosz", "Biustonosz", "biustonosze", "Biustonosze"
        ]

        has_top_word = any(variant in text for variant in top_variants)

        print(
            f"🔍 Sprawdzam góra/biustonosz: kostium={True}, top={has_top_word}")
        return has_top_word

    def _optimize_szorty_title(self, main_part):
        """Optymalizuje tytuły szortów kąpielowych"""
        model_name = self._extract_model_name_for_title(main_part)
        if model_name:
            return f"Szorty kąpielowe {model_name}"
        return None

    def _optimize_figi_title(self, main_part):
        """Optymalizuje tytuły figów kąpielowych"""
        model_name = self._extract_model_name_for_title(main_part)
        if model_name:
            return f"Figi kąpielowe {model_name}"
        return None

    def _optimize_top_title(self, main_part):
        """Optymalizuje tytuły biustonoszy kąpielowych"""
        model_name = self._extract_model_name_for_title(main_part)
        if model_name:
            # Sprawdź typ biustonosza na podstawie nazwy modelu lub opisu
            if "Bralet" in model_name:
                # Usuń "Bralet" z nazwy modelu i dodaj jako typ
                clean_model = model_name.replace("Bralet", "").strip()
                return f"Biustonosz kąpielowy {clean_model} Bralet"
            elif "Kopa" in model_name:
                # Usuń "Kopa" z nazwy modelu i dodaj jako typ
                clean_model = model_name.replace("Kopa", "").strip()
                return f"Biustonosz kąpielowy {clean_model} Kopa"
            elif "Big" in model_name:
                # Zachowaj "Big" na końcu
                if not model_name.endswith("Big"):
                    clean_model = model_name.replace("Big", "").strip()
                    return f"Biustonosz kąpielowy {clean_model} Big"
                else:
                    return f"Biustonosz kąpielowy {model_name}"
            else:
                return f"Biustonosz kąpielowy {model_name}"
        return None

    def test_ai_optimization(self):
        """Testuje logikę AI optymalizacji dla różnych wzorców"""
        test_titles = [
            "Kostium dwuczęściowy Figi 1 Kąpielowe Model Mirage Big Multicolor - Lupo Line",
            "Kostium dwuczęściowy Figi 1 Kąpielowe Model Ocean Wave - Lupo Line",
            "Kostium dwuczęściowy Góra Model Coral Bralet - Lupo Line",
            "Kostium dwuczęściowy Góra Model Paradise Kopa - Lupo Line",
            "Kostium dwuczęściowy Góra Model Summer Big - Lupo Line",
            "Kostium dwuczęściowy Góra Model Sunset - Lupo Line"
        ]

        print("🧪 Testowanie AI optymalizacji dla kostiumów dwuczęściowych:")
        print("=" * 70)

        for title in test_titles:
            print(f"\n📝 Tytuł oryginalny:")
            print(f"   {title}")
            optimized = self.get_ai_optimized_title(title)
            print(f"🤖 Tytuł zoptymalizowany:")
            print(f"   {optimized}")
            print("-" * 50)

    def test_ai_description_optimization(self):
        """Testuje logikę AI optymalizacji opisów"""
        test_descriptions = [
            "Kostium dwuczęściowy figi wykonany z wysokiej jakości materiału. Idealny na plażę.",
            "Strój kąpielowy góra z funkcją push-up. Bardzo wygodny w noszeniu.",
            "Figi kąpielowe z regulacją na bokach . Dostępne w różnych kolorach .",
            "Biustonosz kąpielowy z miękkim wypełnieniem  ,  doskonały na urlop nad morzem.",
            "Dwuczęściowy kostium kąpielowy marki premium. Wykonany z elastycznego materiału."
        ]

        print("🧪 Testowanie AI optymalizacji opisów:")
        print("=" * 70)

        for desc in test_descriptions:
            print(f"\n📝 Opis oryginalny:")
            print(f"   {desc}")
            optimized = self.get_ai_optimized_description(
                desc, "Kostium dwuczęściowy Model Ocean - Lupo Line")
            print(f"🤖 Opis zoptymalizowany:")
            print(f"   {optimized}")
            print("-" * 50)

    def test_ai_short_description_optimization(self):
        """Testuje logikę wyciągania pierwszych zdań jako krótki opis"""
        test_long_descriptions = [
            "Figi kąpielowe wykonane z wysokiej jakości materiału elastycznego. Bardzo wygodne w noszeniu, idealne na plażę i basen. Dostępne w różnych rozmiarach.",
            "Biustonosz kąpielowy z miękkim wypełnieniem push-up. Zapewnia doskonałe wsparcie i komfort podczas kąpieli. Regulowane ramiączka dla lepszego dopasowania.",
            "Figi Mirage w poziome paski w ciepłych kolorach lata, z wyższym stanem, który optycznie spłaszcza brzuch, ukrywając niedoskonałości sylwetki.",
            "Wygodne figi kąpielowe idealne na lato",
            "Wysokiej jakości biustonosz kąpielowy z funkcją push-up zapewniającą doskonałe wsparcie i naturalny wygląd piersi podczas każdej aktywności nad wodą w okresie letnim",
            "Eleganckie figi z delikatnym wzorem w kwiaty",
            "Bardzo długi opis bez kropek który się ciągnie i ciągnie i nie ma końca i w końcu trzeba go będzie obciąć żeby zmieścił się w polu krótkiego opisu ale bez obcinania słów w połowie"
        ]

        print("🧪 Testowanie wyciągania pierwszych zdań jako krótki opis:")
        print("=" * 70)

        for long_desc in test_long_descriptions:
            print(f"\n📝 Długi opis:")
            print(f"   {long_desc}")
            short_desc = self.get_ai_short_description(
                long_desc, "Figi kąpielowe Ocean Wave - Lupo Line")
            print(f"📄 Krótki opis (pierwsze zdania):")
            print(f"   {short_desc}")
            print(f"📏 Długość: {len(short_desc)} znaków")
            print("-" * 50)

    def test_title_validation(self):
        """Testuje sprawdzanie czy tytuł już jest prawidłowy"""
        test_titles = [
            "Figi kąpielowe Mirage Big",  # ✅ prawidłowy
            "Biustonosz kąpielowy Triangle Push-Up",  # ✅ prawidłowy
            # ❌ nieprawidłowy
            "Kostium dwuczęściowy Figi 1 Kąpielowe Model Mirage Big Multicolor - Lupo Line",
            "FIGI KĄPIELOWE Wonder Classic",  # ✅ prawidłowy (wielkie litery)
            "Strój kąpielowy jednoczęściowy",  # 🤔 nieznany
            "",  # ❌ pusty
        ]

        print("🧪 Testowanie walidacji tytułów:")
        print("=" * 60)

        for title in test_titles:
            print(f"\n📝 Tytuł: '{title}'")
            is_valid = self._is_title_already_optimized(title)
            print(
                f"   Wynik: {'✅ Prawidłowy' if is_valid else '❌ Wymaga edycji'}")
            print("-" * 40)

    def edit_mpd_name_field(self, new_value=None, use_ai_optimization=True):
        """
        Edytuje pole mpd_name na stronie szczegółów produktu

        Args:
            new_value (str): Nowa wartość pola (jeśli None, używa AI)
            use_ai_optimization (bool): Czy używać AI do optymalizacji

        Returns:
            bool: True jeśli edycja się powiodła
        """
        try:
            driver = self.navigator.get_driver()

            if not driver:
                print("❌ Brak aktywnej sesji przeglądarki")
                return False

            # Sprawdź czy jesteśmy na stronie edycji produktu
            current_url = driver.current_url
            if "/change/" not in current_url:
                print("❌ Nie jesteśmy na stronie edycji produktu")
                return False

            # Znajdź pole mpd_name
            try:
                mpd_name_field = driver.find_element(By.ID, "mpd_name")
                print("✅ Znaleziono pole mpd_name")
            except Exception as e:
                print(f"❌ Nie można znaleźć pola mpd_name: {str(e)}")
                return False

            # Pobierz aktualną wartość
            current_value = mpd_name_field.get_attribute("value")
            print(f"📝 Aktualna wartość: {current_value}")

            # Sprawdź czy nazwa już jest prawidłowa
            if self._is_title_already_optimized(current_value):
                print("✅ Nazwa już jest prawidłowa - pomijam edycję")
                return True

            # Określ nową wartość
            if new_value:
                final_value = new_value
                print(f"🎯 Używam podanej wartości: {final_value}")
            elif use_ai_optimization:
                final_value = self.get_ai_optimized_title(current_value)
                print(f"🤖 AI zoptymalizował tytuł: {final_value}")
            else:
                print("❌ Brak nowej wartości do ustawienia")
                return False

            # Sprawdź czy wartość się zmieniła
            if current_value == final_value:
                print("ℹ️ Wartość jest już poprawna, nie ma co zmieniać")
                return True

            # Wyczyść pole i wprowadź nową wartość
            mpd_name_field.clear()
            mpd_name_field.send_keys(final_value)

            # Sprawdź czy wartość została ustawiona
            time.sleep(1)
            new_field_value = mpd_name_field.get_attribute("value")

            if new_field_value == final_value:
                print(f"✅ Pomyślnie zmieniono wartość na: {final_value}")
                return True
            else:
                print(
                    f"❌ Wartość nie została poprawnie ustawiona. Oczekiwano: {final_value}, Otrzymano: {new_field_value}")
                return False

        except Exception as e:
            print(f"❌ Błąd podczas edycji pola mpd_name: {str(e)}")
            return False

    def get_ai_optimized_description(self, current_description, product_title=None):
        """
        Używa AI do delikatnej modyfikacji opisu produktu

        Args:
            current_description (str): Aktualny opis produktu
            product_title (str): Tytuł produktu do kontekstu

        Returns:
            str: Zoptymalizowany opis
        """
        print(f"🔍 Analizuję opis przez OpenAI: {current_description[:100]}...")

        if not current_description or len(current_description.strip()) < 10:
            print("⚠️ Opis jest zbyt krótki lub pusty - nie modyfikuję")
            return current_description

        # Sprawdź czy OpenAI jest dostępne
        if not OPENAI_AVAILABLE:
            print("❌ OpenAI nie jest dostępne - używam podstawowej logiki")
            return self._basic_description_optimization(current_description, product_title)

        # Pobierz klucz API z zmiennych środowiskowych
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ Brak klucza OPENAI_API_KEY w .env.dev - używam podstawowej logiki")
            return self._basic_description_optimization(current_description, product_title)

        try:
            # Inicjalizuj klienta OpenAI
            client = OpenAI(api_key=api_key)

            # Przygotuj prompt dla AI
            context = f"Tytuł produktu: {product_title}" if product_title else "Brak tytułu"

            prompt = f"""Jesteś ekspertem od tekstów marketingowych dla kostiumów kąpielowych. 
Twoim zadaniem jest delikatnie poprawić opis produktu, zachowując jego oryginalny sens i długość.

{context}

Obecny opis:
"{current_description}"

Proszę o delikatne poprawki w następujących obszarach:
1. Terminologia: "kostium dwuczęściowy" → "figi kąpielowe" lub "biustonosz kąpielowy" (zależnie od kontekstu)
2. Spójność: "strój kąpielowy" → "kostium kąpielowy"
3. Interpunkcja i formatowanie
4. Poprawność językowa

WAŻNE: 
- Zachowaj oryginalną długość i styl opisu
- Nie dodawaj zbędnych ozdobników czy przesadnych przymiotników
- Zwróć TYLKO poprawiony opis bez dodatkowych komentarzy
- Jeśli opis jest już dobry, zwróć go bez zmian"""

            # Wywołaj OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Jesteś ekspertem od tekstów marketingowych kostiumów kąpielowych. Wykonujesz delikatne poprawki tekstów."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )

            optimized_description = response.choices[0].message.content.strip()

            # Usuń ewentualne cudzysłowy z odpowiedzi AI
            if optimized_description.startswith('"') and optimized_description.endswith('"'):
                optimized_description = optimized_description[1:-1]

            # Sprawdź czy coś się zmieniło
            if optimized_description != current_description:
                print(f"✅ OpenAI zoptymalizował opis")
                print(
                    f"📝 Długość: {len(current_description)} → {len(optimized_description)} znaków")
            else:
                print("ℹ️ OpenAI uznał że opis nie wymaga modyfikacji")

            return optimized_description

        except Exception as e:
            print(f"❌ Błąd OpenAI API: {str(e)}")
            print("🔄 Używam podstawowej logiki jako fallback")
            return self._basic_description_optimization(current_description, product_title)

    def _basic_description_optimization(self, description, product_title=None):
        """Podstawowa logika optymalizacji jako fallback"""
        optimized_description = description.strip()

        # Podstawowe poprawki
        if "kostium dwuczęściowy" in description.lower():
            if "figi" in description.lower():
                optimized_description = optimized_description.replace(
                    "kostium dwuczęściowy", "figi kąpielowe")
                optimized_description = optimized_description.replace(
                    "Kostium dwuczęściowy", "Figi kąpielowe")
            elif "góra" in description.lower() or "biustonosz" in description.lower():
                optimized_description = optimized_description.replace(
                    "kostium dwuczęściowy", "biustonosz kąpielowy")
                optimized_description = optimized_description.replace(
                    "Kostium dwuczęściowy", "Biustonosz kąpielowy")

        # Popraw interpunkcję
        optimized_description = optimized_description.replace(" .", ".")
        optimized_description = optimized_description.replace(" ,", ",")
        optimized_description = optimized_description.replace("  ", " ")

        print("✅ Użyto podstawowej logiki optymalizacji")
        return optimized_description

    def edit_mpd_description_field(self, new_value=None, use_ai_optimization=True):
        """
        Edytuje pole mpd_description na stronie szczegółów produktu

        Args:
            new_value (str): Nowa wartość pola (jeśli None, używa AI)
            use_ai_optimization (bool): Czy używać AI do optymalizacji

        Returns:
            bool: True jeśli edycja się powiodła
        """
        try:
            driver = self.navigator.get_driver()

            if not driver:
                print("❌ Brak aktywnej sesji przeglądarki")
                return False

            # Sprawdź czy jesteśmy na stronie edycji produktu
            current_url = driver.current_url
            if "/change/" not in current_url:
                print("❌ Nie jesteśmy na stronie edycji produktu")
                return False

            # Znajdź pole mpd_description
            try:
                mpd_description_field = driver.find_element(
                    By.ID, "mpd_description")
                print("✅ Znaleziono pole mpd_description")
            except Exception as e:
                print(f"❌ Nie można znaleźć pola mpd_description: {str(e)}")
                return False

            # Pobierz aktualną wartość
            current_value = mpd_description_field.get_attribute("value")
            print(f"📝 Aktualny opis: {current_value[:100]}...")

            # Pobierz tytuł produktu dla kontekstu
            product_title = None
            try:
                title_field = driver.find_element(By.ID, "mpd_name")
                product_title = title_field.get_attribute("value")
            except Exception:
                pass

            # Określ nową wartość
            if new_value:
                final_value = new_value
                print(f"🎯 Używam podanej wartości")
            elif use_ai_optimization:
                final_value = self.get_ai_optimized_description(
                    current_value, product_title)
                print(f"🤖 AI zmodyfikował opis")
            else:
                print("❌ Brak nowej wartości do ustawienia")
                return False

            # Sprawdź czy wartość się zmieniła
            if current_value == final_value:
                print("ℹ️ Opis jest już poprawny, nie ma co zmieniać")
                return True

            # Wyczyść pole i wprowadź nową wartość
            mpd_description_field.clear()
            mpd_description_field.send_keys(final_value)

            # Sprawdź czy wartość została ustawiona
            time.sleep(1)
            new_field_value = mpd_description_field.get_attribute("value")

            if new_field_value == final_value:
                print(f"✅ Pomyślnie zmieniono opis")
                return True
            else:
                print(f"❌ Opis nie został poprawnie ustawiony")
                return False

        except Exception as e:
            print(f"❌ Błąd podczas edycji pola mpd_description: {str(e)}")
            return False

    def get_ai_short_description(self, long_description, product_title=None):
        """
        Tworzy krótki opis z długiego - pierwsze lub dwa pierwsze zdania

        Args:
            long_description (str): Długi opis produktu
            product_title (str): Tytuł produktu do kontekstu (nieużywane)

        Returns:
            str: Krótki opis (pierwsze 1-2 zdania)
        """
        print(
            f"🔍 Tworzę krótki opis z pierwszych zdań: {long_description[:100]}...")

        if not long_description or len(long_description.strip()) < 20:
            print("⚠️ Długi opis jest zbyt krótki - nie można utworzyć krótkiego")
            return long_description

        return self._extract_first_sentences(long_description)

    def extract_mpd_attributes_from_description(self, description):
        """
        Wyciąga atrybuty MPD z opisu produktu

        Args:
            description (str): Opis produktu

        Returns:
            list: Lista ID atrybutów znalezionych w opisie
        """
        if not description:
            return []

        # Słownik mapujący atrybuty MPD z ich ID
        mpd_attributes = {
            1: ["bawełniany klin", "bawełna", "klin"],
            3: ["bezszwowe", "bez szwów", "bezszwowy"],
            4: ["bezuciskowe", "bez ucisku", "bezuciskowy"],
            2: ["biustonosz bez fiszbin", "bez fiszbin", "bez fiszbina"],
            5: ["duży biust", "duże biusty", "plus size", "większe rozmiary"],
            6: ["gładkie", "gładki", "jednolite"],
            7: ["gładkie miseczki", "gładka miseczka"],
            8: ["korygujące", "korygująca", "modelujące", "kształtujące"],
            27: ["miękkie miseczki", "miękka miseczka", "soft cup"],
            9: ["na fiszbinach", "z fiszbinami", "fiszbiny", "na kościach", "usztywniony fiszbinami"],
            10: ["na kopie", "na kopię", "podkopie"],
            23: ["nieodpinane ramiączka", "stałe ramiączka", "nieodpinane"],
            11: ["niewidoczne wzmocnienie", "push up", "push-up"],
            28: ["niski stan", "low rise", "nisko osadzone", "z niższym stanem", "niższym stanem", "z niskim stanem", "niskim stanem"],
            12: ["odpinane ramiączka", "odpinane"],
            13: ["płaski szew", "płaskie szwy"],
            14: ["przeciwżylakowe", "przeciwżylakowa", "uciskowe", "kompresyjne"],
            26: ["regulowane", "regulacja", "regulowany", "ściągane", "ściągany", "możesz regulować", "regulować", "ściągane sznureczki", "sznureczki", "z regulacją", "wiązane na troczki", "wiązane troczki", "umożliwiają regulację", "umożliwia regulację"],
            15: ["regulowane ramiączka", "regulacja ramiączek", "ramiączka regulowane", "ramiączka z regulacją"],
            16: ["sportowy", "sportowe", "do sportu", "aktywność"],
            29: ["wiązane na szyi", "wiązany na szyi", "wiązanie na szyi", "halter"],
            17: ["wielofunkcyjne", "wielofunkcyjna", "multiway"],
            18: ["wyjmowane wkładki", "wyjmowalne wkładki", "padding"],
            22: ["wyściełane miseczki", "wyściełana miseczka", "z wkładkami"],
            25: ["wyższy stan", "wyższym stanem", "high waist", "wysoko osadzone", "wysokim stanem", "z wyższym stanem", "z wysokim stanem"],
            19: ["wzmocnione palce", "wzmocnienia w palcach", "reinforced toe"],
            20: ["wzorzyste", "wzory", "z wzorem", "nadruk"],
            21: ["zapinane z przodu", "zapięcie z przodu", "front closure", "zapinany z przodu"],
            24: ["zapinane z tyłu", "zapięcie z tyłu", "zapięciem z tyłu", "back closure", "zapinany na plecach", "zapinane na plecach", "na plecach"],
            30: ["usztywniane miseczki", "usztywniana miseczka", "usztywnianymi miseczkami", "z usztywnieniem", "sztywne miseczki"]
        }

        description_lower = description.lower()
        found_attributes = []

        print(f"🔍 Szukam atrybutów w opisie: {description[:100]}...")

        # Sprawdzaj atrybuty w kolejności: bardziej specyficzne (ramiączka) przed ogólnymi
        specific_first_order = [15, 12, 23]  # Atrybuty ramiączek najpierw
        remaining_attrs = [attr_id for attr_id in mpd_attributes.keys(
        ) if attr_id not in specific_first_order]
        ordered_attrs = specific_first_order + remaining_attrs

        # Flagi dla wykluczania ogólnych atrybutów gdy znaleziono specyficzne
        found_specific_straps = False

        for attr_id in ordered_attrs:
            if attr_id in mpd_attributes:
                keywords = mpd_attributes[attr_id]
                # Sortuj słowa kluczowe według długości (najdłuższe pierwsze)
                sorted_keywords = sorted(keywords, key=len, reverse=True)

                for keyword in sorted_keywords:
                    if keyword.lower() in description_lower:
                        found_attributes.append(attr_id)
                        print(
                            f"✅ Znaleziono atrybut ID {attr_id}: '{keyword}'")

                        # Oznacz że znaleziono specyficzny atrybut ramiączek
                        if attr_id in [12, 15, 23]:  # ramiączka
                            found_specific_straps = True

                        break  # Jeśli znaleziono jeden keyword dla tego atrybutu, nie szukaj dalej

        # Wykluczaj kolizje między podobnymi atrybutami ramiączek
        if 12 in found_attributes and 23 in found_attributes:
            # Sprawdź czy opis zawiera "nieodpinane" (bardziej specyficzne)
            if "nieodpinane" in description_lower:
                found_attributes.remove(12)  # Usuń ogólne "odpinane"
                print(
                    f"🔧 Usunięto ogólny atrybut 'odpinane' (ID 12) bo znaleziono specyficzny 'nieodpinane' (ID 23)")

        # Usuń ogólne "regulowane" (ID 26) TYLKO jeśli koliduje ze specyficznymi ramiączkami
        if 15 in found_attributes and 26 in found_attributes:
            # Sprawdź czy "regulowane" w opisie odnosi się TYLKO do ramiączek
            straps_keywords = ["ramiączka regulowane", "regulowane ramiączka",
                               "ramiączka z regulacją", "regulacja ramiączek"]
            has_straps_specific = any(
                keyword in description_lower for keyword in straps_keywords)

            # Sprawdź czy są inne "regulowane" elementy (sznureczki itp.)
            other_regulated_keywords = [
                "ściągane sznureczki", "sznureczki", "regulowane elementy", "regulowane części"]
            has_other_regulated = any(
                keyword in description_lower for keyword in other_regulated_keywords)

            # Usuń ogólne "regulowane" TYLKO jeśli nie ma innych regulowanych elementów
            if has_straps_specific and not has_other_regulated:
                found_attributes.remove(26)
                print(
                    f"🔧 Usunięto ogólny atrybut 'regulowane' (ID 26) bo odnosi się tylko do ramiączek (ID 15)")

        if found_attributes:
            print(f"📋 Znalezione atrybuty: {found_attributes}")
        else:
            print("❌ Nie znaleziono żadnych atrybutów w opisie")

        return list(set(found_attributes))  # Usuń duplikaty

    def set_mpd_attributes(self, attribute_ids):
        """
        Ustawia atrybuty MPD w formularzu

        Args:
            attribute_ids (list): Lista ID atrybutów do zaznaczenia

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            # Znajdź element select dla atrybutów MPD
            mpd_attributes_select = driver.find_element(
                By.ID, "mpd_attributes")

            # Wyczyść poprzednie zaznaczenia
            options = mpd_attributes_select.find_elements(
                By.TAG_NAME, "option")
            for option in options:
                if option.is_selected():
                    option.click()

            # Zaznacz nowe atrybuty
            selected_count = 0
            for attr_id in attribute_ids:
                try:
                    option = mpd_attributes_select.find_element(
                        By.CSS_SELECTOR, f'option[value="{attr_id}"]')
                    if not option.is_selected():
                        option.click()
                        selected_count += 1
                        print(
                            f"✅ Zaznaczono atrybut ID {attr_id}: {option.text.strip()}")
                except Exception as e:
                    print(
                        f"⚠️ Nie udało się zaznaczyć atrybutu ID {attr_id}: {str(e)}")

            print(f"📋 Zaznaczono {selected_count} atrybutów")
            return True

        except Exception as e:
            print(f"❌ Błąd podczas ustawiania atrybutów MPD: {str(e)}")
            return False

    def extract_producer_color_from_title(self, product_title):
        """
        Wyciąga kolor producenta z tytułu produktu

        Args:
            product_title (str): Tytuł produktu

        Returns:
            str: Kolor producenta lub None jeśli nie znaleziono
        """
        if not product_title:
            return None

        # Lista popularnych kolorów w różnych językach
        common_colors = [
            # Podstawowe kolory
            "multicolor", "multi", "black", "white", "red", "blue", "green", "yellow",
            "pink", "purple", "orange", "brown", "grey", "gray", "beige", "navy",
            # Polskie nazwy kolorów
            "czarny", "biały", "czerwony", "niebieski", "zielony", "żółty", "różowy",
            "fioletowy", "pomarańczowy", "brązowy", "szary", "beżowy", "granatowy",
            # Odcienie
            "nude", "coral", "mint", "lime", "teal", "aqua", "maroon", "olive",
            "silver", "gold", "bronze", "cream", "ivory", "khaki", "turquoise",
            # Wzory mogące być kolorami
            "leopard", "zebra", "floral", "tropical", "animal", "print",
            # Specjalne określenia
            "neon", "pastel", "bright", "dark", "light", "deep", "pale",
            # Kombinacje
            "mix", "combo", "blend", "stripe", "dot", "solid"
        ]

        title_lower = product_title.lower()

        # Szukaj kolorów od końca tytułu (przed marką)
        # Usuń markę z końca jeśli jest
        title_without_brand = title_lower
        brands = ["lupo line", "lupo", "triumph", "change", "anita"]
        for brand in brands:
            if title_without_brand.endswith(f" - {brand}"):
                title_without_brand = title_without_brand[:-len(f" - {brand}")]
            elif title_without_brand.endswith(f" {brand}"):
                title_without_brand = title_without_brand[:-len(f" {brand}")]

        print(f"🎨 Szukam koloru w tytule: {product_title}")
        print(f"📝 Tytuł bez marki: {title_without_brand}")

        # Znajdź ostatni kolor w tytule
        found_colors = []
        words = title_without_brand.split()

        for i, word in enumerate(words):
            # Sprawdź czy słowo lub kombinacja słów to kolor
            for color in common_colors:
                color_words = color.split()
                if len(color_words) == 1:
                    if word == color:
                        found_colors.append((i, color))
                else:
                    # Sprawdź kombinacje słów
                    if i + len(color_words) <= len(words):
                        phrase = " ".join(words[i:i+len(color_words)])
                        if phrase == color:
                            found_colors.append((i, color))

        if found_colors:
            # Weź ostatni znaleziony kolor (najbliżej końca)
            last_color = max(found_colors, key=lambda x: x[0])[1]
            # Skapitalizuj pierwszą literę
            formatted_color = last_color.capitalize()
            print(f"✅ Znaleziony kolor: '{formatted_color}'")
            return formatted_color
        else:
            print("❌ Nie znaleziono koloru w tytule")
            return None

    def set_producer_color(self, color_name):
        """
        Ustawia kolor producenta w polu producer_color_name

        Args:
            color_name (str): Nazwa koloru do ustawienia

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            # Znajdź pole koloru producenta
            color_field = driver.find_element(By.ID, "producer_color_name")

            # Wyczyść pole i wpisz nowy kolor
            color_field.clear()
            color_field.send_keys(color_name)

            print(f"✅ Ustawiono kolor producenta: '{color_name}'")
            return True

        except Exception as e:
            print(f"❌ Błąd podczas ustawiania koloru producenta: {str(e)}")
            return False

    def set_mpd_size_category(self, category="bielizna"):
        """
        Ustawia kategorię rozmiaru MPD

        Args:
            category (str): Kategoria rozmiaru (domyślnie "bielizna")

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            print(f"🔍 Szukam pola kategorii rozmiaru: mpd_size_category")

            # Znajdź pole kategorii rozmiaru
            size_category_field = driver.find_element(
                By.ID, "mpd_size_category")

            # Sprawdź typ elementu
            element_tag = size_category_field.tag_name.lower()
            print(f"📋 Znaleziono element: {element_tag}")

            if element_tag == "select":
                # To jest dropdown - użyj Select
                select = Select(size_category_field)

                print(f"📝 Dostępne opcje w dropdown:")
                for i, option in enumerate(select.options):
                    option_text = option.text.strip()
                    option_value = option.get_attribute('value')
                    print(
                        f"   {i+1}. '{option_text}' (value: '{option_value}')")

                # Spróbuj wybrać opcję po tekście
                try:
                    select.select_by_visible_text(category)
                    print(f"✅ Wybrano kategorię po tekście: '{category}'")
                    return True
                except:
                    # Spróbuj wybrać opcję po wartości
                    try:
                        select.select_by_value(category)
                        print(f"✅ Wybrano kategorię po wartości: '{category}'")
                        return True
                    except:
                        # Spróbuj znaleźć częściowe dopasowanie
                        for option in select.options:
                            option_text = option.text.strip().lower()
                            if category.lower() in option_text or option_text in category.lower():
                                select.select_by_visible_text(option.text)
                                print(
                                    f"✅ Wybrano kategorię (częściowe dopasowanie): '{option.text}'")
                                return True

                        print(
                            f"❌ Nie znaleziono opcji '{category}' w dropdown")
                        return False

            elif element_tag == "input":
                # To jest pole tekstowe
                input_type = size_category_field.get_attribute('type')
                print(f"📝 Typ input: {input_type}")

                if input_type in ['text', 'search']:
                    # Zwykłe pole tekstowe
                    size_category_field.clear()
                    size_category_field.send_keys(category)
                    print(f"✅ Wpisano kategorię w pole tekstowe: '{category}'")
                    return True
                else:
                    print(f"⚠️ Nieobsługiwany typ input: {input_type}")
                    return False
            else:
                print(f"⚠️ Nieznany typ elementu: {element_tag}")
                return False

        except Exception as e:
            print(f"❌ Błąd podczas ustawiania kategorii rozmiaru: {str(e)}")
            return False

    def get_main_color_from_readonly_field(self):
        """
        Pobiera główny kolor z pola readonly w formularzu

        Returns:
            str: Główny kolor lub None jeśli nie znaleziono
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            # Znajdź sekcję z kolorem głównym
            color_section = driver.find_element(
                By.CSS_SELECTOR, "div.form-row.field-color")

            # Znajdź element readonly z kolorem
            readonly_element = color_section.find_element(
                By.CSS_SELECTOR, "div.readonly")
            main_color = readonly_element.text.strip()

            print(f"🎨 Odczytano główny kolor z pola readonly: '{main_color}'")
            return main_color

        except Exception as e:
            print(f"❌ Błąd podczas odczytywania głównego koloru: {str(e)}")
            return None

    def get_available_main_colors(self):
        """
        Pobiera listę dostępnych głównych kolorów z formularza

        Returns:
            list: Lista dostępnych kolorów
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            # Znajdź sekcję z kolorami głównymi
            color_section = driver.find_element(
                By.CSS_SELECTOR, "#products_form > div > fieldset > div.form-row.field-color")

            # Pobierz wszystkie opcje kolorów (labels lub options)
            color_options = color_section.find_elements(By.TAG_NAME, "label")
            if not color_options:
                color_options = color_section.find_elements(
                    By.TAG_NAME, "option")

            colors = []
            for option in color_options:
                color_text = option.text.strip()
                if color_text and color_text not in colors:
                    colors.append(color_text)

            print(f"📋 Dostępne główne kolory: {len(colors)} opcji")
            for i, color in enumerate(colors[:10]):  # Pokaż pierwsze 10
                print(f"   {i+1}. {color}")
            if len(colors) > 10:
                print(f"   ... i {len(colors) - 10} więcej")

            return colors

        except Exception as e:
            print(f"❌ Błąd podczas pobierania listy kolorów: {str(e)}")
            return []

    def select_main_color_from_dropdown(self):
        """
        Wybiera główny kolor w dropdown na podstawie koloru z pola readonly

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            # 1. Odczytaj główny kolor z pola readonly
            main_color = self.get_main_color_from_readonly_field()
            if not main_color:
                print("❌ Nie udało się odczytać głównego koloru z pola readonly")
                return False

            print(f"🎯 Będę szukać koloru '{main_color}' w dropdown")

            # 2. Znajdź dropdown/select z kolorami
            driver = self.navigator.login_agent.get_driver()

            # Spróbuj znaleźć dropdown w różnych lokalizacjach
            dropdown_selectors = [
                "select[name*='color']",
                "select[id*='color']",
                "#products_form select",
                "div.form-row select",
                "select"
            ]

            color_dropdown = None
            for selector in dropdown_selectors:
                try:
                    dropdowns = driver.find_elements(By.CSS_SELECTOR, selector)
                    for dropdown in dropdowns:
                        # Sprawdź czy ten dropdown ma opcje kolorów
                        options = dropdown.find_elements(By.TAG_NAME, "option")
                        if len(options) > 1:  # Ma więcej niż pustą opcję
                            color_dropdown = dropdown
                            print(f"✅ Znaleziono dropdown kolorów: {selector}")
                            break
                    if color_dropdown:
                        break
                except:
                    continue

            if not color_dropdown:
                print("❌ Nie znaleziono dropdown z kolorami")
                return False

            # 3. Wybierz odpowiednią opcję z dropdown
            select = Select(color_dropdown)

            print(f"📝 Dostępne opcje w dropdown kolorów:")
            for i, option in enumerate(select.options):
                option_text = option.text.strip()
                option_value = option.get_attribute('value')
                print(f"   {i+1}. '{option_text}' (value: '{option_value}')")

            # Spróbuj wybrać opcję po dokładnym tekście
            try:
                select.select_by_visible_text(main_color)
                print(f"✅ Wybrano kolor po dokładnym tekście: '{main_color}'")
                return True
            except:
                pass

            # Spróbuj wybrać opcję po wartości
            try:
                select.select_by_value(main_color)
                print(f"✅ Wybrano kolor po wartości: '{main_color}'")
                return True
            except:
                pass

            # Spróbuj częściowe dopasowanie
            main_color_lower = main_color.lower()
            for option in select.options:
                option_text = option.text.strip().lower()
                option_value = option.get_attribute('value').lower()

                # Sprawdź czy main_color zawiera się w opcji lub na odwrót
                if (main_color_lower in option_text or option_text in main_color_lower or
                        main_color_lower in option_value or option_value in main_color_lower):
                    try:
                        select.select_by_visible_text(option.text)
                        print(
                            f"✅ Wybrano kolor (częściowe dopasowanie): '{option.text.strip()}'")
                        return True
                    except:
                        continue

            print(
                f"❌ Nie znaleziono pasującej opcji dla koloru: '{main_color}'")
            return False

        except Exception as e:
            print(f"❌ Błąd podczas wybierania głównego koloru: {str(e)}")
            return False

    def extract_model_name_from_title(self, product_title):
        """
        Wyciąga nazwę modelu z tytułu produktu

        Args:
            product_title (str): Tytuł produktu

        Returns:
            str: Nazwa modelu lub None jeśli nie znaleziono
        """
        if not product_title:
            return None

        print(f"🔍 Wyciągam nazwę modelu z tytułu: {product_title}")

        # Usuń markę z końca
        title_without_brand = product_title
        brands = ["- Lupo Line", "- Triumph", "- Change", "- Anita"]
        for brand in brands:
            if title_without_brand.endswith(brand):
                title_without_brand = title_without_brand[:-len(brand)].strip()
                break

        print(f"📝 Tytuł bez marki: {title_without_brand}")

        # Szukaj wzorca "Model {nazwa}" lub podobnego
        import re

        # Wzorce do wyszukiwania nazwy modelu
        patterns = [
            # "Model Mirage" lub "Model Mirage Big"
            r"Model\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)",
            r"model\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)",  # "model mirage"
            # nazwa przed Big/Small itp
            r"\s([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:Big|Small|Classic|Premium|Deluxe)",
            # nazwa przed kolorem
            r"\s([A-Z][a-z]+)\s+(?:Multicolor|Black|White|Red|Blue|Green|Pink)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, title_without_brand, re.IGNORECASE)
            if matches:
                model_name = matches[0].strip()
                # Usuń słowa które nie są nazwami modeli
                exclude_words = ["kostium", "dwuczęściowy", "figi",
                                 "kąpielowe", "biustonosz", "big", "small"]
                model_words = model_name.split()
                filtered_words = [
                    word for word in model_words if word.lower() not in exclude_words]

                if filtered_words:
                    final_model_name = " ".join(filtered_words)
                    print(
                        f"✅ Znaleziono nazwę modelu: '{final_model_name}' (wzorzec: {pattern})")
                    return final_model_name

        # Fallback - spróbuj znaleźć wielką literę po słowie "Model"
        model_index = title_without_brand.lower().find("model")
        if model_index != -1:
            rest_of_title = title_without_brand[model_index + 5:].strip()
            words = rest_of_title.split()
            for word in words:
                if word and word[0].isupper() and len(word) > 2:
                    if word.lower() not in ["big", "small", "multicolor", "black", "white"]:
                        print(
                            f"✅ Znaleziono nazwę modelu (fallback): '{word}'")
                        return word

        print("❌ Nie znaleziono nazwy modelu w tytule")
        return None

    def create_series_name(self, model_name):
        """
        Tworzy nazwę serii według wzoru: "strój kąpielowy {nazwa modelu} - Lupo Line"

        Args:
            model_name (str): Nazwa modelu

        Returns:
            str: Nazwa serii
        """
        if not model_name:
            return "strój kąpielowy - Lupo Line"

        series_name = f"strój kąpielowy {model_name} - Lupo Line"
        print(f"📝 Utworzono nazwę serii: '{series_name}'")
        return series_name

    def set_series_name(self, series_name):
        """
        Ustawia nazwę serii w polu series_name

        Args:
            series_name (str): Nazwa serii do ustawienia

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            # Znajdź pole nazwy serii
            series_field = driver.find_element(By.ID, "series_name")

            # Wyczyść pole i wpisz nazwę serii
            series_field.clear()
            series_field.send_keys(series_name)

            print(f"✅ Ustawiono nazwę serii: '{series_name}'")
            return True

        except Exception as e:
            print(f"❌ Błąd podczas ustawiania nazwy serii: {str(e)}")
            return False

    def auto_detect_and_set_series_name(self):
        """
        Automatycznie wykrywa nazwę modelu z tytułu i tworzy nazwę serii

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            # Pobierz tytuł produktu z nagłówka h2
            title_element = driver.find_element(By.TAG_NAME, "h2")
            product_title = title_element.text.strip()

            if not product_title:
                print("⚠️ Nie znaleziono tytułu produktu")
                return False

            # Wykryj nazwę modelu z tytułu (dla serii - bez kolorów!)
            model_name = self._extract_model_name(product_title)

            # Utwórz nazwę serii
            series_name = self.create_series_name(model_name)

            # Ustaw nazwę serii w polu
            return self.set_series_name(series_name)

        except Exception as e:
            print(
                f"❌ Błąd podczas automatycznego ustawiania nazwy serii: {str(e)}")
            return False

    def detect_product_type_from_title(self, product_title):
        """
        Wykrywa typ produktu z tytułu

        Args:
            product_title (str): Tytuł produktu

        Returns:
            str: Typ produktu lub None jeśli nie wykryto
        """
        if not product_title:
            return None

        title_lower = product_title.lower()
        print(f"🔍 Wykrywam typ produktu z tytułu: {product_title}")

        # Najpierw sprawdź konkretne części stroju kąpielowego
        specific_parts = {
            "figi": "figi",
            "stringi": "figi",
            "szorty kąpielowe": "szorty",  # Szorty Kąpielowe to osobny typ!
            "szorty": "szorty",
            "biustonosz": "biustonosze",
            "stanik": "biustonosze",
            "top": "biustonosze"
        }

        # Sprawdź konkretne części (mają priorytet nad ogólnymi określeniami)
        for keyword, product_type in specific_parts.items():
            if keyword in title_lower:
                print(
                    f"✅ Wykryto konkretną część: '{product_type}' (słowo kluczowe: '{keyword}')")
                return product_type

        # Jeśli nie znaleziono konkretnych części, sprawdź ogólne typy
        general_types = {
            "dwuczęściowy": "dwuczęściowe",  # Fallback jeśli nie ma konkretnych części
            "kostium dwuczęściowy": "dwuczęściowe",
            "bikini": "dwuczęściowe",
            "jednoczęściowy": "jednoczęściowe",
            "kostium jednoczęściowy": "jednoczęściowe",
            "kombinezon": "kombinezony",
            "pareo": "pareo",
            "spódniczka": "spódniczki",
            "sukienka": "sukienki",
            "tankini": "tankini",
            "tunika": "tuniki"
        }

        # Sprawdź ogólne typy produktów
        for keyword, product_type in general_types.items():
            if keyword in title_lower:
                print(
                    f"✅ Wykryto typ produktu: '{product_type}' (słowo kluczowe: '{keyword}')")
                return product_type

        print("❌ Nie wykryto typu produktu")
        return None

    def get_path_id_for_product_type(self, product_type):
        """
        Zwraca ID ścieżki dla danego typu produktu

        Args:
            product_type (str): Typ produktu

        Returns:
            int: ID ścieżki lub None jeśli nie znaleziono
        """
        # Mapowanie typów produktów na ID ścieżek
        path_mapping = {
            # Dwuczęściowe (Moda damska\Bielizna\Stroje kąpielowe\Dwuczęściowe)
            "dwuczęściowe": 5,
            # Biustonosze | Topy (Moda damska\Bielizna\Stroje kąpielowe\Biustonosze | Topy)
            "biustonosze": 4,
            # Figi | Stringi | Szorty (Moda damska\Bielizna\Stroje kąpielowe\Figi | Stringi | Szorty)
            "figi": 6,
            "szorty": 6,  # Szorty też w kategorii "Figi | Stringi | Szorty"
            # Jednoczęściowe (Moda damska\Bielizna\Stroje kąpielowe\Jednoczęściowe)
            "jednoczęściowe": 7,
            # Kombinezony (Moda damska\Bielizna\Stroje kąpielowe\Kombinezony)
            "kombinezony": 8,
            # Pareo (Moda damska\Bielizna\Stroje kąpielowe\Pareo)
            "pareo": 9,
            # Spódniczki plażowe (Moda damska\Bielizna\Stroje kąpielowe\Spódniczki plażowe)
            "spódniczki": 10,
            # Sukienki plażowe (Moda damska\Bielizna\Stroje kąpielowe\Sukienki plażowe)
            "sukienki": 11,
            # Tankini (Moda damska\Bielizna\Stroje kąpielowe\Tankini)
            "tankini": 12,
            # Tuniki (Moda damska\Bielizna\Stroje kąpielowe\Tuniki)
            "tuniki": 13
        }

        path_id = path_mapping.get(product_type)
        if path_id:
            print(f"📍 Znaleziono ID ścieżki dla '{product_type}': {path_id}")
        else:
            print(f"❌ Nie znaleziono ID ścieżki dla '{product_type}'")

        return path_id

    def set_mpd_paths(self, path_ids):
        """
        Ustawia ścieżki MPD w select multiple

        Args:
            path_ids (list): Lista ID ścieżek do zaznaczenia

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            # Znajdź select z ścieżkami
            paths_select = driver.find_element(By.ID, "mpd_paths")

            print(f"🗂️ Dostępne ścieżki w select:")
            options = paths_select.find_elements(By.TAG_NAME, "option")
            for option in options:
                option_value = option.get_attribute('value')
                option_text = option.text.strip()
                is_selected = option.is_selected()
                status = "✓" if is_selected else " "
                print(f"   [{status}] ID {option_value}: {option_text}")

            # Wyczyść poprzednie zaznaczenia
            for option in options:
                if option.is_selected():
                    option.click()
                    print(f"❌ Odznaczono: {option.text.strip()}")

            # Zaznacz nowe ścieżki
            selected_count = 0
            for path_id in path_ids:
                try:
                    option = paths_select.find_element(
                        By.CSS_SELECTOR, f'option[value="{path_id}"]')
                    if not option.is_selected():
                        option.click()
                        selected_count += 1
                        print(
                            f"✅ Zaznaczono ścieżkę ID {path_id}: {option.text.strip()}")
                except Exception as e:
                    print(
                        f"⚠️ Nie udało się zaznaczyć ścieżki ID {path_id}: {str(e)}")

            print(f"📋 Zaznaczono {selected_count} ścieżek")
            return selected_count > 0

        except Exception as e:
            print(f"❌ Błąd podczas ustawiania ścieżek MPD: {str(e)}")
            return False

    def auto_detect_and_set_mpd_paths(self):
        """
        Automatycznie wykrywa typ produktu i ustawia odpowiednie ścieżki

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            # Pobierz tytuł produktu z nagłówka h2
            title_element = driver.find_element(By.TAG_NAME, "h2")
            product_title = title_element.text.strip()

            if not product_title:
                print("⚠️ Nie znaleziono tytułu produktu")
                return False

            # Wykryj typ produktu z tytułu
            product_type = self.detect_product_type_from_title(product_title)

            if not product_type:
                print("❌ Nie wykryto typu produktu - nie można ustawić ścieżek")
                return False

            # Znajdź ID ścieżki dla tego typu produktu
            path_id = self.get_path_id_for_product_type(product_type)

            if not path_id:
                print("❌ Nie znaleziono ID ścieżki dla wykrytego typu produktu")
                return False

            # Ustaw tylko konkretną ścieżkę końcową (nie dodajemy głównej kategorii)
            path_ids = [path_id]
            return self.set_mpd_paths(path_ids)

        except Exception as e:
            print(
                f"❌ Błąd podczas automatycznego ustawiania ścieżek: {str(e)}")
            return False

    def set_unit(self, unit_name="szt."):
        """
        Ustawia jednostkę miary w select unit_id

        Args:
            unit_name (str): Nazwa jednostki (domyślnie "szt.")

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            print(f"📏 Ustawiam jednostkę: '{unit_name}'")

            # Znajdź select z jednostkami
            unit_select = driver.find_element(By.ID, "unit_id")

            # Wyświetl dostępne opcje
            print(f"📋 Dostępne jednostki:")
            options = unit_select.find_elements(By.TAG_NAME, "option")
            for option in options:
                option_value = option.get_attribute('value')
                option_text = option.text.strip()
                if option_value:  # Pomiń pustą opcję "-- wybierz jednostkę --"
                    print(f"   ID {option_value}: {option_text}")

            # Użyj Select dla lepszej obsługi
            select = Select(unit_select)

            # Spróbuj wybrać po nazwie
            try:
                select.select_by_visible_text(unit_name)
                print(f"✅ Wybrano jednostkę po nazwie: '{unit_name}'")
                return True
            except:
                pass

            # Spróbuj wybrać po wartości (jeśli znamy mapowanie)
            unit_mapping = {
                "szt.": "0",
                "para": "1",
                "komplet": "2",
                "opakowanie": "3",
                "butelka": "4",
                "kilogram": "5",
                "metr kwadratowy": "6",
                "metr": "8",
                "gram": "9",
                "litr": "10",
                "usługa": "256"
            }

            unit_value = unit_mapping.get(unit_name)
            if unit_value:
                try:
                    select.select_by_value(unit_value)
                    print(
                        f"✅ Wybrano jednostkę po wartości: '{unit_name}' (ID: {unit_value})")
                    return True
                except:
                    pass

            # Spróbuj częściowe dopasowanie
            unit_lower = unit_name.lower()
            for option in select.options:
                option_text = option.text.strip().lower()
                if unit_lower in option_text or option_text in unit_lower:
                    try:
                        select.select_by_visible_text(option.text)
                        print(
                            f"✅ Wybrano jednostkę (częściowe dopasowanie): '{option.text.strip()}'")
                        return True
                    except:
                        continue

            print(f"❌ Nie znaleziono jednostki: '{unit_name}'")
            return False

        except Exception as e:
            print(f"❌ Błąd podczas ustawiania jednostki: {str(e)}")
            return False

    def extract_fabric_from_size_table(self):
        """
        Wyciąga informacje o składzie materiału z tabeli rozmiarów

        Returns:
            list: Lista słowników [{'component': 'poliamid', 'percentage': 80}, ...]
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            print(f"🧵 Szukam informacji o składzie materiału...")

            # Znajdź pole z tabelą rozmiarów
            size_table_field = driver.find_element(
                By.CSS_SELECTOR,
                "#products_form > div > fieldset > div.form-row.field-get_size_table_html"
            )

            # Znajdź konkretny element div.prod_data z informacjami o materiale
            try:
                prod_data_element = size_table_field.find_element(
                    By.CSS_SELECTOR, "div.prod_data")
                # Pobierz HTML zamiast tekstu aby zachować strukture <strong>
                size_table_text = prod_data_element.get_attribute(
                    'innerHTML').strip()
                print(
                    f"📋 Zawartość div.prod_data:\n{size_table_text[:200]}...")
            except Exception as e:
                print(
                    f"⚠️ Nie znaleziono div.prod_data, używam całego pola: {str(e)}")
                size_table_text = size_table_field.text.strip()
                print(
                    f"📋 Zawartość tabeli rozmiarów (fallback):\n{size_table_text[:200]}...")

            # Szukaj wzorców materiałów w tekście
            fabric_info = []

            # Wzorce do wyszukiwania składu materiału
            import re

            # Najpopularniejsze wzorce składu tkaniny
            patterns = [
                # "80% poliamid, 20% elastan"
                r'(\d+)\s*%\s*(poliamid|elastan|poliester|bawełna|nylon|lycra|spandex)',
                # "poliamid 80%, elastan 20%"
                r'(poliamid|elastan|poliester|bawełna|nylon|lycra|spandex)\s*(\d+)\s*%',
                # HTML format: "<strong>Elastan</strong> 15 %"
                r'<strong>(poliamid|elastan|poliester|bawełna|nylon|lycra|spandex)</strong>\s*(\d+)\s*%',
                # Odwrócony HTML format: "15 % <strong>elastan</strong>"
                r'(\d+)\s*%\s*</?strong[^>]*>(poliamid|elastan|poliester|bawełna|nylon|lycra|spandex)</strong>',
            ]

            # Mapowanie nazw materiałów na standardowe nazwy
            material_mapping = {
                'poliamid': 'poliamid',
                'nylon': 'poliamid',
                'elastan': 'elastan',
                'lycra': 'elastan',
                'spandex': 'elastan',
                'poliester': 'poliester',
                'bawełna': 'bawełna'
            }

            text_lower = size_table_text.lower()

            # Sprawdź każdy wzorzec
            for i, pattern in enumerate(patterns):
                matches = re.finditer(pattern, size_table_text, re.IGNORECASE)
                for match in matches:
                    percentage = None
                    material = None

                    if i == 0:  # "80% poliamid"
                        percentage = int(match.group(1))
                        material = match.group(2).lower()
                    elif i == 1:  # "poliamid 80%"
                        material = match.group(1).lower()
                        percentage = int(match.group(2))
                    elif i == 2:  # "<strong>Elastan</strong> 15 %"
                        material = match.group(1).lower()
                        percentage = int(match.group(2))
                    elif i == 3:  # "15 % <strong>elastan</strong>"
                        percentage = int(match.group(1))
                        material = match.group(2).lower()

                    if percentage and material:
                        # Mapuj na standardową nazwę
                        standard_material = material_mapping.get(
                            material, material)

                        # Dodaj do listy jeśli jeszcze nie ma
                        existing = next(
                            (item for item in fabric_info if item['component'] == standard_material), None)
                        if not existing:
                            fabric_info.append({
                                'component': standard_material,
                                'percentage': percentage
                            })
                            print(
                                f"   🧵 Znaleziono: {standard_material} {percentage}%")

            # Jeśli nie znaleziono konkretnych składników, spróbuj bardziej konserwatywne podejście
            if not fabric_info:
                print(
                    f"🔍 Nie znaleziono składników z procentami, sprawdzam czy są wyraźne informacje o materiale...")

                # Bardziej konserwatywne sprawdzenie - wymagamy wyraźnych oznak opisu materiału
                material_context_keywords = [
                    'materiał:', 'skład:', 'składa się z', 'wykonany z', 'material:', 'composition:',
                    'fabric:', 'made of', 'tkanina:', 'włókno:'
                ]

                # Sprawdź czy jest kontekst opisu materiału
                has_material_context = any(
                    keyword in text_lower for keyword in material_context_keywords)

                if has_material_context:
                    print(f"   📋 Znaleziono kontekst opisu materiału")

                    # Tylko wtedy sprawdź słowa kluczowe materiałów
                    if any(word in text_lower for word in ['poliamid', 'nylon']):
                        fabric_info.append(
                            {'component': 'poliamid', 'percentage': 80})
                        print(
                            f"   🧵 Wykryto poliamid w kontekście materiału (domyślnie 80%)")

                    if any(word in text_lower for word in ['elastan', 'lycra', 'spandex']):
                        fabric_info.append(
                            {'component': 'elastan', 'percentage': 20})
                        print(
                            f"   🧵 Wykryto elastan w kontekście materiału (domyślnie 20%)")
                else:
                    print(
                        f"   ⚠️ Brak wyraźnego kontekstu materiału - pomijam fallback")
                    print(f"   ℹ️ Aby uniknąć błędów, nie dodaję domyślnych wartości")

            if fabric_info:
                # Sortuj składniki alfabetycznie (zgodnie z kolejnością w formularzu)
                fabric_info = sorted(fabric_info, key=lambda x: x['component'])

                print(f"✅ Wykryto składniki (posortowane alfabetycznie):")
                for item in fabric_info:
                    print(f"   - {item['component']}: {item['percentage']}%")
            else:
                print(f"❌ Nie wykryto składu materiału")

            return fabric_info

        except Exception as e:
            print(f"❌ Błąd podczas wyciągania składu materiału: {str(e)}")
            return []

    def set_fabric_components(self, fabric_info):
        """
        Ustawia składniki tkaniny w formularzu

        Args:
            fabric_info (list): Lista słowników [{'component': 'poliamid', 'percentage': 80}, ...]

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            if not fabric_info:
                print(f"⚠️ Brak informacji o składzie materiału do ustawienia")
                return False

            print(f"🧵 Ustawiam składniki tkaniny...")
            print(f"📋 Liczba składników do ustawienia: {len(fabric_info)}")
            print(f"📋 Składniki do ustawienia:")
            for idx, item in enumerate(fabric_info):
                print(f"   {idx}: {item['component']} {item['percentage']}%")

            # Mapowanie nazw materiałów na wartości w dropdown
            fabric_mapping = {
                'elastan': '1',
                'poliamid': '2'
            }

            # Ustaw każdy składnik
            for i, fabric_data in enumerate(fabric_info):
                component = fabric_data['component']
                percentage = fabric_data['percentage']

                print(
                    f"\n--- 🧵 Przetwarzam składnik {i+1}/{len(fabric_info)} ---")
                print(f"   Składnik: '{component}'")
                print(f"   Procent: {percentage}%")

                # Znajdź wartość dla dropdown
                fabric_value = fabric_mapping.get(component)
                if not fabric_value:
                    print(f"❌ Nieznany materiał: {component}")
                    continue

                print(f"   Mapowany na ID: '{fabric_value}'")

                # Jeśli to nie pierwszy składnik, dodaj nowy wiersz
                if i > 0:
                    try:
                        add_fabric_button = driver.find_element(
                            By.XPATH, "//button[contains(text(), 'Dodaj materiał') or @onclick='addFabricRow()']"
                        )
                        add_fabric_button.click()
                        print(
                            f"🔄 Kliknięto 'Dodaj materiał' dla składnika {i+1}")

                        # Dłuższa pauza aby formularz się zaktualizował
                        import time
                        time.sleep(1.5)
                        print(f"   ⏳ Pauza 1.5s na aktualizację DOM")

                    except Exception as e:
                        print(
                            f"⚠️ Nie udało się dodać nowego wiersza materiału: {str(e)}")
                        break

                # Znajdź wszystkie pola fabric_component[] i fabric_percentage[] (po ewentualnym dodaniu)
                fabric_selects = driver.find_elements(
                    By.NAME, "fabric_component[]")
                fabric_percentages = driver.find_elements(
                    By.NAME, "fabric_percentage[]")

                print(f"📋 Dostępnych pól składników: {len(fabric_selects)}")

                if i >= len(fabric_selects):
                    print(f"⚠️ Za mało pól formularza dla składnika {i+1}")
                    break

                # Ustaw dropdown z materiałem
                fabric_select = Select(fabric_selects[i])
                try:
                    fabric_select.select_by_value(fabric_value)
                    print(
                        f"   ✅ Składnik {i+1}: Wybrano materiał {component} (ID: {fabric_value})")
                except Exception as e:
                    print(
                        f"   ❌ Nie można wybrać materiału {component}: {str(e)}")
                    continue

                # Ustaw procent
                try:
                    percentage_input = fabric_percentages[i]
                    print(
                        f"   📝 Przed clear: element value = '{percentage_input.get_attribute('value')}'")
                    percentage_input.clear()
                    print(
                        f"   📝 Po clear: element value = '{percentage_input.get_attribute('value')}'")
                    print(f"   📝 Wysyłam klucze: '{str(percentage)}'")
                    percentage_input.send_keys(str(percentage))
                    print(
                        f"   📝 Po send_keys: element value = '{percentage_input.get_attribute('value')}'")
                    print(
                        f"   ✅ Składnik {i+1}: Ustawiono procent {percentage}%")
                except Exception as e:
                    print(
                        f"   ❌ Nie można ustawić procentu {percentage}%: {str(e)}")
                    continue

            print(
                f"✅ Zakończono ustawianie {len(fabric_info)} składników materiału")

            return True

        except Exception as e:
            print(f"❌ Błąd podczas ustawiania składników tkaniny: {str(e)}")
            return False

    def save_mpd_product(self):
        """
        Klika przycisk 'Utwórz nowy produkt w MPD' aby zapisać zmiany

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            print(f"💾 Zapisuję produkt MPD...")

            # Znajdź przycisk "Utwórz nowy produkt w MPD"
            save_button = driver.find_element(By.ID, "create-mpd-product-btn")

            # Sprawdź czy przycisk jest widoczny i klikalny
            if not save_button.is_displayed():
                print(f"⚠️ Przycisk 'Utwórz nowy produkt w MPD' nie jest widoczny")
                return False

            if not save_button.is_enabled():
                print(f"⚠️ Przycisk 'Utwórz nowy produkt w MPD' nie jest aktywny")
                return False

            # Kliknij przycisk
            save_button.click()
            print(f"✅ Kliknięto 'Utwórz nowy produkt w MPD'")

            # Poczekaj na przetworzenie (może być komunikat lub przekierowanie)
            import time
            time.sleep(2)

            # Sprawdź czy nie ma komunikatów błędów
            try:
                error_elements = driver.find_elements(
                    By.CSS_SELECTOR, ".error, .alert-danger, .django-error")
                if error_elements:
                    error_text = error_elements[0].text.strip()
                    print(f"⚠️ Komunikat błędu: {error_text}")
                    return False
            except:
                pass

            # Sprawdź czy nie ma komunikatów sukcesu
            try:
                success_elements = driver.find_elements(
                    By.CSS_SELECTOR, ".success, .alert-success, .django-success")
                if success_elements:
                    success_text = success_elements[0].text.strip()
                    print(f"✅ Komunikat sukcesu: {success_text}")
            except:
                pass

            print(f"✅ Produkt MPD został zapisany")
            return True

        except Exception as e:
            print(f"❌ Błąd podczas zapisywania produktu MPD: {str(e)}")
            return False

    def return_to_products_list(self, filtered_url=None):
        """
        Powraca do listy produktów aby kontynuować pracę z kolejnymi produktami

        Args:
            filtered_url (str): Opcjonalny URL z filtrami (np. is_mapped__exact=0)

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            print(f"🔙 Powracam do listy produktów...")

            # Metoda 0: Jeśli podano filtered_url, nawiguj bezpośrednio tam
            if filtered_url:
                try:
                    print(f"🎯 Nawiguję do URL z filtrami: {filtered_url}")
                    driver.get(filtered_url)
                    import time
                    time.sleep(2)
                    print(f"✅ Nawigacja do filtrowanej listy produktów zakończona")
                    return True
                except Exception as e:
                    print(
                        f"⚠️ Nie udało się nawigować do filtered_url: {str(e)}")

            # Metoda 1: Użyj przycisku "Back" lub "Wstecz" jeśli istnieje
            try:
                back_button = driver.find_element(
                    By.XPATH, "//a[contains(text(), 'Back') or contains(text(), 'Wstecz') or contains(@class, 'back')]")
                back_button.click()
                print(f"✅ Kliknięto przycisk 'Back'")
                import time
                time.sleep(1)
                return True
            except:
                pass

            # Metoda 2: Użyj breadcrumb lub linku do produktów
            try:
                products_link = driver.find_element(
                    By.XPATH, "//a[contains(@href, '/products/') or contains(text(), 'Products') or contains(text(), 'Produkty')]")
                products_link.click()
                print(f"✅ Kliknięto link do produktów")
                import time
                time.sleep(1)
                return True
            except:
                pass

            # Metoda 3: Nawigacja przez historię przeglądarki
            try:
                driver.back()
                print(f"✅ Użyto przycisku 'Wstecz' przeglądarki")
                import time
                time.sleep(1)
                return True
            except:
                pass

            # Metoda 4: Bezpośrednia nawigacja do URL listy produktów
            try:
                current_url = driver.current_url
                # Wyciągnij bazowy URL i przejdź do listy produktów
                if '/admin/' in current_url:
                    base_url = current_url.split('/admin/')[0] + '/admin/'
                    products_url = base_url + "matterhorn/products/"
                    driver.get(products_url)
                    print(f"✅ Nawigacja bezpośrednia do: {products_url}")
                    import time
                    time.sleep(2)
                    return True
            except Exception as e:
                print(f"⚠️ Błąd nawigacji bezpośredniej: {str(e)}")

            print(f"❌ Nie udało się powrócić do listy produktów")
            return False

        except Exception as e:
            print(f"❌ Błąd podczas powrotu do listy produktów: {str(e)}")
            return False

    def complete_mpd_process(self, filtered_url=None):
        """
        Kompletuje proces MPD: zapisuje produkt i wraca do listy

        Args:
            filtered_url (str): URL z filtrami do powrotu

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            print(f"\n💾 Finalizuję proces MPD...")

            # 1. Zapisz produkt MPD
            save_success = self.save_mpd_product()
            if not save_success:
                print(f"❌ Nie udało się zapisać produktu MPD")
                return False

            # 2. Powróć do listy produktów (z filtrami)
            return_success = self.return_to_products_list(filtered_url)
            if not return_success:
                print(f"❌ Nie udało się powrócić do listy produktów")
                return False

            print(f"✅ Proces MPD zakończony pomyślnie")
            return True

        except Exception as e:
            print(f"❌ Błąd podczas finalizacji procesu MPD: {str(e)}")
            return False

    def auto_detect_and_set_fabric_components(self):
        """
        Automatycznie wykrywa składniki materiału z tabeli rozmiarów i ustawia je

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            print(f"\n🧵 Automatyczne wykrywanie i ustawianie składu materiału...")

            # Wyciągnij informacje o składzie z tabeli rozmiarów
            fabric_info = self.extract_fabric_from_size_table()

            if not fabric_info:
                print(f"❌ Nie udało się wykryć składu materiału")
                return False

            # Ustaw składniki w formularzu
            success = self.set_fabric_components(fabric_info)

            if success:
                print(f"✅ Pomyślnie ustawiono składniki materiału")
            else:
                print(f"❌ Błąd podczas ustawiania składników materiału")

            return success

        except Exception as e:
            print(
                f"❌ Błąd podczas automatycznego ustawiania składu materiału: {str(e)}")
            return False

    def auto_detect_and_set_producer_color(self):
        """
        Automatycznie wykrywa i ustawia kolor producenta na podstawie tytułu produktu

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            # Pobierz tytuł produktu z nagłówka h2
            title_element = driver.find_element(By.TAG_NAME, "h2")
            product_title = title_element.text.strip()

            if not product_title:
                print("⚠️ Nie znaleziono tytułu produktu")
                return False

            # Wykryj kolor z tytułu
            detected_color = self.extract_producer_color_from_title(
                product_title)

            if not detected_color:
                print("❌ Nie wykryto koloru w tytule produktu")
                return False

            # Ustaw wykryty kolor
            return self.set_producer_color(detected_color)

        except Exception as e:
            print(f"❌ Błąd podczas automatycznego wykrywania koloru: {str(e)}")
            return False

    def auto_setup_mpd_fields(self):
        """
        Automatycznie ustawia wszystkie pola MPD w odpowiedniej kolejności:
        1. Kategoria rozmiaru (bielizna)
        2. Główny kolor (na podstawie koloru producenta)
        3. Kolor producenta (z tytułu produktu)

        Returns:
            bool: True jeśli wszystkie operacje się powiodły
        """
        print("🔧 Rozpoczynam automatyczne ustawianie pól MPD...")

        # 1. Ustaw kategorię rozmiaru na "bielizna"
        print("\n📏 Ustawiam kategorię rozmiaru...")
        size_category_success = self.set_mpd_size_category("bielizna")

        # 2. Wykryj kolor producenta z tytułu
        print("\n🎨 Wykrywam kolor producenta z tytułu...")
        detected_producer_color = None
        try:
            driver = self.navigator.login_agent.get_driver()
            title_element = driver.find_element(By.TAG_NAME, "h2")
            product_title = title_element.text.strip()

            if product_title:
                detected_producer_color = self.extract_producer_color_from_title(
                    product_title)

        except Exception as e:
            print(f"❌ Błąd podczas wykrywania koloru z tytułu: {str(e)}")

        # 3. Wybierz główny kolor z dropdown na podstawie pola readonly
        print(f"\n🌈 Wybieram główny kolor z dropdown na podstawie pola readonly...")
        main_color_success = self.select_main_color_from_dropdown()

        # 4. Ustaw kolor producenta w polu
        producer_color_success = False
        if detected_producer_color:
            print(f"\n📝 Ustawiam kolor producenta w polu...")
            producer_color_success = self.set_producer_color(
                detected_producer_color)

        # 5. Ustaw nazwę serii na podstawie nazwy modelu
        print(f"\n🏷️ Ustawiam nazwę serii na podstawie nazwy modelu...")
        series_name_success = self.auto_detect_and_set_series_name()

        # 6. Ustaw ścieżki kategorii na podstawie typu produktu
        print(f"\n🗂️ Ustawiam ścieżki kategorii na podstawie typu produktu...")
        paths_success = self.auto_detect_and_set_mpd_paths()

        # 7. Ustaw jednostkę na "szt."
        print(f"\n📏 Ustawiam jednostkę na 'szt.'...")
        unit_success = self.set_unit("szt.")

        # 8. Ustaw składniki materiału na podstawie tabeli rozmiarów
        print(f"\n🧵 Ustawiam składniki materiału z tabeli rozmiarów...")
        fabric_success = self.auto_detect_and_set_fabric_components()

        # Podsumowanie
        successes = [size_category_success, main_color_success, producer_color_success,
                     series_name_success, paths_success, unit_success, fabric_success]
        success_count = sum(successes)

        print(f"\n📊 Podsumowanie ustawiania pól MPD:")
        print(
            f"   ✅ Kategoria rozmiaru: {'OK' if size_category_success else 'BŁĄD'}")
        print(f"   ✅ Główny kolor: {'OK' if main_color_success else 'BŁĄD'}")
        print(
            f"   ✅ Kolor producenta: {'OK' if producer_color_success else 'BŁĄD'}")
        print(f"   ✅ Nazwa serii: {'OK' if series_name_success else 'BŁĄD'}")
        print(f"   ✅ Ścieżki kategorii: {'OK' if paths_success else 'BŁĄD'}")
        print(f"   ✅ Jednostka: {'OK' if unit_success else 'BŁĄD'}")
        print(
            f"   ✅ Składniki materiału: {'OK' if fabric_success else 'BŁĄD'}")
        print(f"   📈 Sukces: {success_count}/7 pól")

        return success_count >= 6  # Uznajemy sukces jeśli co najmniej 6/7 pól się udało

    def auto_detect_and_set_mpd_attributes(self):
        """
        Automatycznie wykrywa i ustawia atrybuty MPD na podstawie długiego opisu

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            driver = self.navigator.login_agent.get_driver()

            # Pobierz długi opis z pola mpd_description
            description_field = driver.find_element(By.ID, "mpd_description")
            description = description_field.get_attribute("value") or ""

            if not description.strip():
                print("⚠️ Brak długiego opisu - nie można wykryć atrybutów")
                return False

            # Wykryj atrybuty z opisu
            detected_attributes = self.extract_mpd_attributes_from_description(
                description)

            if not detected_attributes:
                print("❌ Nie wykryto żadnych atrybutów w opisie")
                return False

            # Ustaw wykryte atrybuty
            return self.set_mpd_attributes(detected_attributes)

        except Exception as e:
            print(
                f"❌ Błąd podczas automatycznego wykrywania atrybutów: {str(e)}")
            return False

    def _extract_first_sentences(self, long_description):
        """Wyciąga pierwsze lub dwa pierwsze zdania z długiego opisu"""
        # Podstawowe czyszczenie
        text = long_description.strip()

        # Podziel na zdania (zakończone kropką, wykrzyknikiem, znakiem zapytania)
        import re
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            # Jeśli nie ma zdań, inteligentnie skróć
            return self._smart_truncate(text, 150)

        # Weź pierwsze zdanie
        first_sentence = sentences[0].strip()

        # Jeśli pierwsze zdanie jest rozsądnej długości (do 150 znaków), użyj go
        if len(first_sentence) <= 150:
            print(f"✅ Wzięto pierwsze zdanie ({len(first_sentence)} znaków)")
            return first_sentence

        # Jeśli za długie, inteligentnie skróć
        short = self._smart_truncate(first_sentence, 150)
        print(
            f"✅ Skrócono pierwsze zdanie inteligentnie ({len(short)} znaków)")
        return short

    def _smart_truncate(self, text, max_length):
        """Inteligentnie skraca tekst nie obcinając słów"""
        if len(text) <= max_length:
            return text

        # Znajdź ostatnią spację przed limitem
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')

        # Jeśli spacja jest w rozsądnym miejscu (po 70% tekstu)
        if last_space > max_length * 0.7:
            result = text[:last_space]
        else:
            # Jeśli nie ma dobrej spacji, skróć do ostatniego pełnego słowa
            words = text.split()
            result = ""
            for word in words:
                if len(result + " " + word) <= max_length:
                    result += " " + word if result else word
                else:
                    break

        return result.strip()

    def _is_title_already_optimized(self, title):
        """
        Sprawdza czy tytuł już jest w prawidłowym formacie

        Args:
            title (str): Tytuł do sprawdzenia

        Returns:
            bool: True jeśli tytuł już jest prawidłowy
        """
        if not title:
            return False

        title_lower = title.lower().strip()

        # Wzorce prawidłowych tytułów dla dwuczęściowych kostiumów
        valid_patterns = [
            "figi kąpielowe",
            "biustonosz kąpielowy"
        ]

        # Sprawdź czy tytuł zaczyna się od któregoś z prawidłowych wzorców
        for pattern in valid_patterns:
            if title_lower.startswith(pattern):
                print(f"✅ Tytuł już jest prawidłowy (wzorzec: '{pattern}')")
                return True

        # Sprawdź czy to nie jest długi nieprawidłowy tytuł (jak oryginalny z "Kostium dwuczęściowy")
        if "kostium dwuczęściowy" in title_lower:
            print(f"❌ Tytuł wymaga optymalizacji (zawiera 'kostium dwuczęściowy')")
            return False

        print(f"🤔 Nieznany format tytułu: {title}")
        return False

    def edit_mpd_short_description_field(self, new_value=None, use_ai_optimization=True):
        """
        Edytuje pole mpd_short_description na stronie szczegółów produktu

        Args:
            new_value (str): Nowa wartość pola (jeśli None, generuje z długiego opisu)
            use_ai_optimization (bool): Czy używać AI do generowania

        Returns:
            bool: True jeśli edycja się powiodła
        """
        try:
            driver = self.navigator.get_driver()

            if not driver:
                print("❌ Brak aktywnej sesji przeglądarki")
                return False

            # Sprawdź czy jesteśmy na stronie edycji produktu
            current_url = driver.current_url
            if "/change/" not in current_url:
                print("❌ Nie jesteśmy na stronie edycji produktu")
                return False

            # Znajdź pole mpd_short_description
            try:
                short_desc_field = driver.find_element(
                    By.ID, "mpd_short_description")
                print("✅ Znaleziono pole mpd_short_description")
            except Exception as e:
                print(
                    f"❌ Nie można znaleźć pola mpd_short_description: {str(e)}")
                return False

            # Pobierz aktualną wartość
            current_value = short_desc_field.get_attribute("value")
            print(f"📝 Aktualny krótki opis: {current_value}")

            # Określ nową wartość
            if new_value:
                final_value = new_value
                print(f"🎯 Używam podanej wartości")
            elif use_ai_optimization:
                # Pobierz długi opis dla kontekstu
                try:
                    long_desc_field = driver.find_element(
                        By.ID, "mpd_description")
                    long_description = long_desc_field.get_attribute("value")
                except Exception:
                    long_description = ""

                # Pobierz tytuł produktu dla kontekstu
                try:
                    title_field = driver.find_element(By.ID, "mpd_name")
                    product_title = title_field.get_attribute("value")
                except Exception:
                    product_title = None

                if not long_description:
                    print("❌ Brak długiego opisu - nie można wygenerować krótkiego")
                    return False

                final_value = self.get_ai_short_description(
                    long_description, product_title)
                print(f"🤖 AI wygenerował krótki opis")
            else:
                print("❌ Brak nowej wartości do ustawienia")
                return False

            # Sprawdź czy wartość się zmieniła
            if current_value == final_value:
                print("ℹ️ Krótki opis jest już poprawny, nie ma co zmieniać")
                return True

            # Wyczyść pole i wprowadź nową wartość
            short_desc_field.clear()
            short_desc_field.send_keys(final_value)

            # Sprawdź czy wartość została ustawiona
            time.sleep(1)
            new_field_value = short_desc_field.get_attribute("value")

            if new_field_value == final_value:
                print(f"✅ Pomyślnie zmieniono krótki opis")
                return True
            else:
                print(f"❌ Krótki opis nie został poprawnie ustawiony")
                return False

        except Exception as e:
            print(
                f"❌ Błąd podczas edycji pola mpd_short_description: {str(e)}")
            return False

    def edit_all_fields(self, name_value=None, description_value=None, short_description_value=None, use_ai_optimization=True):
        """
        Edytuje wszystkie pola: mpd_name, mpd_description i mpd_short_description

        Args:
            name_value (str): Nowa wartość nazwy (jeśli None, używa AI)
            description_value (str): Nowa wartość długiego opisu (jeśli None, używa AI)
            short_description_value (str): Nowa wartość krótkiego opisu (jeśli None, generuje AI z długiego)
            use_ai_optimization (bool): Czy używać AI do optymalizacji

        Returns:
            bool: True jeśli edycja wszystkich pól się powiodła
        """
        print("🔄 Edytuję wszystkie pola: nazwę, długi opis i krótki opis...")

        success_name = self.edit_mpd_name_field(
            name_value, use_ai_optimization)
        success_description = self.edit_mpd_description_field(
            description_value, use_ai_optimization)
        success_short_description = self.edit_mpd_short_description_field(
            short_description_value, use_ai_optimization)

        successes = [success_name, success_description,
                     success_short_description]
        success_count = sum(successes)

        if success_count == 3:
            print("✅ Wszystkie pola zostały pomyślnie zmodyfikowane!")
            return True
        elif success_count >= 2:
            print(f"⚠️ {success_count}/3 pól zostało zmienionych pomyślnie")
            return True  # Uznajemy częściowy sukces za sukces
        elif success_count == 1:
            print(
                f"⚠️ Tylko {success_count}/3 pole zostało zmienione pomyślnie")
            return False
        else:
            print("❌ Nie udało się zmienić żadnego z pól")
            return False

    def edit_both_fields(self, name_value=None, description_value=None, use_ai_optimization=True):
        """
        Edytuje oba pola: mpd_name i mpd_description (zachowane dla kompatybilności)

        Args:
            name_value (str): Nowa wartość nazwy (jeśli None, używa AI)
            description_value (str): Nowa wartość opisu (jeśli None, używa AI)
            use_ai_optimization (bool): Czy używać AI do optymalizacji

        Returns:
            bool: True jeśli edycja obu pól się powiodła
        """
        print("🔄 Edytuję oba pola: nazwę i opis produktu...")

        success_name = self.edit_mpd_name_field(
            name_value, use_ai_optimization)
        success_description = self.edit_mpd_description_field(
            description_value, use_ai_optimization)

        if success_name and success_description:
            print("✅ Oba pola zostały pomyślnie zmodyfikowane!")
            return True
        elif success_name:
            print("⚠️ Nazwa została zmieniona, ale wystąpił problem z opisem")
            return False
        elif success_description:
            print("⚠️ Opis został zmieniony, ale wystąpił problem z nazwą")
            return False
        else:
            print("❌ Nie udało się zmienić żadnego z pól")
            return False

    def save_changes(self):
        """Zapisuje zmiany na stronie edycji produktu"""
        try:
            driver = self.navigator.get_driver()

            # Znajdź przycisk zapisywania
            save_button = driver.find_element(By.NAME, "_save")
            print("💾 Zapisuję zmiany...")
            save_button.click()

            # Poczekaj na przekierowanie
            time.sleep(3)

            # Sprawdź czy zapisywanie się powiodło
            current_url = driver.current_url
            if "/change/" not in current_url:
                print("✅ Zmiany zostały zapisane pomyślnie!")
                return True
            else:
                print("❌ Mogły wystąpić błędy podczas zapisywania")
                return False

        except Exception as e:
            print(f"❌ Błąd podczas zapisywania: {str(e)}")
            return False

    def edit_and_save_mpd_name(self, new_value=None, use_ai_optimization=True):
        """
        Edytuje pole mpd_name i zapisuje zmiany

        Args:
            new_value (str): Nowa wartość pola (jeśli None, używa AI)
            use_ai_optimization (bool): Czy używać AI do optymalizacji

        Returns:
            bool: True jeśli cała operacja się powiodła
        """
        try:
            # Edytuj pole
            if not self.edit_mpd_name_field(new_value, use_ai_optimization):
                return False

            # Zapisz zmiany
            if not self.save_changes():
                return False

            print("🎉 Pełna operacja edycji zakończona sukcesem!")
            return True

        except Exception as e:
            print(f"❌ Błąd podczas pełnej operacji edycji: {str(e)}")
            return False

    def close_browser(self):
        """Zamyka przeglądarkę jeśli jest właścicielem nawigatora"""
        if self.owned_navigator:
            self.navigator.close_browser()

    def __enter__(self):
        """Context manager - rozpoczęcie"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - zakończenie"""
        self.close_browser()


def navigate_to_lupo_line_products():
    """Funkcja pomocnicza do nawigacji do produktów Lupo Line"""
    navigator = ProductsNavigator()
    url = "http://localhost:8000/admin/matterhorn/products/?active=true&brand=Lupo+Line&category_name=Kostiumy+Dwuczęściowe&is_mapped__exact=0"
    return navigator.navigate_to_specific_url(url)


def test_attribute_extraction(description_text):
    """
    Funkcja testowa do sprawdzania wykrywania atrybutów z opisu

    Args:
        description_text (str): Tekst opisu do przeanalizowania

    Returns:
        list: Lista znalezionych ID atrybutów
    """
    editor = ProductEditor()
    return editor.extract_mpd_attributes_from_description(description_text)


def test_color_extraction(product_title):
    """
    Funkcja testowa do sprawdzania wykrywania koloru z tytułu

    Args:
        product_title (str): Tytuł produktu do przeanalizowania

    Returns:
        str: Wykryty kolor lub None
    """
    editor = ProductEditor()
    return editor.extract_producer_color_from_title(product_title)


def test_model_name_extraction(product_title):
    """
    Funkcja testowa do sprawdzania wykrywania nazwy modelu z tytułu

    Args:
        product_title (str): Tytuł produktu do przeanalizowania

    Returns:
        str: Wykryta nazwa modelu lub None
    """
    editor = ProductEditor()
    return editor.extract_model_name_from_title(product_title)


def test_series_name_creation(product_title):
    """
    Funkcja testowa do sprawdzania tworzenia nazwy serii

    Args:
        product_title (str): Tytuł produktu do przeanalizowania

    Returns:
        str: Utworzona nazwa serii
    """
    editor = ProductEditor()
    model_name = editor.extract_model_name_from_title(product_title)
    return editor.create_series_name(model_name)


def test_product_type_detection(product_title):
    """
    Funkcja testowa do sprawdzania wykrywania typu produktu

    Args:
        product_title (str): Tytuł produktu do przeanalizowania

    Returns:
        tuple: (typ produktu, ID ścieżki)
    """
    editor = ProductEditor()
    product_type = editor.detect_product_type_from_title(product_title)
    path_id = editor.get_path_id_for_product_type(
        product_type) if product_type else None
    return (product_type, path_id)


def run_product_name_agent():
    """
    Główna funkcja agenta do edycji nazw produktów

    Agent wykonuje w pętli dla wszystkich produktów:
    1. Logowanie do panelu
    2. Nawigację do produktów Lupo Line (kostiumy dwuczęściowe, is_mapped=0)
    3. Kliknięcie w pierwszy produkt 
    4. Zmianę nazwy według schematu AI
    5. Automatyczne ustawianie wszystkich pól MPD
    6. Zapisanie produktu i powrót do listy
    7. Powtórzenie dla kolejnego produktu
    """
    print("🤖 === Agent do edycji produktów MPD (pełna automatyzacja) === 🤖")
    print("📋 Nazwa: AI optymalizacja + terminologia")
    print("📝 Długi opis: AI optymalizacja przez OpenAI")
    print("📄 Krótki opis: Pierwsze 1-2 zdania z długiego opisu")
    print("🏷️ Atrybuty MPD: Automatyczne wykrywanie z opisu")
    print("🔧 Pola MPD: Kategoria, kolory, seria, ścieżki, jednostka, materiał")
    print("💾 Zapisanie: Automatyczne kliknięcie 'Utwórz nowy produkt w MPD'")
    print("🔄 Pętla: Agent pracuje aż zabraknie produktów na stronie")

    if not OPENAI_AVAILABLE:
        print("⚠️  WYMAGANE: pip install openai")

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️  WYMAGANE: OPENAI_API_KEY w pliku .env.dev")
    else:
        print("✅ OpenAI API key znaleziony")

    print()

    try:
        with ProductsNavigator() as nav:
            url = "http://localhost:8000/admin/matterhorn/products/?active=true&brand=Lupo+Line&category_name=Kostiumy+Dwuczęściowe&is_mapped__exact=0"

            processed_count = 0
            max_products = 50  # Bezpiecznik - maksymalnie 50 produktów na sesję

            while processed_count < max_products:
                print(f"\n{'='*60}")
                print(
                    f"🔄 PRODUKT {processed_count + 1} / maks. {max_products}")
                print(f"{'='*60}")

                # 1. Nawiguj i kliknij w pierwszy produkt
                print("🚀 Szukam kolejnego produktu do przetworzenia...")
                if nav.navigate_to_url_and_click_first_product(url):
                    print(f"✅ Dotarłem do produktu {processed_count + 1}!")

                    # 2. Edytuj wszystkie pola produktu
                    editor = ProductEditor(nav)
                    print(
                        "\n🤖 Analizuję i zmieniam nazwę, opis oraz krótki opis produktu...")

                    if editor.edit_all_fields(use_ai_optimization=True):
                        print("✅ Wszystkie pola produktu zostały zoptymalizowane!")

                        # 3. Automatyczne wykrywanie i ustawianie atrybutów MPD
                        print("\n🏷️ Wykrywam atrybuty MPD z opisu produktu...")
                        if editor.auto_detect_and_set_mpd_attributes():
                            print(
                                "✅ Atrybuty MPD zostały automatycznie wykryte i ustawione!")
                        else:
                            print(
                                "⚠️ Nie udało się wykryć lub ustawić atrybutów MPD")

                        # 4. Automatyczne ustawianie pól MPD
                        print(
                            "\n🔧 Ustawiam pola MPD (kategoria, kolory, seria, ścieżki, jednostka, materiał)...")
                        if editor.auto_setup_mpd_fields():
                            print("✅ Pola MPD zostały automatycznie ustawione!")
                        else:
                            print("⚠️ Nie udało się ustawić wszystkich pól MPD")

                        # 5. Zapisz produkt i wróć do listy (z filtrem is_mapped=0)
                        print("\n💾 Zapisuję produkt i wracam do listy...")
                        if editor.complete_mpd_process(url):
                            print(
                                f"✅ Produkt {processed_count + 1} został pomyślnie przetworzony i zapisany!")
                            processed_count += 1
                        else:
                            print(
                                f"❌ Nie udało się zapisać produktu {processed_count + 1}")
                            break

                    else:
                        print("❌ Nie udało się zmienić nazwy produktu")
                        break
                else:
                    print("🏁 Brak więcej produktów do przetworzenia lub błąd nawigacji")
                    break

                # Krótka pauza między produktami
                print(f"\n⏳ Pauza 2 sekundy przed kolejnym produktem...")
                time.sleep(2)

            print(f"\n{'='*60}")
            print(f"🎉 AGENT ZAKOŃCZYŁ PRACĘ!")
            print(f"📊 Przetworzone produkty: {processed_count}")
            if processed_count == max_products:
                print(
                    f"⚠️ Osiągnięto limit maksymalny ({max_products} produktów)")
            elif processed_count == 0:
                print(f"❌ Nie udało się przetworzyć żadnego produktu")
            else:
                print(f"✅ Wszystkie dostępne produkty zostały przetworzone")
            print(f"{'='*60}")

            return processed_count > 0

    except Exception as e:
        print(f"❌ Błąd agenta: {str(e)}")
        return False


if __name__ == "__main__":
    print("=== Agent do edycji nazw produktów ===")
    print("Dostępne opcje:")
    print("1. Test AI optymalizacji (bez przeglądarki)")
    print("2. Test wykrywania atrybutów MPD")
    print("3. Uruchom pełnego agenta")
    print()

    # Możesz wybrać co uruchomić przez zmianę tej zmiennej
    run_mode = 3  # 1 = test AI, 2 = test atrybutów, 3 = pełny agent

    if run_mode == 1:
        # Tylko test AI optymalizacji (bez przeglądarki)
        print("🧪 Uruchamiam test AI optymalizacji...")
        editor = ProductEditor()
        editor.test_ai_optimization()
        print("\n" + "="*50)
        editor.test_ai_description_optimization()
        print("\n" + "="*50)
        editor.test_ai_short_description_optimization()
        print("\n" + "="*50)
        editor.test_title_validation()
        print("\n✅ Wszystkie testy AI zakończone!")

    elif run_mode == 2:
        # Test wykrywania atrybutów MPD i kolorów
        print("🧪 Uruchamiam test wykrywania atrybutów MPD...")

        test_descriptions = [
            "Biustonosz sportowy bez fiszbin z miękkimi miseczkami i regulowanymi ramiączkami",
            "Figi kąpielowe z wysokim stanem, bezszwowe i przeciwżylakowe",
            "Kostium jednoczęściowy z wyjmowanymi wkładkami, gładkie miseczki",
            "Bielizna modelująca z płaskim szwem i niewidocznym wzmocnieniem",
            "Rajstopy wzorzyste z wzmocnionymi palcami"
        ]

        for i, desc in enumerate(test_descriptions, 1):
            print(f"\n--- Test atrybutów {i} ---")
            print(f"Opis: {desc}")
            attributes = test_attribute_extraction(desc)
            print(f"Wykryte atrybuty: {attributes}")

        print("\n" + "="*60)
        print("🎨 Uruchamiam test wykrywania kolorów producenta...")

        test_titles = [
            "214962 Kostium dwuczęściowy Figi 1 Kąpielowe Model Mirage Big Multicolor - Lupo Line",
            "123456 Biustonosz Model Comfort Black - Triumph",
            "789012 Figi Model Summer Red Coral - Change",
            "345678 Kostium Navy Blue Stripes - Anita",
            "567890 Model Basic White Nude Mix - Lupo"
        ]

        for i, title in enumerate(test_titles, 1):
            print(f"\n--- Test koloru {i} ---")
            print(f"Tytuł: {title}")
            color = test_color_extraction(title)
            print(f"Wykryty kolor: {color}")

        print("\n" + "="*60)
        print("🏷️ Uruchamiam test wykrywania nazw modeli i tworzenia nazw serii...")

        for i, title in enumerate(test_titles, 1):
            print(f"\n--- Test nazwy serii {i} ---")
            print(f"Tytuł: {title}")
            model_name = test_model_name_extraction(title)
            series_name = test_series_name_creation(title)
            print(f"Nazwa modelu: {model_name}")
            print(f"Nazwa serii: {series_name}")

        print("\n" + "="*60)
        print("🗂️ Uruchamiam test wykrywania typów produktów i ścieżek...")

        for i, title in enumerate(test_titles, 1):
            print(f"\n--- Test ścieżek {i} ---")
            print(f"Tytuł: {title}")
            product_type, path_id = test_product_type_detection(title)
            print(f"Typ produktu: {product_type}")
            print(f"ID ścieżki: {path_id}")

        print("\n✅ Wszystkie testy zakończone!")

    else:
        # Uruchom pełnego agenta
        print("🚀 Uruchamiam pełnego agenta...")
        success = run_product_name_agent()

        if success:
            print("\n🎯 Agent zakończył pracę pomyślnie!")
        else:
            print("\n💥 Agent napotkał błędy")
