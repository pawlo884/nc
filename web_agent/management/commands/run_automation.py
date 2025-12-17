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
                brand = Brand.objects.using(
                    'matterhorn1').get(name__iexact=brand_name)
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
                category = Category.objects.using('matterhorn1').filter(
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

            # Otwórz pierwszy produkt z listy (domyślnie 1)
            if max_products and max_products > 0:
                self.stdout.write(
                    f"\n[INFO] Otwieranie pierwszego produktu z listy (max: {max_products})...")
                try:
                    browser.open_first_product_from_list()
                    self.stdout.write(self.style.SUCCESS(
                        "[OK] Otworzono pierwszy produkt z listy"))

                    # KROK 1: Edycja nazwy produktu
                    self.stdout.write("\n[INFO] KROK 1: Edycja nazwy produktu...")
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
                        self.stdout.write("\n[INFO] KROK 2: Edycja opisu produktu...")
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
                            self.stdout.write("\n[INFO] KROK 3: Edycja krótkiego opisu produktu...")
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
                        browser.select_size_category(category_name_for_size)
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
                            EC.element_to_be_clickable((By.ID, "create-mpd-product-btn"))
                        )
                        create_button.click()
                        self.stdout.write(self.style.SUCCESS(
                            "[OK] Kliknięto przycisk 'Utwórz nowy produkt w MPD'"))
                        time.sleep(2)  # Czekaj na przetworzenie
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

                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"[WARNING] Nie udało się otworzyć produktu: {e}"))

            self.stdout.write(
                "[INFO] Przeglądarka pozostanie otwarta. Możesz teraz ręcznie przetwarzać produkty.")
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
