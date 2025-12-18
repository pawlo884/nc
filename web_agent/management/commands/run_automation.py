"""
Management command do uruchomienia automatyzacji wypełniania formularzy MPD
"""
from django.core.management.base import BaseCommand
from web_agent.automation.browser_automation import BrowserAutomation
from web_agent.models import AutomationRun, BrandConfig
from matterhorn1.models import Brand, Category
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import os
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Uruchom automatyzację wypełniania formularzy MPD'

    def add_arguments(self, parser):
        parser.add_argument('--brand', type=str,
                            help='Nazwa marki (opcjonalne)')
        parser.add_argument('--category', type=str,
                            help='Nazwa kategorii (opcjonalne)')
        parser.add_argument('--active', type=str,
                            help='Filtr active (true/false, opcjonalne)')
        parser.add_argument('--is_mapped', type=str,
                            help='Filtr is_mapped (true/false, opcjonalne)')
        parser.add_argument('--max', type=int, default=1,
                            help='Maksymalna liczba produktów do otwarcia (domyślnie: 1)')

    def handle(self, *args, **options):
        brand_name = options.get('brand')
        category_name = options.get('category')
        max_products = options.get('max')

        # Konwertuj stringi na boolean
        active_filter = None
        if options.get('active'):
            active_filter = options.get('active').lower() in (
                'true', '1', 'yes', 'tak')

        is_mapped_filter = None
        if options.get('is_mapped'):
            is_mapped_filter = options.get(
                'is_mapped').lower() in ('true', '1', 'yes', 'tak')

        self.stdout.write(f"\nURUCHOMIENIE AGENTA")
        self.stdout.write(f"   Marka: {brand_name or 'Wszystkie'}")
        self.stdout.write(f"   Kategoria: {category_name or 'Wszystkie'}")
        if active_filter is not None:
            self.stdout.write(f"   Active: {active_filter}")
        if is_mapped_filter is not None:
            self.stdout.write(f"   Is Mapped: {is_mapped_filter}")
        self.stdout.write("")

        # Znajdź brand i category ID tylko jeśli podano
        brand_id = None
        brand = None
        brand_config = None
        if brand_name:
            try:
                # Nie wymuszaj aliasu bazy - routing (Matterhorn1Router) wybierze poprawnie
                # 'zzz_matterhorn1' w dev lub 'matterhorn1' w prod.
                brand = Brand.objects.get(name__iexact=brand_name)
                brand_id = int(brand.brand_id)
                self.stdout.write(
                    f"[OK] Znaleziono marke: {brand.name} (ID: {brand_id})")

                # Sprawdź czy istnieje konfiguracja dla tej marki
                try:
                    brand_config = BrandConfig.objects.get(brand_id=brand_id)
                    self.stdout.write(self.style.SUCCESS(
                        f"[OK] Znaleziono konfigurację marki: {brand_config.brand_name}"))
                except BrandConfig.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"[WARNING] Brak konfiguracji dla marki {brand_name}"))
            except Brand.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"[ERROR] Nie znaleziono marki: {brand_name}"))
                return

        category_id = None
        category = None
        if category_name:
            try:
                # Nie wymuszaj aliasu bazy - routing (Matterhorn1Router) wybierze poprawnie
                # 'zzz_matterhorn1' w dev lub 'matterhorn1' w prod.
                category = Category.objects.filter(
                    name__icontains=category_name).first()
                if category:
                    category_id = int(category.category_id)
                    self.stdout.write(
                        f"[OK] Znaleziono kategorie: {category.name} (ID: {category_id})")
                else:
                    self.stdout.write(self.style.WARNING(
                        f"[WARNING] Nie znaleziono kategorii: {category_name}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"[WARNING] Blad podczas wyszukiwania kategorii: {e}"))

        # Utwórz AutomationRun
        # Użyj domyślnych filtrów z konfiguracji marki, jeśli nie podano w parametrach
        # Globalne domyślne wartości: active=True, is_mapped=False
        filters = {}
        if active_filter is not None:
            filters['active'] = active_filter
        elif brand_config and brand_config.default_active_filter is not None:
            filters['active'] = brand_config.default_active_filter
            self.stdout.write(
                f"[INFO] Użyto domyślnego filtra active z konfiguracji: {brand_config.default_active_filter}")
        else:
            # Globalny domyślny filtr active=True
            filters['active'] = True
            self.stdout.write(
                "[INFO] Użyto globalnego domyślnego filtra active: True")

        if is_mapped_filter is not None:
            filters['is_mapped'] = is_mapped_filter
        elif brand_config and brand_config.default_is_mapped_filter is not None:
            filters['is_mapped'] = brand_config.default_is_mapped_filter
            self.stdout.write(
                f"[INFO] Użyto domyślnego filtra is_mapped z konfiguracji: {brand_config.default_is_mapped_filter}")
        else:
            # Globalny domyślny filtr is_mapped=False
            filters['is_mapped'] = False
            self.stdout.write(
                "[INFO] Użyto globalnego domyślnego filtra is_mapped: False")

        # AutomationRun automatycznie trafi do bazy web_agent dzięki WebAgentRouter
        automation_run = AutomationRun.objects.create(
            status='running',
            brand_id=brand_id,
            category_id=category_id,
            filters=filters
        )
        self.stdout.write(
            f"\n[OK] Utworzono AutomationRun ID: {automation_run.id}\n")

        # Konfiguracja
        base_url = os.getenv('WEB_AGENT_BASE_URL',
                             'http://localhost:8080/admin/')
        admin_username = os.getenv('DJANGO_ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('DJANGO_ADMIN_PASSWORD', '')

        if not admin_password:
            self.stdout.write(self.style.ERROR(
                "[ERROR] Brak DJANGO_ADMIN_PASSWORD w .env.dev"))
            automation_run.status = 'failed'
            automation_run.error_message = "Brak konfiguracji"
            automation_run.save()
            return

        try:
            # Inicjalizuj przeglądarkę
            browser = BrowserAutomation(
                base_url, admin_username, admin_password, headless=False)

            # Uruchom przeglądarkę
            self.stdout.write("\n[INFO] Uruchamianie przeglądarki...")
            browser.start_browser()

            # Zaloguj się do admin
            self.stdout.write("[INFO] Logowanie do admin...")
            browser.login_to_admin()
            self.stdout.write(self.style.SUCCESS("[OK] Zalogowano do admin"))

            # Przygotuj filtry tylko jeśli są podane
            automation_filters = {}

            if brand_id and brand:
                automation_filters['brand_id'] = brand_id
                automation_filters['brand_name'] = brand.name
                self.stdout.write(f"\n[INFO] Filtr marki: {brand.name}")

            if category_id:
                automation_filters['category_id'] = category_id
                # Dodaj nazwę kategorii do filtrów
                automation_filters['category_name'] = category_name
                self.stdout.write(f"[INFO] Filtr kategorii: {category_name}")
            elif category_name:
                # Jeśli nie znaleziono w bazie, ale podano nazwę, spróbuj użyć oryginalnej nazwy
                automation_filters['category_name'] = category_name
                self.stdout.write(
                    f"[INFO] Filtr kategorii (bez ID): {category_name}")

            # Dodaj filtry active i is_mapped z utworzonych filtrów (zawierają już domyślne wartości)
            if 'active' in filters:
                automation_filters['active'] = filters['active']
                self.stdout.write(f"[INFO] Filtr active: {filters['active']}")

            if 'is_mapped' in filters:
                automation_filters['is_mapped'] = filters['is_mapped']
                self.stdout.write(
                    f"[INFO] Filtr is_mapped: {filters['is_mapped']}")

            # Przejdź do listy produktów (z filtrami lub bez)
            self.stdout.write(f"\n[INFO] Przechodzenie do listy produktów...")
            if not automation_filters:
                self.stdout.write(
                    "   Brak filtrów - wyświetlanie wszystkich produktów")

            browser.navigate_to_product_list(
                automation_filters if automation_filters else None)

            if automation_filters:
                self.stdout.write(self.style.SUCCESS(
                    "\n[OK] Przeglądarka otwarta z wybranymi filtrami!"))
            else:
                self.stdout.write(self.style.SUCCESS(
                    "\n[OK] Przeglądarka otwarta - wszystkie produkty!"))

            # Przetwarzaj produkty z listy (max_products)
            if max_products and max_products > 0:
                self.stdout.write(
                    f"\n[INFO] Przetwarzanie produktów z listy (max: {max_products})...")

                # Zapisz URL listy produktów z filtrami przed wejściem w pierwszy produkt
                filtered_list_url = browser.driver.current_url
                # Zapisz również w obiekcie browser, aby metody mogły z niego korzystać
                browser._saved_filtered_list_url = filtered_list_url
                self.stdout.write(
                    f"[DEBUG] Zapisano URL listy produktów z filtrami: {filtered_list_url}")
                logger.info(
                    f"Zapisano URL listy produktów z filtrami: {filtered_list_url}")

                # WAŻNE:
                # Po CREATE/ASSIGN produkt często znika z listy (np. gdy filtrujemy is_mapped=False),
                # więc indeksy w tabeli przesuwają się i "produkt o indeksie 1" staje się innym produktem.
                # Żeby nie przeskakiwać (np. 1->3), zawsze wybieramy kolejny NIEprzetworzony produkt
                # na podstawie aktualnej listy checkboxów (ID) na stronie.
                processed_product_ids = set()

                for product_index in range(max_products):
                    self.stdout.write(
                        f"\n{'='*60}")
                    self.stdout.write(
                        f"[INFO] PRODUKT {product_index + 1}/{max_products}")
                    self.stdout.write(
                        f"{'='*60}")

                    # Jeśli to nie pierwszy produkt, wróć do zapisanej listy z filtrami
                    if product_index > 0:
                        self.stdout.write(
                            f"\n[INFO] Wracanie do przefiltrowanej listy produktów przed produktem {product_index + 1}...")
                        browser.navigate_back_to_product_list(
                            filtered_list_url=filtered_list_url)
                        time.sleep(2)

                    # Otwórz kolejny nieprzetworzony produkt z listy (indeksy mogą się przesuwać)
                    try:
                        current_list_product_ids = browser.get_product_ids_from_list()
                        next_product_id = None
                        for pid in current_list_product_ids:
                            if pid not in processed_product_ids:
                                next_product_id = pid
                                break

                        if not next_product_id:
                            self.stdout.write(self.style.WARNING(
                                "[WARNING] Brak kolejnych produktów na liście do przetworzenia"))
                            break

                        target_index = current_list_product_ids.index(
                            next_product_id)
                        self.stdout.write(
                            f"[INFO] Wybrany produkt z listy: ID={next_product_id} (index={target_index})")

                        success = browser.open_product_from_list_by_index(
                            target_index)
                        if not success:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Nie udało się otworzyć produktu o indeksie {product_index}"))
                            continue
                        processed_product_ids.add(next_product_id)
                        self.stdout.write(self.style.SUCCESS(
                            f"[OK] Otworzono produkt {product_index + 1} z listy"))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(
                            f"[WARNING] Błąd podczas otwierania produktu {product_index + 1}: {e}"))
                        continue

                    try:
                        # Pobierz oryginalną nazwę produktu (potrzebna dla ASSIGN i CREATE)
                        try:
                            from selenium.webdriver.common.by import By
                            name_field = browser.driver.find_element(
                                By.ID, "id_name")
                            original_name = name_field.get_attribute("value")
                            if original_name:
                                browser._original_product_name = original_name
                                logger.info(
                                    f"Pobrano oryginalną nazwę produktu: {original_name}")
                                print(
                                    f"[DEBUG] Pobrano oryginalną nazwę produktu: {original_name}")
                        except Exception as e:
                            logger.warning(
                                f"Nie udało się pobrać oryginalnej nazwy produktu: {e}")
                            print(
                                f"[DEBUG] Nie udało się pobrać oryginalnej nazwy produktu: {e}")

                        # SCENARIUSZ ASSIGN: Sprawdź najpierw sugerowane produkty
                        self.stdout.write(
                            "\n[INFO] Sprawdzanie scenariusza ASSIGN (sugerowane produkty)...")
                        assign_result = browser.handle_assign_scenario(
                            brand_id=brand_id,
                            brand_name=brand.name if brand else None
                        )

                        if assign_result:
                            # Scenariusz ASSIGN się powiódł (znaleziono produkt z pokryciem 100% i przypisano)
                            self.stdout.write(self.style.SUCCESS(
                                "[OK] Scenariusz ASSIGN zakończony - produkt został przypisany do istniejącego produktu w MPD"))
                            self.stdout.write(
                                f"\n[OK] Produkt {product_index + 1}/{max_products} przetworzony pomyślnie (ASSIGN)")
                            # Scenariusz ASSIGN zakończony - metoda handle_assign_scenario już wróciła do listy
                            # Przejdź do następnego produktu (jeśli to nie ostatni)
                            continue
                        else:
                            # Brak sugerowanych produktów z pokryciem 100% - przejdź do scenariusza CREATE
                            self.stdout.write(
                                "[INFO] Brak sugerowanych produktów z pokryciem 100% - przechodzę do scenariusza CREATE")

                        # SCENARIUSZ CREATE: Wypełnij wszystkie pola i utwórz nowy produkt
                        # KROK 1: Edycja nazwy produktu
                        self.stdout.write(
                            "\n[INFO] KROK 1: Edycja nazwy produktu...")
                        try:
                            browser.update_product_name()
                            self.stdout.write(self.style.SUCCESS(
                                "[OK] Zaktualizowano nazwę produktu"))
                        except Exception as e_name:
                            self.stdout.write(self.style.ERROR(
                                f"[ERROR] Błąd podczas edycji nazwy: {e_name}"))
                            self.stdout.write(
                                "[ERROR] Kończę proces - nie można ulepszyć nazwy produktu")
                            raise

                        # KROK 2: Edycja opisu produktu
                        try:
                            self.stdout.write(
                                "\n[INFO] KROK 2: Edycja opisu produktu...")
                            enhanced_description = browser.update_product_description()
                            self.stdout.write(self.style.SUCCESS(
                                "[OK] Zaktualizowano opis produktu"))
                        except Exception as e_desc:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas edycji opisu: {e_desc}"))
                            enhanced_description = None

                        # KROK 3: Edycja krótkiego opisu
                        if enhanced_description:
                            try:
                                self.stdout.write(
                                    "\n[INFO] KROK 3: Edycja krótkiego opisu produktu...")
                                browser.update_product_short_description(
                                    enhanced_description)
                                self.stdout.write(self.style.SUCCESS(
                                    "[OK] Zaktualizowano krótki opis produktu"))
                            except Exception as e_short_desc:
                                self.stdout.write(self.style.WARNING(
                                    f"[WARNING] Błąd podczas edycji krótkiego opisu: {e_short_desc}"))

                        # KROK 4: Wyciągnij i zaznacz atrybuty z opisu
                        try:
                            self.stdout.write(
                                "\n[INFO] KROK 4: Wyciąganie atrybutów z opisu produktu...")
                            from web_agent.automation.ai_processor import AIProcessor
                            ai_processor = AIProcessor()

                            # Pobierz dostępne atrybuty z formularza
                            available_attributes = browser.get_available_attributes()

                            if available_attributes and enhanced_description:
                                # Wyciągnij atrybuty z opisu używając AI
                                attribute_ids = ai_processor.extract_attributes_from_description(
                                    enhanced_description,
                                    available_attributes
                                )

                                if attribute_ids:
                                    # Zaznacz atrybuty w formularzu
                                    browser.select_attributes(attribute_ids)
                                    self.stdout.write(self.style.SUCCESS(
                                        f"[OK] Zaznaczono {len(attribute_ids)} atrybutów z opisu"))
                                else:
                                    self.stdout.write(
                                        "[INFO] Nie znaleziono atrybutów w opisie produktu")
                            else:
                                self.stdout.write(
                                    "[INFO] Brak dostępnych atrybutów lub opisu do analizy")
                        except Exception as e_attrs:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas wyciągania atrybutów: {e_attrs}"))

                        # KROK 5: Zaznacz markę w dropdown
                        try:
                            self.stdout.write(
                                "\n[INFO] KROK 5: Zaznaczanie marki w dropdown...")
                            brand_result = browser.fill_mpd_brand()
                            if brand_result:
                                self.stdout.write(self.style.SUCCESS(
                                    f"[OK] Zaznaczono markę: {brand_result}"))
                            else:
                                self.stdout.write(self.style.WARNING(
                                    "[WARNING] Nie udało się zaznaczyć marki w dropdown"))
                        except Exception as e_brand:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas zaznaczania marki: {e_brand}"))

                        # KROK 6: Wybierz grupę rozmiarową na podstawie kategorii
                        try:
                            self.stdout.write(
                                "\n[INFO] KROK 6: Wybieranie grupy rozmiarowej...")
                            category_name_for_size = automation_filters.get(
                                'category_name') if automation_filters else category_name
                            browser.select_size_category(
                                category_name_for_size)
                            self.stdout.write(self.style.SUCCESS(
                                "[OK] Wybrano grupę rozmiarową"))
                        except Exception as e_size:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas wyboru grupy rozmiarowej: {e_size}"))

                        # KROK 7: Wybierz główny kolor (main_color_id) na podstawie wartości z pola id_color
                        try:
                            self.stdout.write(
                                "\n[INFO] KROK 7: Wybieranie głównego koloru (main_color_id)...")
                            color_result = browser.fill_main_color_from_product_color()
                            if color_result:
                                self.stdout.write(self.style.SUCCESS(
                                    f"[OK] Wybrano główny kolor: {color_result}"))
                            else:
                                self.stdout.write(self.style.WARNING(
                                    "[WARNING] Nie udało się wybrać głównego koloru"))
                        except Exception as e_color_main:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas wyboru głównego koloru: {e_color_main}"))

                        # KROK 8: Wyodrębnij i wypełnij kolor producenta (użyj zapisanej oryginalnej nazwy)
                        if hasattr(browser, '_original_product_name') and browser._original_product_name:
                            try:
                                self.stdout.write(
                                    "\n[INFO] KROK 8: Wyodrębnianie koloru producenta...")
                                browser.update_producer_color(
                                    browser._original_product_name,
                                    brand_id=brand_id,
                                    brand_name=brand.name if brand else None
                                )
                                self.stdout.write(self.style.SUCCESS(
                                    "[OK] Wypełniono kolor producenta"))
                            except Exception as e_color:
                                self.stdout.write(self.style.WARNING(
                                    f"[WARNING] Błąd podczas wyodrębniania koloru: {e_color}"))

                        # KROK 9: Wyodrębnij i wypełnij kod producenta (użyj zapisanej oryginalnej nazwy)
                        if hasattr(browser, '_original_product_name') and browser._original_product_name:
                            try:
                                self.stdout.write(
                                    "\n[INFO] KROK 9: Wyodrębnianie kodu producenta...")
                                browser.update_producer_code(
                                    browser._original_product_name
                                )
                                self.stdout.write(self.style.SUCCESS(
                                    "[OK] Wypełniono kod producenta"))
                            except Exception as e_code:
                                self.stdout.write(self.style.WARNING(
                                    f"[WARNING] Błąd podczas wyodrębniania kodu: {e_code}"))

                        # KROK 10: Ustaw placeholder w polu series_name (nie wypełniamy faktycznej wartości)
                        try:
                            self.stdout.write(
                                "\n[INFO] KROK 10: Ustawianie placeholder w polu series_name...")
                            series_result = browser.fill_series_name_placeholder()
                            if series_result:
                                self.stdout.write(self.style.SUCCESS(
                                    "[OK] Ustawiono placeholder w polu series_name"))
                            else:
                                self.stdout.write(self.style.WARNING(
                                    "[WARNING] Nie udało się ustawić placeholder w polu series_name"))
                        except Exception as e_series:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas ustawiania placeholder w polu series_name: {e_series}"))

                        # KROK 11: Zaznacz ścieżkę produktu (Dwuczęściowe)
                        try:
                            self.stdout.write(
                                "\n[INFO] KROK 11: Wybieranie ścieżki produktu...")
                            # value="5" dla Dwuczęściowe
                            browser.select_product_path(path_value="5")
                            self.stdout.write(self.style.SUCCESS(
                                "[OK] Wybrano ścieżkę produktu"))
                        except Exception as e_path:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas wyboru ścieżki produktu: {e_path}"))

                        # KROK 12: Wybierz jednostkę produktu (szt.)
                        try:
                            self.stdout.write(
                                "\n[INFO] KROK 12: Wybieranie jednostki produktu...")
                            # value="0" dla szt.
                            browser.select_unit(unit_value="0")
                            self.stdout.write(self.style.SUCCESS(
                                "[OK] Wybrano jednostkę produktu"))
                        except Exception as e_unit:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas wyboru jednostki produktu: {e_unit}"))

                        # KROK 13: Wypełnij materiały (skład) z szczegółów produktu - PRZED przejściem do MPD
                        # Pola szczegółów są w formularzu produktu matterhorn1, nie w MPD
                        try:
                            self.stdout.write(
                                "\n[INFO] KROK 13: Wyodrębnianie i wypełnianie materiałów...")
                            browser.fill_fabric_materials()
                            self.stdout.write(self.style.SUCCESS(
                                "[OK] Wypełniono materiały"))
                        except Exception as e_fabric:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas wypełniania materiałów: {e_fabric}"))

                        # KROK 14: Kliknij przycisk "Utwórz nowy produkt w MPD"
                        try:
                            self.stdout.write(
                                "\n[INFO] KROK 14: Klikanie przycisku 'Utwórz nowy produkt w MPD'...")

                            # Znajdź przycisk po ID
                            create_button = browser.wait.until(
                                EC.element_to_be_clickable(
                                    (By.ID, "create-mpd-product-btn"))
                            )
                            create_button.click()
                            self.stdout.write(self.style.SUCCESS(
                                "[OK] Kliknięto przycisk 'Utwórz nowy produkt w MPD'"))
                            # Czekaj na przetworzenie i ewentualne przekierowanie
                            time.sleep(3)

                            # Po utworzeniu produktu, sprawdź czy jesteśmy na stronie produktu czy już na liście
                            # Jeśli jesteśmy na stronie produktu, wróć do listy
                            try:
                                current_url = browser.driver.current_url
                                self.stdout.write(
                                    f"[DEBUG] URL po utworzeniu produktu: {current_url}")
                                if '/change/' in current_url:
                                    self.stdout.write(
                                        "[INFO] Po utworzeniu produktu - wracam do listy produktów")
                                    browser.navigate_back_to_product_list()
                                    time.sleep(2)
                                else:
                                    self.stdout.write(
                                        "[INFO] Po utworzeniu produktu - już jesteśmy na liście produktów")
                            except Exception as e_nav:
                                self.stdout.write(self.style.WARNING(
                                    f"[WARNING] Błąd podczas nawigacji po utworzeniu produktu: {e_nav}"))
                                import traceback
                                traceback.print_exc()
                        except NoSuchElementException:
                            self.stdout.write(
                                "[INFO] Produkt jest już zmapowany - przycisk 'Utwórz nowy produkt w MPD' nie istnieje")
                        except Exception as e_button:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas klikania przycisku: {e_button}"))

                    # ZAKOMENTOWANE: Utwórz produkt w MPD (przycisk "Utwórz nowy produkt w MPD")
                    # Wszystkie pola są już wypełnione w krokach 1-13, więc nie ma potrzeby ponownie wypełniać
                    # Jeśli przycisk istnieje, produkt nie jest zmapowany - klikamy go
                    # Jeśli przycisk nie istnieje, produkt jest już zmapowany - nie robimy nic
                    # try:
                    #     self.stdout.write(
                    #         "\n[INFO] Tworzę produkt w MPD...")
                    #     browser.create_mpd_product()
                    #     self.stdout.write(self.style.SUCCESS(
                    #         "[OK] Produkt został utworzony w MPD"))
                    # except NoSuchElementException:
                    #     self.stdout.write(
                    #         "[INFO] Produkt jest już zmapowany - przycisk 'Utwórz nowy produkt w MPD' nie istnieje")
                    # except Exception as e_save:
                    #     self.stdout.write(self.style.WARNING(
                    #         f"[WARNING] Błąd podczas tworzenia produktu w MPD: {e_save}"))

                        self.stdout.write(
                            f"\n[OK] Produkt {product_index + 1}/{max_products} przetworzony pomyślnie (CREATE)")
                        # Metoda już wróciła do listy po kliknięciu "Utwórz nowy produkt w MPD"
                        # Sprawdź czy faktycznie jesteśmy na liście przed przejściem do następnego produktu
                        try:
                            current_url_after = browser.driver.current_url
                            self.stdout.write(
                                f"[DEBUG] URL po CREATE: {current_url_after}")
                            if '/change/' in current_url_after:
                                self.stdout.write(
                                    "[WARNING] Nadal jesteśmy na stronie produktu - wracam do przefiltrowanej listy...")
                                browser.navigate_back_to_product_list(
                                    filtered_list_url=filtered_list_url)
                                time.sleep(2)
                            elif '/matterhorn1/product/' in current_url_after:
                                self.stdout.write(
                                    "[OK] Jesteśmy na liście produktów - gotowi do następnego produktu")
                            else:
                                self.stdout.write(
                                    "[WARNING] Nie jesteśmy ani na liście, ani na stronie produktu - wracam do przefiltrowanej listy...")
                                browser.navigate_back_to_product_list(
                                    filtered_list_url=filtered_list_url)
                                time.sleep(2)
                        except Exception as e_check:
                            self.stdout.write(self.style.WARNING(
                                f"[WARNING] Błąd podczas sprawdzania URL po CREATE: {e_check}"))
                            # Spróbuj wrócić do zapisanej listy mimo błędu
                            try:
                                browser.navigate_back_to_product_list(
                                    filtered_list_url=filtered_list_url)
                                time.sleep(2)
                            except:
                                pass

                    except Exception as e:
                        import traceback
                        self.stdout.write(self.style.ERROR(
                            f"[ERROR] Błąd podczas przetwarzania produktu {product_index + 1}: {e}"))
                        traceback.print_exc()
                        self.stdout.write(self.style.WARNING(
                            f"[WARNING] Błąd podczas przetwarzania produktu {product_index + 1}: {e}"))
                        # W przypadku błędu również wróć do zapisanej listy (jeśli to nie ostatni produkt)
                        if product_index < max_products - 1:
                            try:
                                browser.navigate_back_to_product_list(
                                    filtered_list_url=filtered_list_url)
                                time.sleep(2)
                            except:
                                pass
                        continue

                # Po przetworzeniu wszystkich produktów
                self.stdout.write(
                    f"\n{'='*60}")
                self.stdout.write(
                    f"[OK] Przetworzono {max_products} produktów")
                self.stdout.write(
                    f"{'='*60}")

            self.stdout.write(
                "\n[INFO] Przeglądarka pozostanie otwarta. Możesz teraz ręcznie przetwarzać produkty.")
            self.stdout.write(f"\n   AutomationRun ID: {automation_run.id}")
            # Pobierz port z base_url lub użyj domyślnego 8080
            port = '8080'
            if base_url:
                import re
                match = re.search(r':(\d+)', base_url)
                if match:
                    port = match.group(1)
            self.stdout.write(
                f"   Wyniki: http://localhost:{port}/admin/web_agent/automationrun/{automation_run.id}/\n")

            # Zostaw przeglądarkę otwartą - nie zamykaj!
            # Użytkownik może teraz ręcznie przetwarzać produkty

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Blad: {e}"))
            import traceback
            traceback.print_exc()
            automation_run.status = 'failed'
            automation_run.error_message = str(e)
            automation_run.save()
            if 'browser' in locals():
                browser.close_browser()
