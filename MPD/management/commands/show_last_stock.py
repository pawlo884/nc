from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = 'Wyświetla 10 ostatnich rekordów z tabeli stock_and_prices w bazie MPD.'

    def handle(self, *args, **options):
        with connections['MPD'].cursor() as cursor:
            cursor.execute('''
                SELECT id, variant_id, source_id, stock, price, currency, last_updated
                FROM stock_and_prices
                ORDER BY last_updated DESC
                LIMIT 10
            ''')
            rows = cursor.fetchall()
            if not rows:
                self.stdout.write(self.style.WARNING(
                    'Brak rekordów w tabeli.'))
            for row in rows:
                self.stdout.write(str(row))
