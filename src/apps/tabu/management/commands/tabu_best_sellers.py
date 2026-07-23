import csv
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone

logger = logging.getLogger(__name__)


def _tabu_db_alias():
    return 'zzz_tabu' if 'zzz_tabu' in settings.DATABASES else 'tabu'


# Zdarzenia masowego zerowania stanu (>100 produktów marki wyzerowanych tego samego
# dnia, średnio >8 szt./produkt) to sygnatura wygaszenia oferty przez dostawcę, nie
# sprzedaży detalicznej — patrz analogiczny przypadek w matterhorn1 (marka Teyli).
CONTAMINATION_CTE = """
    WITH suspect_groups AS (
        SELECT p.tabu_brand_fk_id AS brand_id, date(sh.timestamp) AS d
        FROM tabu_stock_history sh
        JOIN tabu_product_detail p ON p.api_id = sh.product_api_id
        WHERE sh.change_type = 'decrease' AND sh.new_stock = 0 AND sh.old_stock > 0
            AND sh.timestamp >= %(since_contamination)s
        GROUP BY 1, 2
        HAVING COUNT(DISTINCT sh.product_api_id) > 100
           AND SUM(ABS(sh.stock_change))::numeric / COUNT(DISTINCT sh.product_api_id) > 8
    )
"""

NOT_CONTAMINATED = """
    AND NOT EXISTS (
        SELECT 1 FROM suspect_groups sg
        WHERE sg.brand_id = p.tabu_brand_fk_id AND sg.d = date(sh.timestamp)
    )
"""

PRODUCT_QUERY = CONTAMINATION_CTE + """
    SELECT
        p.api_id, p.name AS product_name, b.name AS brand_name, c.name AS category_name,
        SUM(ABS(sh.stock_change)) AS total_sold, COUNT(*) AS decrease_events
    FROM tabu_stock_history sh
    JOIN tabu_product_detail p ON p.api_id = sh.product_api_id
    LEFT JOIN tabu_brand b ON b.id = p.tabu_brand_fk_id
    LEFT JOIN tabu_category c ON c.id = p.tabu_category_fk_id
    WHERE sh.change_type = 'decrease'
        AND sh.timestamp >= %(since)s
        {active_filter}
        {brand_filter}
        {category_filter}
        """ + NOT_CONTAMINATED + """
    GROUP BY p.api_id, p.name, b.name, c.name
    ORDER BY total_sold DESC, decrease_events DESC
    LIMIT %(limit)s
"""

BRAND_QUERY = CONTAMINATION_CTE + """
    SELECT
        b.name AS brand_name,
        SUM(ABS(sh.stock_change)) AS total_sold,
        COUNT(*) AS decrease_events,
        COUNT(DISTINCT sh.product_api_id) AS unique_products
    FROM tabu_stock_history sh
    JOIN tabu_product_detail p ON p.api_id = sh.product_api_id
    LEFT JOIN tabu_brand b ON b.id = p.tabu_brand_fk_id
    WHERE sh.change_type = 'decrease'
        AND sh.timestamp >= %(since)s
        {active_filter}
        """ + NOT_CONTAMINATED + """
    GROUP BY b.name
    ORDER BY total_sold DESC
    LIMIT %(limit)s
"""

CATEGORY_QUERY = CONTAMINATION_CTE + """
    SELECT
        c.name AS category_name, c.path AS category_path,
        SUM(ABS(sh.stock_change)) AS total_sold,
        COUNT(*) AS decrease_events,
        COUNT(DISTINCT sh.product_api_id) AS unique_products
    FROM tabu_stock_history sh
    JOIN tabu_product_detail p ON p.api_id = sh.product_api_id
    LEFT JOIN tabu_category c ON c.id = p.tabu_category_fk_id
    WHERE sh.change_type = 'decrease'
        AND sh.timestamp >= %(since)s
        {active_filter}
        {brand_filter}
        """ + NOT_CONTAMINATED + """
    GROUP BY c.name, c.path
    ORDER BY total_sold DESC
    LIMIT %(limit)s
"""


class Command(BaseCommand):
    """Ranking najlepiej sprzedających się produktów w tabu (analogia do matterhorn1).

    Sprzedaż jest przybliżana spadkami stanu magazynowego (change_type='decrease')
    w tabu_stock_history. Zdarzenia masowego zerowania stanu (wygaszanie oferty przez
    dostawcę) są wykluczane, żeby nie zafałszowały rankingu.
    """

    help = (
        'Ranking najlepiej sprzedających się produktów/marek/kategorii dla Tabu '
        '(na podstawie spadków stanu magazynowego w tabu_stock_history)'
    )

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=90,
                             help='Liczba dni wstecz (domyślnie 90)')
        parser.add_argument('--top', type=int, default=20,
                             help='Liczba pozycji w rankingu (domyślnie 20)')
        parser.add_argument('--group-by', choices=['product', 'brand', 'category'], default='product',
                             help='Poziom agregacji rankingu (domyślnie product)')
        parser.add_argument('--brand', type=str, default=None,
                             help='Filtruj po nazwie marki (dokładne dopasowanie)')
        parser.add_argument('--category', type=str, default=None,
                             help='Filtruj po nazwie kategorii (dokładne dopasowanie)')
        parser.add_argument('--active-only', action='store_true',
                             help='Uwzględnij tylko dostępne produkty (status_id=1)')
        parser.add_argument('--export', type=str, default=None,
                             help='Ścieżka do pliku CSV, do którego zapisać wynik')

    def handle(self, *args, **options):
        days = options['days']
        limit = options['top']
        group_by = options['group_by']
        brand = options['brand']
        category = options['category']
        active_only = options['active_only']
        export_path = options['export']

        since = timezone.now() - timezone.timedelta(days=days)
        since_contamination = timezone.now() - timezone.timedelta(days=400)
        params = {'since': since, 'since_contamination': since_contamination, 'limit': limit}

        active_filter = "AND p.status_id = 1" if active_only else ""
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
                active_filter=active_filter, brand_filter=brand_filter, category_filter=category_filter)
            headers = ['api_id', 'product_name', 'brand_name',
                       'category_name', 'total_sold', 'decrease_events']
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

        with connections[_tabu_db_alias()].cursor() as cursor:
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
