import csv
import logging

from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone

logger = logging.getLogger(__name__)


PRODUCT_QUERY = """
    SELECT
        p.product_uid,
        p.name AS product_name,
        b.name AS brand_name,
        c.name AS category_name,
        SUM(ABS(sh.stock_change)) AS total_sold,
        COUNT(*) AS decrease_events,
        MAX(sh.timestamp) AS last_sale
    FROM matterhorn1_stock_history sh
    JOIN product p ON p.product_uid = sh.product_uid
    LEFT JOIN brand b ON b.id = p.brand_id
    LEFT JOIN category c ON c.id = p.category_id
    WHERE sh.change_type = 'decrease'
        AND sh.timestamp >= %(since)s
        {active_filter}
        {brand_filter}
        {category_filter}
    GROUP BY p.product_uid, p.name, b.name, c.name
    ORDER BY total_sold DESC, decrease_events DESC
    LIMIT %(limit)s
"""

BRAND_QUERY = """
    SELECT
        b.name AS brand_name,
        SUM(ABS(sh.stock_change)) AS total_sold,
        COUNT(*) AS decrease_events,
        COUNT(DISTINCT sh.product_uid) AS unique_products
    FROM matterhorn1_stock_history sh
    JOIN product p ON p.product_uid = sh.product_uid
    LEFT JOIN brand b ON b.id = p.brand_id
    WHERE sh.change_type = 'decrease'
        AND sh.timestamp >= %(since)s
        {active_filter}
    GROUP BY b.name
    ORDER BY total_sold DESC
    LIMIT %(limit)s
"""

CATEGORY_QUERY = """
    SELECT
        c.name AS category_name,
        c.path AS category_path,
        SUM(ABS(sh.stock_change)) AS total_sold,
        COUNT(*) AS decrease_events,
        COUNT(DISTINCT sh.product_uid) AS unique_products
    FROM matterhorn1_stock_history sh
    JOIN product p ON p.product_uid = sh.product_uid
    LEFT JOIN category c ON c.id = p.category_id
    WHERE sh.change_type = 'decrease'
        AND sh.timestamp >= %(since)s
        {active_filter}
        {brand_filter}
    GROUP BY c.name, c.path
    ORDER BY total_sold DESC
    LIMIT %(limit)s
"""


class Command(BaseCommand):
    """Ranking najlepiej sprzedających się produktów w matterhorn1.

    Sprzedaż jest przybliżana spadkami stanu magazynowego (change_type='decrease')
    w matterhorn1_stock_history — nie ma tu danych o rzeczywistych zamówieniach.
    """

    help = (
        'Ranking najlepiej sprzedających się produktów/marek/kategorii dla Matterhorn '
        '(na podstawie spadków stanu magazynowego w matterhorn1_stock_history)'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=90,
            help='Liczba dni wstecz (domyślnie 90)'
        )
        parser.add_argument(
            '--top', type=int, default=20,
            help='Liczba pozycji w rankingu (domyślnie 20)'
        )
        parser.add_argument(
            '--group-by', choices=['product', 'brand', 'category'], default='product',
            help='Poziom agregacji rankingu (domyślnie product)'
        )
        parser.add_argument(
            '--brand', type=str, default=None,
            help='Filtruj po nazwie marki (dokładne dopasowanie)'
        )
        parser.add_argument(
            '--category', type=str, default=None,
            help='Filtruj po nazwie kategorii (dokładne dopasowanie)'
        )
        parser.add_argument(
            '--active-only', action='store_true',
            help='Uwzględnij tylko aktywne produkty'
        )
        parser.add_argument(
            '--export', type=str, default=None,
            help='Ścieżka do pliku CSV, do którego zapisać wynik'
        )

    def handle(self, *args, **options):
        days = options['days']
        limit = options['top']
        group_by = options['group_by']
        brand = options['brand']
        category = options['category']
        active_only = options['active_only']
        export_path = options['export']

        since = timezone.now() - timezone.timedelta(days=days)
        params = {'since': since, 'limit': limit}

        active_filter = "AND p.active = true" if active_only else ""
        brand_filter = ""
        category_filter = ""
        if brand:
            brand_filter = "AND b.name = %(brand)s"
            params['brand'] = brand
        if category:
            category_filter = "AND c.name = %(category)s"
            params['category'] = category

        if group_by == 'product':
            query = PRODUCT_QUERY.format(
                active_filter=active_filter,
                brand_filter=brand_filter,
                category_filter=category_filter,
            )
            headers = ['product_uid', 'product_name', 'brand_name',
                       'category_name', 'total_sold', 'decrease_events', 'last_sale']
        elif group_by == 'brand':
            if category_filter:
                self.stderr.write(
                    'Ostrzeżenie: --category jest ignorowany dla --group-by brand')
            query = BRAND_QUERY.format(active_filter=active_filter)
            headers = ['brand_name', 'total_sold',
                       'decrease_events', 'unique_products']
        else:  # category
            query = CATEGORY_QUERY.format(
                active_filter=active_filter, brand_filter=brand_filter)
            headers = ['category_name', 'category_path',
                       'total_sold', 'decrease_events', 'unique_products']

        with connections['matterhorn1'].cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        if not rows:
            self.stdout.write(self.style.WARNING(
                'Brak danych dla podanych filtrów.'))
            return

        self._print_table(headers, rows)

        if export_path:
            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
            self.stdout.write(self.style.SUCCESS(
                f'Zapisano {len(rows)} wierszy do {export_path}'))

    def _print_table(self, headers, rows):
        col_widths = [len(h) for h in headers]
        str_rows = [[str(v) for v in row] for row in rows]
        for row in str_rows:
            for i, val in enumerate(row):
                col_widths[i] = max(col_widths[i], len(val))

        def fmt_row(values):
            return '  '.join(v.ljust(col_widths[i]) for i, v in enumerate(values))

        self.stdout.write(fmt_row(headers))
        self.stdout.write('  '.join('-' * w for w in col_widths))
        for row in str_rows:
            self.stdout.write(fmt_row(row))
