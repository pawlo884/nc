"""
Usuwa wszystkie dane Tabu z bazy.
Użycie przed pełnym reimportem (import_tabu_by_id).
Użycie:
  python manage.py clear_tabu_data --settings=core.settings.dev
  python manage.py clear_tabu_data --keep-logs --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand
from django.db import router

from tabu.models import ApiSyncLog, Brand, Category, StockHistory, TabuProduct


class Command(BaseCommand):
    help = 'Usuwa wszystkie dane Tabu z bazy (produkty, warianty, zdjęcia, historia, brandy, kategorie)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-logs',
            action='store_true',
            help='Zachowaj logi synchronizacji (ApiSyncLog)',
        )

    def handle(self, *args, **options):
        db = router.db_for_write(TabuProduct)

        self.stdout.write('Usuwanie danych Tabu...')

        count_sh = StockHistory.objects.using(db).count()
        StockHistory.objects.using(db).all().delete()
        self.stdout.write(f'  StockHistory: usunięto {count_sh}')

        count_prod = TabuProduct.objects.using(db).count()
        TabuProduct.objects.using(db).all().delete()
        self.stdout.write(f'  TabuProduct (i CASCADE: warianty, zdjęcia): usunięto {count_prod}')

        count_cat = Category.objects.using(db).count()
        Category.objects.using(db).all().delete()
        self.stdout.write(f'  Category: usunięto {count_cat}')

        count_brand = Brand.objects.using(db).count()
        Brand.objects.using(db).all().delete()
        self.stdout.write(f'  Brand: usunięto {count_brand}')

        if not options.get('keep_logs'):
            count_logs = ApiSyncLog.objects.using(db).count()
            ApiSyncLog.objects.using(db).all().delete()
            self.stdout.write(f'  ApiSyncLog: usunięto {count_logs}')
        else:
            self.stdout.write('  ApiSyncLog: zachowano (--keep-logs)')

        self.stdout.write(self.style.SUCCESS('\n✅ Baza Tabu wyczyszczona.'))
