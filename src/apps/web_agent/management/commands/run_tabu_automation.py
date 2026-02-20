"""
Uruchomienie automatyzacji Tabu → MPD z filtrami po nazwie marki i kategorii.
Użycie:
  python manage.py run_tabu_automation --brand ava --category dwuczesciowe --settings=nc.settings.dev
  python manage.py run_tabu_automation --brand ava --settings=nc.settings.dev
  python manage.py run_tabu_automation --dry-run --brand ava --category dwuczesciowe --settings=nc.settings.dev
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Uruchom automatyzację dodawania produktów z Tabu do MPD (marka/kategoria po nazwie)'

    def add_arguments(self, parser):
        parser.add_argument('--brand', type=str, help='Nazwa marki (np. ava) – dopasowanie po zawieraniu')
        parser.add_argument('--category', type=str, help='Nazwa kategorii (np. dwuczesciowe) – dopasowanie po zawieraniu')
        parser.add_argument('--dry-run', action='store_true', help='Tylko pokaż liczbę produktów do przetworzenia, nie uruchamiaj taska')
        parser.add_argument('--max', type=int, default=500, help='Maks. liczba produktów (domyślnie 500)')

    def handle(self, *args, **options):
        brand_name = (options.get('brand') or '').strip()
        category_name = (options.get('category') or '').strip()
        dry_run = options.get('dry_run', False)
        max_products = options.get('max', 500)

        from tabu.models import TabuProduct, Brand, Category
        from web_agent.models import AutomationRun
        from web_agent.tasks import automate_tabu_to_mpd

        brand_id = None
        category_id = None

        if brand_name:
            brand = Brand.objects.filter(name__icontains=brand_name).first()
            if not brand:
                self.stdout.write(self.style.ERROR(f'Nie znaleziono marki zawierającej "{brand_name}" w Tabu.'))
                return
            brand_id = brand.id
            self.stdout.write(f'Marka: {brand.name} (id={brand_id})')
        else:
            self.stdout.write('Marka: wszystkie')

        if category_name:
            category = Category.objects.filter(name__icontains=category_name).first()
            if not category:
                self.stdout.write(self.style.ERROR(f'Nie znaleziono kategorii zawierającej "{category_name}" w Tabu.'))
                return
            category_id = category.id
            self.stdout.write(f'Kategoria: {category.name} (id={category_id})')
        else:
            self.stdout.write('Kategoria: wszystkie')

        qs = TabuProduct.objects.filter(mapped_product_uid__isnull=True)
        if brand_id is not None:
            qs = qs.filter(brand_id=brand_id)
        if category_id is not None:
            qs = qs.filter(category_id=category_id)
        count = qs.count()
        product_ids = list(qs.values_list('id', flat=True)[:max_products])

        self.stdout.write(f'Produktów Tabu do dodania (mapped_product_uid=NULL): {count} (weźmiemy max {len(product_ids)})')

        if dry_run:
            if product_ids:
                self.stdout.write(self.style.SUCCESS(f'[DRY-RUN] Uruchomienie przetworzyłoby {len(product_ids)} produktów.'))
                for pid in product_ids[:5]:
                    p = TabuProduct.objects.filter(pk=pid).first()
                    if p:
                        self.stdout.write(f'  - {p.name} (id={pid})')
                if len(product_ids) > 5:
                    self.stdout.write(f'  ... i {len(product_ids) - 5} innych')
            else:
                self.stdout.write('[DRY-RUN] Brak produktów do przetworzenia.')
            return

        if not product_ids:
            self.stdout.write(self.style.WARNING('Brak produktów do przetworzenia.'))
            return

        run = AutomationRun.objects.create(
            status='running',
            source='tabu',
            brand_id=brand_id,
            category_id=category_id,
            filters={'brand_id': brand_id, 'category_id': category_id},
        )
        self.stdout.write(f'Utworzono AutomationRun id={run.id} (source=tabu). Uruchamiam task...')

        # Uruchom task synchronicznie (apply), żeby zobaczyć wynik w terminalu
        result = automate_tabu_to_mpd.apply(
            kwargs={
                'brand_id': brand_id,
                'category_id': category_id,
                'filters': {'brand_id': brand_id, 'category_id': category_id},
                'automation_run_id': run.id,
            }
        )
        if result.successful():
            out = result.get()
            self.stdout.write(self.style.SUCCESS(
                f'Zakończono: przetworzono={out.get("products_processed", 0)}, '
                f'sukces={out.get("products_success", 0)}, błędy={out.get("products_failed", 0)}'
            ))
        else:
            self.stdout.write(self.style.ERROR(f'Błąd: {result.result}'))
        self.stdout.write(f'Szczegóły: /admin/web_agent/automationrun/{run.id}/change/')
