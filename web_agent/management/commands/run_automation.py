"""
Management command do uruchomienia automatyzacji wypełniania formularzy MPD
"""
from django.core.management.base import BaseCommand
from web_agent.automation.browser_automation import BrowserAutomation
from web_agent.automation.ai_processor import AIProcessor
from web_agent.automation.product_processor import ProductProcessor
from web_agent.models import AutomationRun, ProductProcessingLog
from matterhorn1.models import Product, Brand, Category
import os


class Command(BaseCommand):
    help = 'Uruchom automatyzację wypełniania formularzy MPD'

    def add_arguments(self, parser):
        parser.add_argument('--brand', type=str, required=True, help='Nazwa marki')
        parser.add_argument('--category', type=str, help='Nazwa kategorii')
        parser.add_argument('--limit', type=int, default=5, help='Maksymalna liczba produktów')

    def handle(self, *args, **options):
        brand_name = options['brand']
        category_name = options.get('category')
        limit = options['limit']

        self.stdout.write(f"\nAUTOMATYZACJA MPD")
        self.stdout.write(f"   Marka: {brand_name}")
        self.stdout.write(f"   Kategoria: {category_name or 'Wszystkie'}")
        self.stdout.write(f"   Limit: {limit}\n")

        # Znajdź brand i category ID
        try:
            brand = Brand.objects.using('matterhorn1').get(name__iexact=brand_name)
            brand_id = int(brand.brand_id)
            self.stdout.write(f"[OK] Znaleziono marke: {brand.name} (ID: {brand_id})")
        except Brand.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"[ERROR] Nie znaleziono marki: {brand_name}"))
            return

        category_id = None
        if category_name:
            try:
                category = Category.objects.using('matterhorn1').filter(name__icontains=category_name).first()
                if category:
                    category_id = int(category.category_id)
                    self.stdout.write(f"[OK] Znaleziono kategorie: {category.name} (ID: {category_id})")
                else:
                    self.stdout.write(self.style.WARNING(f"[WARNING] Nie znaleziono kategorii: {category_name}, uzywam wszystkich"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARNING] Blad podczas wyszukiwania kategorii: {e}, uzywam wszystkich"))

        # Utwórz AutomationRun
        automation_run = AutomationRun.objects.using('zzz_default').create(
            status='running',
            brand_id=brand_id,
            category_id=category_id,
            filters={'active': True, 'is_mapped': False}
        )
        self.stdout.write(f"\n[OK] Utworzono AutomationRun ID: {automation_run.id}\n")

        # Konfiguracja
        base_url = os.getenv('WEB_AGENT_BASE_URL', 'http://localhost:8000')
        admin_username = os.getenv('DJANGO_ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('DJANGO_ADMIN_PASSWORD', '')
        openai_key = os.getenv('OPENAI_API_KEY', '')

        if not admin_password or not openai_key:
            self.stdout.write(self.style.ERROR("[ERROR] Brak DJANGO_ADMIN_PASSWORD lub OPENAI_API_KEY w .env.dev"))
            automation_run.status = 'failed'
            automation_run.error_message = "Brak konfiguracji"
            automation_run.save(using='zzz_default')
            return

        try:
            # Inicjalizuj komponenty
            browser = BrowserAutomation(base_url, admin_username, admin_password, headless=False)
            ai = AIProcessor(openai_key)
            processor = ProductProcessor(browser, ai, automation_run)

            # Uruchom przeglądarkę
            browser.start_browser()
            if not browser.login_admin():
                raise Exception("Nie udało się zalogować")

            # Pobierz produkty
            products = processor.get_products_to_process(
                brand_id=brand_id,
                category_id=category_id,
                limit=limit,
                filters={'active': True, 'is_mapped': False}
            )

            if not products:
                self.stdout.write(self.style.WARNING("[WARNING] Brak produktow do przetworzenia"))
                automation_run.status = 'completed'
                automation_run.save(using='zzz_default')
                return

            self.stdout.write(f"\n[INFO] Znaleziono {len(products)} produktow do przetworzenia\n")

            # Przetwarzaj
            for i, product in enumerate(products, 1):
                self.stdout.write(f"\n{'='*70}")
                self.stdout.write(f"Produkt {i}/{len(products)}: {product.name[:60]}...")
                self.stdout.write(f"{'='*70}")

                success = processor.process_product(product)
                if success:
                    self.stdout.write(self.style.SUCCESS(f"[OK] Sukces!"))
                else:
                    self.stdout.write(self.style.ERROR(f"[ERROR] Blad"))

            # Zakończ
            automation_run.status = 'completed'
            automation_run.save(using='zzz_default')

            self.stdout.write(f"\n\n[OK] AUTOMATYZACJA ZAKONCZONA!")
            self.stdout.write(f"   Przetworzono: {automation_run.products_processed}")
            self.stdout.write(f"   Sukcesow: {automation_run.products_success}")
            self.stdout.write(f"   Bledow: {automation_run.products_failed}")
            self.stdout.write(f"\n   Wyniki: http://localhost:8000/admin/web_agent/automationrun/{automation_run.id}/\n")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Blad: {e}"))
            import traceback
            traceback.print_exc()
            automation_run.status = 'failed'
            automation_run.error_message = str(e)
            automation_run.save(using='zzz_default')
        finally:
            if 'browser' in locals():
                browser.stop_browser()

