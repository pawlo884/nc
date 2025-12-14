"""
Management command do uruchomienia automatyzacji wypełniania formularzy MPD
"""
from django.core.management.base import BaseCommand
from web_agent.automation.browser_automation import BrowserAutomation
from web_agent.models import AutomationRun, BrandConfig
from matterhorn1.models import Brand, Category
from selenium.common.exceptions import NoSuchElementException
import os


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
        filters = {}
        if active_filter is not None:
            filters['active'] = active_filter
        elif brand_config and brand_config.default_active_filter is not None:
            filters['active'] = brand_config.default_active_filter
            self.stdout.write(
                f"[INFO] Użyto domyślnego filtra active z konfiguracji: {brand_config.default_active_filter}")

        if is_mapped_filter is not None:
            filters['is_mapped'] = is_mapped_filter
        elif brand_config and brand_config.default_is_mapped_filter is not None:
            filters['is_mapped'] = brand_config.default_is_mapped_filter
            self.stdout.write(
                f"[INFO] Użyto domyślnego filtra is_mapped z konfiguracji: {brand_config.default_is_mapped_filter}")

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

            if active_filter is not None:
                automation_filters['active'] = active_filter
                self.stdout.write(f"[INFO] Filtr active: {active_filter}")

            if is_mapped_filter is not None:
                automation_filters['is_mapped'] = is_mapped_filter
                self.stdout.write(
                    f"[INFO] Filtr is_mapped: {is_mapped_filter}")

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

                    # Edytuj pola produktu (nazwa, opis, krótki opis)
                    self.stdout.write("\n[INFO] Edycja pól produktu...")
                    try:
                        browser.update_product_name()
                        self.stdout.write(self.style.SUCCESS(
                            "[OK] Zaktualizowano nazwę produktu"))
                    except Exception as e_name:
                        self.stdout.write(self.style.WARNING(
                            f"[WARNING] Błąd podczas edycji nazwy: {e_name}"))

                    try:
                        enhanced_description = browser.update_product_description()
                        self.stdout.write(self.style.SUCCESS(
                            "[OK] Zaktualizowano opis produktu"))

                        # Edytuj krótki opis jeśli długi opis został wygenerowany
                        if enhanced_description:
                            try:
                                browser.update_product_short_description(
                                    enhanced_description)
                                self.stdout.write(self.style.SUCCESS(
                                    "[OK] Zaktualizowano krótki opis produktu"))
                            except Exception as e_short_desc:
                                self.stdout.write(self.style.WARNING(
                                    f"[WARNING] Błąd podczas edycji krótkiego opisu: {e_short_desc}"))
                    except Exception as e_desc:
                        self.stdout.write(self.style.WARNING(
                            f"[WARNING] Błąd podczas edycji opisu: {e_desc}"))

                    # Utwórz produkt w MPD (przycisk "Utwórz nowy produkt w MPD")
                    # Jeśli przycisk istnieje, produkt nie jest zmapowany - klikamy go
                    # Jeśli przycisk nie istnieje, produkt jest już zmapowany - nie robimy nic
                    try:
                        self.stdout.write(
                            "\n[INFO] Tworzę produkt w MPD...")
                        browser.create_mpd_product()
                        self.stdout.write(self.style.SUCCESS(
                            "[OK] Produkt został utworzony w MPD"))
                    except NoSuchElementException:
                        self.stdout.write(
                            "[INFO] Produkt jest już zmapowany - przycisk 'Utwórz nowy produkt w MPD' nie istnieje")
                    except Exception as e_save:
                        self.stdout.write(self.style.WARNING(
                            f"[WARNING] Błąd podczas tworzenia produktu w MPD: {e_save}"))

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
