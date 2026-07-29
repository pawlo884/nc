"""
Usuwa wszystkie dane Mada z bazy. Użycie przed pełnym reimportem.

Użycie:
  python manage.py clear_mada_data --settings=core.settings.dev
  python manage.py clear_mada_data --keep-logs --settings=core.settings.dev
"""
from django.core.management.base import BaseCommand
from django.db import router

from mada.models import ApiSyncLog, Brand, Category, MadaProduct, StockHistory


class Command(BaseCommand):
    help = 'Usuwa wszystkie dane Mada z bazy (produkty, warianty, zdjęcia, historia, brandy, kategorie)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-logs',
            action='store_true',
            help='Zachowaj logi synchronizacji (ApiSyncLog)',
        )

    def handle(self, *args, **options):
        db = router.db_for_write(MadaProduct)

        self.stdout.write('Usuwanie danych Mada...')

        count_sh = StockHistory.objects.using(db).count()
        StockHistory.objects.using(db).all().delete()
        self.stdout.write(f'  StockHistory: usunięto {count_sh}')

        count_prod = MadaProduct.objects.using(db).count()
        MadaProduct.objects.using(db).all().delete()
        self.stdout.write(f'  MadaProduct (i CASCADE: warianty, zdjęcia): usunięto {count_prod}')

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

        self.stdout.write(self.style.SUCCESS('\nBaza Mada wyczyszczona.'))
