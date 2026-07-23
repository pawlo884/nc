"""
Dane dla dashboardu bestsellerów w Django admin (matterhorn1).

Sprzedaż jest przybliżana spadkami stanu magazynowego (change_type='decrease')
w matterhorn1_stock_history. Zdarzenia masowego zerowania stanu (wygaszanie
oferty przez dostawcę — patrz przypadek marki Teyli) są wykluczane z liczb,
żeby nie zafałszowały rankingu.
"""
from django.db import connections
from django.urls import reverse
from django.utils import timezone


def _product_url(pk):
    return reverse('admin:matterhorn1_product_change', args=[pk])

SUSPECT_GROUPS_QUERY = """
    SELECT p.brand_id, date(sh.timestamp) AS d
    FROM matterhorn1_stock_history sh
    JOIN product p ON p.product_uid = sh.product_uid
    WHERE sh.change_type = 'decrease' AND sh.new_stock = 0 AND sh.old_stock > 0
        AND sh.timestamp >= %(since_contamination)s
    GROUP BY 1, 2
    HAVING COUNT(DISTINCT sh.product_uid) > 100
       AND SUM(ABS(sh.stock_change))::numeric / COUNT(DISTINCT sh.product_uid) > 8
"""
# suspect_groups liczone raz w get_dashboard_data i przekazywane dalej jako
# tablice (sg_brand_ids, sg_dates) — unikamy powtarzania tego skanu w każdym
# z kolejnych zapytań.
NOT_CONTAM = """
    AND NOT EXISTS (
        SELECT 1 FROM unnest(%(sg_brand_ids)s::int[], %(sg_dates)s::date[]) AS sg(brand_id, d)
        WHERE sg.brand_id = p.brand_id AND sg.d = date(sh.timestamp)
    )
"""


def _rows_to_dicts(cursor):
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _clean(s):
    return ' '.join(s.split()) if isinstance(s, str) else s


def _strip_brand_suffix(name, brand):
    name = _clean(name)
    suffix = f'- {brand}'
    if brand and name.endswith(suffix):
        name = name[:-len(suffix)].strip()
    return name


def get_dashboard_data(days=90):
    """Zwraca dane do dashboardu bestsellerów (top produkty/marki/kategorie,
    trend miesięczny, braki magazynowe, wygaszane marki)."""
    since = timezone.now() - timezone.timedelta(days=days)
    since_30 = timezone.now() - timezone.timedelta(days=30)
    since_contamination = timezone.now() - timezone.timedelta(days=400)
    params_base = {'since_contamination': since_contamination}

    with connections['matterhorn1'].cursor() as cur:
        cur.execute(SUSPECT_GROUPS_QUERY, params_base)
        suspect_rows = cur.fetchall()
        params_base['sg_brand_ids'] = [r[0] for r in suspect_rows]
        params_base['sg_dates'] = [r[1] for r in suspect_rows]

        cur.execute("""
            SELECT p.id AS pk, p.product_uid, p.name AS product_name, b.name AS brand_name, c.name AS category_name,
                   SUM(ABS(sh.stock_change)) AS total_sold, COUNT(*) AS decrease_events
            FROM matterhorn1_stock_history sh
            JOIN product p ON p.product_uid = sh.product_uid
            LEFT JOIN brand b ON b.id = p.brand_id
            LEFT JOIN category c ON c.id = p.category_id
            WHERE sh.change_type = 'decrease' AND sh.timestamp >= %(since)s
            """ + NOT_CONTAM + """
            GROUP BY p.id, p.product_uid, p.name, b.name, c.name
            ORDER BY total_sold DESC LIMIT 20
        """, {**params_base, 'since': since})
        top_products_raw = _rows_to_dicts(cur)

        cur.execute("""
            SELECT b.name AS brand_name, SUM(ABS(sh.stock_change)) AS total_sold,
                   COUNT(*) AS decrease_events, COUNT(DISTINCT sh.product_uid) AS unique_products
            FROM matterhorn1_stock_history sh
            JOIN product p ON p.product_uid = sh.product_uid
            LEFT JOIN brand b ON b.id = p.brand_id
            WHERE sh.change_type = 'decrease' AND sh.timestamp >= %(since)s
            """ + NOT_CONTAM + """
            GROUP BY b.name ORDER BY total_sold DESC LIMIT 12
        """, {**params_base, 'since': since})
        top_brands_raw = _rows_to_dicts(cur)

        cur.execute("""
            SELECT c.name AS category_name, SUM(ABS(sh.stock_change)) AS total_sold,
                   COUNT(*) AS decrease_events, COUNT(DISTINCT sh.product_uid) AS unique_products
            FROM matterhorn1_stock_history sh
            JOIN product p ON p.product_uid = sh.product_uid
            LEFT JOIN category c ON c.id = p.category_id
            WHERE sh.change_type = 'decrease' AND sh.timestamp >= %(since)s
            """ + NOT_CONTAM + """
            GROUP BY c.name ORDER BY total_sold DESC LIMIT 8
        """, {**params_base, 'since': since})
        top_categories_raw = _rows_to_dicts(cur)

        cur.execute("""
            SELECT to_char(date_trunc('month', sh.timestamp), 'YYYY-MM') AS month,
                   SUM(ABS(sh.stock_change)) AS total_sold
            FROM matterhorn1_stock_history sh
            JOIN product p ON p.product_uid = sh.product_uid
            WHERE sh.change_type = 'decrease' AND sh.timestamp >= %(since_contamination)s
            """ + NOT_CONTAM + """
            GROUP BY 1 ORDER BY 1
        """, params_base)
        monthly = [{'month': r['month'], 'sold': r['total_sold']} for r in _rows_to_dicts(cur)]

        cur.execute("""
            SELECT SUM(ABS(sh.stock_change)) AS total_sold, COUNT(DISTINCT sh.product_uid) AS uniq_products,
                   COUNT(DISTINCT b.id) AS uniq_brands
            FROM matterhorn1_stock_history sh
            JOIN product p ON p.product_uid = sh.product_uid
            LEFT JOIN brand b ON b.id = p.brand_id
            WHERE sh.change_type='decrease' AND sh.timestamp >= %(since)s
            """ + NOT_CONTAM, {**params_base, 'since': since})
        grand = _rows_to_dicts(cur)[0]

        cur.execute("""
            SELECT SUM(ABS(sh.stock_change)) AS total_sold
            FROM matterhorn1_stock_history sh
            JOIN product p ON p.product_uid = sh.product_uid
            WHERE sh.change_type='decrease' AND sh.timestamp >= %(since_30)s
            """ + NOT_CONTAM, {**params_base, 'since_30': since_30})
        sold_30d = _rows_to_dicts(cur)[0]['total_sold'] or 0

        cur.execute("""
            WITH sales_30d AS (
                SELECT sh.product_uid, SUM(ABS(sh.stock_change)) AS sold_30d
                FROM matterhorn1_stock_history sh
                JOIN product p ON p.product_uid = sh.product_uid
                WHERE sh.change_type = 'decrease' AND sh.timestamp >= %(since_30)s
                """ + NOT_CONTAM + """
                GROUP BY sh.product_uid
                HAVING SUM(ABS(sh.stock_change)) >= 15
            ),
            current_stock AS (
                SELECT pv.product_id, SUM(pv.stock) AS stock_now
                FROM productvariant pv GROUP BY pv.product_id
            )
            SELECT p.id AS pk, p.product_uid, p.name AS product_name, b.name AS brand_name,
                   s.sold_30d, COALESCE(cs.stock_now, 0) AS stock_now
            FROM sales_30d s
            JOIN product p ON p.product_uid = s.product_uid
            LEFT JOIN brand b ON b.id = p.brand_id
            LEFT JOIN current_stock cs ON cs.product_id = p.id
            WHERE p.active = true AND COALESCE(cs.stock_now, 0) = 0
            ORDER BY s.sold_30d DESC
        """, {**params_base, 'since_30': since_30})
        out_of_stock_raw = _rows_to_dicts(cur)

        cur.execute("""
            WITH sales_30d AS (
                SELECT sh.product_uid, SUM(ABS(sh.stock_change)) AS sold_30d
                FROM matterhorn1_stock_history sh
                JOIN product p ON p.product_uid = sh.product_uid
                WHERE sh.change_type = 'decrease' AND sh.timestamp >= %(since_30)s
                """ + NOT_CONTAM + """
                GROUP BY sh.product_uid
                HAVING SUM(ABS(sh.stock_change)) >= 15
            ),
            current_stock AS (
                SELECT pv.product_id, SUM(pv.stock) AS stock_now
                FROM productvariant pv GROUP BY pv.product_id
            )
            SELECT p.id AS pk, p.product_uid, p.name AS product_name, b.name AS brand_name,
                   s.sold_30d, cs.stock_now,
                   ROUND(cs.stock_now::numeric / (s.sold_30d::numeric/30), 1) AS days_left
            FROM sales_30d s
            JOIN product p ON p.product_uid = s.product_uid
            LEFT JOIN brand b ON b.id = p.brand_id
            JOIN current_stock cs ON cs.product_id = p.id
            WHERE p.active = true AND cs.stock_now > 0
                  AND cs.stock_now::numeric / (s.sold_30d::numeric/30) < 14
            ORDER BY days_left ASC
        """, {**params_base, 'since_30': since_30})
        low_stock_raw = _rows_to_dicts(cur)

        cur.execute("""
            SELECT DISTINCT b.id, b.name FROM brand b
            WHERE b.id = ANY(%(sg_brand_ids)s::int[])
        """, params_base)
        contaminated_brands = _rows_to_dicts(cur)

        discontinued, winding_down = [], []
        brand_ids = [cb['id'] for cb in contaminated_brands]
        if brand_ids:
            cur.execute("""
                SELECT p.brand_id, COUNT(DISTINCT p.id), COUNT(DISTINCT p.id) FILTER (WHERE p.active), SUM(pv.stock)
                FROM product p LEFT JOIN productvariant pv ON pv.product_id = p.id
                WHERE p.brand_id = ANY(%(brand_ids)s::int[])
                GROUP BY p.brand_id
            """, {'brand_ids': brand_ids})
            stats_by_brand = {row[0]: (row[1], row[2], row[3]) for row in cur.fetchall()}

            cur.execute("""
                SELECT p.brand_id, COUNT(*)
                FROM matterhorn1_stock_history sh
                JOIN product p ON p.product_uid = sh.product_uid
                WHERE p.brand_id = ANY(%(brand_ids)s::int[]) AND sh.change_type = 'increase'
                    AND sh.timestamp >= %(since)s
                GROUP BY p.brand_id
            """, {'brand_ids': brand_ids, 'since': since})
            increases_by_brand = dict(cur.fetchall())

            for cb in contaminated_brands:
                products, active, stock = stats_by_brand.get(cb['id'], (0, 0, 0))
                increases = increases_by_brand.get(cb['id'], 0)
                entry = {'brand': cb['name'], 'products': products, 'active': active or 0,
                         'stock_now': stock or 0, 'increases_90d': increases}
                if (active or 0) == 0 and (stock or 0) == 0:
                    discontinued.append(entry)
                elif products and (active or 0) / products < 0.15:
                    winding_down.append(entry)
        discontinued.sort(key=lambda b: b['products'], reverse=True)
        winding_down.sort(key=lambda b: b['active'] / b['products'] if b['products'] else 0)

    def fmt_restock(items):
        out = []
        for i in items[:14]:
            item = {
                'name': _strip_brand_suffix(i['product_name'], i['brand_name']),
                'brand': i['brand_name'], 'sold30': i['sold_30d'], 'stock': i['stock_now'],
                'url': _product_url(i['pk']),
            }
            if 'days_left' in i:
                item['days_left'] = float(i['days_left'])
            out.append(item)
        return out

    top_products = [{
        'name': _strip_brand_suffix(p['product_name'], p['brand_name']),
        'brand': p['brand_name'], 'category': _clean(p['category_name']), 'sold': p['total_sold'],
        'url': _product_url(p['pk']),
    } for p in top_products_raw[:12]]

    top_products_table = [{
        'name': _strip_brand_suffix(p['product_name'], p['brand_name']),
        'brand': p['brand_name'], 'category': _clean(p['category_name']),
        'sold': p['total_sold'], 'events': p['decrease_events'],
        'url': _product_url(p['pk']),
    } for p in top_products_raw]

    return {
        'stats': {
            'sold_90d': grand['total_sold'] or 0,
            'unique_products_90d': grand['uniq_products'] or 0,
            'active_brands_90d': grand['uniq_brands'] or 0,
            'sold_30d': sold_30d,
            'out_of_stock_count': len(out_of_stock_raw),
            'low_stock_count': len(low_stock_raw),
        },
        'top_products': top_products,
        'top_products_table': top_products_table,
        'top_brands': [{'name': b['brand_name'] or 'Nieznana', 'sold': b['total_sold'], 'products': b['unique_products']}
                        for b in top_brands_raw],
        'top_categories': [{'name': _clean(c['category_name']) or 'Nieznana', 'sold': c['total_sold'], 'products': c['unique_products']}
                            for c in top_categories_raw],
        'monthly': monthly,
        'out_of_stock': fmt_restock(out_of_stock_raw),
        'low_stock': fmt_restock(low_stock_raw),
        'discontinued_brands': discontinued,
        'winding_down_brands': winding_down,
        'days': days,
    }
