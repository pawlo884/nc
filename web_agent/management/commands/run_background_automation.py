"""
Management command do uruchomienia automatyzacji w tle (bez przeglądarki)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from web_agent.automation.background_automation import BackgroundAutomation
from web_agent.automation.ai_processor import AIProcessor
from web_agent.models import AutomationRun, BrandConfig
from matterhorn1.models import Brand, Category
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Uruchom automatyzację wypełniania formularzy MPD w tle (bez przeglądarki)'

    def add_arguments(self, parser):
        parser.add_argument('--brand', type=str, help='Nazwa marki (opcjonalne)')
        parser.add_argument('--category', type=str, help='Nazwa kategorii (opcjonalne)')
        parser.add_argument('--active', type=str, help='Filtr active (true/false, opcjonalne)')
        parser.add_argument('--is_mapped', type=str, help='Filtr is_mapped (true/false, opcjonalne)')
        parser.add_argument('--max', type=int, default=1, help='Maksymalna liczba produktów (domyślnie: 1)')

    def handle(self, *args, **options):
        brand_name = options.get('brand')
        category_name = options.get('category')
        max_products = options.get('max')

        # Konwertuj stringi na boolean
        active_filter = None
        if options.get('active'):
            active_filter = options.get('active').lower() in ('true', '1', 'yes', 'tak')

        is_mapped_filter = None
        if options.get('is_mapped'):
            is_mapped_filter = options.get('is_mapped').lower() in ('true', '1', 'yes', 'tak')

        self.stdout.write(f"\nURUCHOMIENIE AGENTA W TLE (BEZ PRZEGLĄDARKI)")
        self.stdout.write(f"   Marka: {brand_name or 'Wszystkie'}")
        self.stdout.write(f"   Kategoria: {category_name or 'Wszystkie'}")
        if active_filter is not None:
            self.stdout.write(f"   Active: {active_filter}")
        if is_mapped_filter is not None:
            self.stdout.write(f"   Is Mapped: {is_mapped_filter}")
        self.stdout.write("")

        # Znajdź brand i category ID (ta sama logika co w run_automation.py)
        brand_id = None
        brand = None
        brand_config = None
        if brand_name:
            try:
                brand = Brand.objects.get(name__iexact=brand_name)
                brand_id = int(brand.brand_id)
                self.stdout.write(f"[OK] Znaleziono markę: {brand.name} (ID: {brand_id})")

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
                category = Category.objects.filter(
                    name__icontains=category_name).first()
                if category:
                    category_id = int(category.category_id)
                    self.stdout.write(
                        f"[OK] Znaleziono kategorię: {category.name} (ID: {category_id})")
                else:
                    self.stdout.write(self.style.WARNING(
                        f"[WARNING] Nie znaleziono kategorii: {category_name}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"[WARNING] Błąd podczas wyszukiwania kategorii: {e}"))

        # Utwórz AutomationRun (ta sama logika)
        filters = {}
        if active_filter is not None:
            filters['active'] = active_filter
        elif brand_config and brand_config.default_active_filter is not None:
            filters['active'] = brand_config.default_active_filter
            self.stdout.write(
                f"[INFO] Użyto domyślnego filtra active z konfiguracji: {brand_config.default_active_filter}")
        else:
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
            filters['is_mapped'] = False
            self.stdout.write(
                "[INFO] Użyto globalnego domyślnego filtra is_mapped: False")

        automation_run = AutomationRun.objects.create(
            status='running',
            brand_id=brand_id,
            category_id=category_id,
            filters=filters
        )
        self.stdout.write(f"\n[OK] Utworzono AutomationRun ID: {automation_run.id}\n")

        try:
            # Inicjalizuj automatyzację w tle
            automation = BackgroundAutomation()
            ai_processor = AIProcessor()

            # Przygotuj filtry
            automation_filters = {}
            if brand_id and brand:
                automation_filters['brand_id'] = brand_id
                automation_filters['brand_name'] = brand.name

            if category_id:
                automation_filters['category_id'] = category_id
                automation_filters['category_name'] = category_name
            elif category_name:
                automation_filters['category_name'] = category_name

            automation_filters['active'] = filters['active']
            automation_filters['is_mapped'] = filters['is_mapped']

            # Pobierz produkty z bazy (zamiast navigate_to_product_list)
            self.stdout.write(f"\n[INFO] Pobieranie produktów z bazy danych...")
            products = automation.get_products_by_filters(automation_filters)
            
            if not products:
                self.stdout.write(self.style.WARNING(
                    "[WARNING] Brak produktów do przetworzenia"))
                automation_run.status = 'completed'
                automation_run.save()
                return

            self.stdout.write(f"[OK] Znaleziono {len(products)} produktów")
            
            # Przetwarzaj produkty (max_products)
            processed_count = 0
            for idx, product in enumerate(products[:max_products]):
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"[INFO] PRODUKT {idx + 1}/{min(max_products, len(products))}")
                self.stdout.write(f"{'='*60}")

                try:
                    product_id = product.id
                    product_data = automation.get_product_from_database(product_id)
                    
                    if not product_data:
                        self.stdout.write(self.style.WARNING(
                            f"[WARNING] Nie udało się pobrać danych produktu {product_id}"))
                        continue

                    # Zapisz oryginalną nazwę
                    automation._original_product_name = product_data.get('name', '')

                    # SCENARIUSZ ASSIGN: Sprawdź najpierw sugerowane produkty
                    self.stdout.write(
                        "\n[INFO] Sprawdzanie scenariusza ASSIGN (sugerowane produkty)...")
                    assign_result = automation.handle_assign_scenario(
                        product_id=product_id,
                        brand_id=brand_id,
                        brand_name=brand.name if brand else None
                    )

                    if assign_result:
                        self.stdout.write(self.style.SUCCESS(
                            "[OK] Scenariusz ASSIGN zakończony - produkt został przypisany"))
                        automation_run.products_processed += 1
                        automation_run.products_success += 1
                        automation_run.save(update_fields=[
                            'products_processed', 'products_success'
                        ])
                        processed_count += 1
                        continue

                    # SCENARIUSZ CREATE: Utwórz nowy produkt w MPD
                    self.stdout.write(
                        "[INFO] Brak sugerowanych produktów z pokryciem 100% - przechodzę do scenariusza CREATE")

                    result = automation.create_mpd_product(
                        product_id=product_id,
                        product_data=product_data,
                        brand_id=brand_id,
                        brand_name=brand.name if brand else None
                    )

                    if result['success']:
                        self.stdout.write(self.style.SUCCESS(
                            f"[OK] Utworzono produkt MPD (ID: {result['mpd_product_id']})"))
                        automation_run.products_processed += 1
                        automation_run.products_success += 1
                        processed_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(
                            f"[ERROR] Błąd: {result['error_message']}"))
                        automation_run.products_processed += 1
                        automation_run.products_failed += 1
                        automation_run.error_message = result['error_message']

                    automation_run.save(update_fields=[
                        'products_processed', 'products_success',
                        'products_failed', 'error_message'
                    ])

                except Exception as e:
                    import traceback
                    self.stdout.write(self.style.ERROR(
                        f"[ERROR] Błąd podczas przetwarzania produktu {idx + 1}: {e}"))
                    traceback.print_exc()
                    automation_run.products_processed += 1
                    automation_run.products_failed += 1
                    automation_run.error_message = str(e)
                    automation_run.save(update_fields=[
                        'products_processed', 'products_failed', 'error_message'
                    ])

            # Zakończ AutomationRun
            automation_run.status = 'completed'
            automation_run.completed_at = timezone.now()
            automation_run.save(update_fields=['status', 'completed_at'])

            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"[OK] Przetworzono {processed_count} produktów")
            self.stdout.write(f"{'='*60}")
            self.stdout.write(f"\n   AutomationRun ID: {automation_run.id}")
            self.stdout.write(f"   Wyniki w admin: /admin/web_agent/automationrun/{automation_run.id}/\n")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Błąd: {e}"))
            import traceback
            traceback.print_exc()
            automation_run.status = 'failed'
            automation_run.error_message = str(e)
            automation_run.completed_at = timezone.now()
            automation_run.save()


