import logging

from django.db import connections
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def fuzzy_suggest_mpd_products(product_name, brand_name, *, mpd_db_alias, limit=5):
    """Ocenia podobieństwo produktów MPD (przefiltrowanych po nazwie marki) do
    `product_name` przez token_sort_ratio; zwraca top `limit` jako listę dictów
    z id/name/brand/similarity/suggested_in_query, albo [] przy braku danych/błędzie."""
    if not brand_name or not product_name:
        return []
    try:
        with connections[mpd_db_alias].cursor() as cursor:
            cursor.execute(
                "SELECT p.id, p.name, b.name AS brand_name FROM products p "
                "LEFT JOIN brands b ON p.brand_id = b.id WHERE b.name = %s ORDER BY p.name",
                [brand_name],
            )
            rows = cursor.fetchall()

        query_words = set(product_name.lower().replace('(', '').replace(')', '').replace('-', ' ').split())
        scored = []
        for row_id, row_name, row_brand in rows:
            row_name = row_name or ''
            similarity = fuzz.token_sort_ratio(product_name, row_name)
            suggested_words = set(row_name.lower().replace('(', '').replace(')', '').replace('-', ' ').split())
            suggested_in_query = (
                int(100 * len(suggested_words & query_words) / len(suggested_words))
                if suggested_words else 0
            )
            scored.append({
                'id': row_id,
                'name': row_name,
                'brand': row_brand or '',
                'similarity': similarity,
                'suggested_in_query': suggested_in_query,
            })
        return sorted(scored, key=lambda x: x['similarity'], reverse=True)[:limit]
    except Exception:
        logger.exception("fuzzy_suggest_mpd_products failed (brand=%s)", brand_name)
        return []
