from django.db import connections


def build_mpd_change_context(mapped_product_uid, *, mpd_db_alias):
    """Pobiera wspólne dane referencyjne z MPD (kolory, ścieżki, atrybuty, marki,
    jednostki, kategorie rozmiarowe, skład) plus — jeśli produkt jest zmapowany —
    dane samego zmapowanego produktu w MPD.

    Zwraca zwykły dict do zmergowania w extra_context przez wywołującego. Obsługa
    try/except i dołożenie kluczy specyficznych dla appki (is_mapped, suggested_products,
    variants_json itp.) zostaje po stronie wywołującego change_view.
    """
    context = {
        'mpd_data': {}, 'main_colors': [], 'producer_colors': [],
        'mpd_paths': [], 'selected_paths': [], 'mpd_attributes': [],
        'selected_attributes': [], 'mpd_brands': [], 'units': [],
        'size_categories': [], 'fabric_components': [],
        'producer_color_name': '', 'producer_code': '', 'series_name': '',
        'selected_unit_id': None,
    }
    with connections[mpd_db_alias].cursor() as cursor:
        cursor.execute("SELECT id, name FROM colors WHERE parent_id IS NULL ORDER BY name")
        context['main_colors'] = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]

        cursor.execute("SELECT id, name, parent_id FROM colors WHERE parent_id IS NOT NULL ORDER BY name")
        context['producer_colors'] = [{'id': r[0], 'name': r[1], 'parent_id': r[2]} for r in cursor.fetchall()]

        cursor.execute("SELECT id, name, path FROM path ORDER BY name")
        context['mpd_paths'] = [{'id': r[0], 'name': r[1], 'path': r[2] or ''} for r in cursor.fetchall()]

        cursor.execute("SELECT id, name FROM attributes ORDER BY name")
        context['mpd_attributes'] = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]

        cursor.execute("SELECT id, name FROM brands ORDER BY name")
        context['mpd_brands'] = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]

        cursor.execute("SELECT unit_id, name FROM units ORDER BY name")
        context['units'] = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT category FROM sizes WHERE category IS NOT NULL ORDER BY category")
        context['size_categories'] = [r[0] for r in cursor.fetchall()]

        cursor.execute("SELECT id, name FROM fabric_component ORDER BY name")
        context['fabric_components'] = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]

        if mapped_product_uid:
            cursor.execute(
                "SELECT p.name, p.description, p.short_description, b.name "
                "FROM products p LEFT JOIN brands b ON p.brand_id = b.id WHERE p.id = %s",
                [mapped_product_uid],
            )
            r = cursor.fetchone()
            if r:
                context['mpd_data'] = {
                    'name': r[0] or '', 'description': r[1] or '',
                    'short_description': r[2] or '', 'brand': r[3] or '',
                }

            cursor.execute(
                """SELECT c.name,
                    (SELECT pvs.producer_code FROM product_variants_sources pvs
                     WHERE pvs.variant_id = pv.variant_id AND pvs.producer_code IS NOT NULL
                       AND pvs.producer_code != '' LIMIT 1)
                   FROM product_variants pv LEFT JOIN colors c ON pv.producer_color_id = c.id
                   WHERE pv.product_id = %s LIMIT 1""",
                [mapped_product_uid],
            )
            r = cursor.fetchone()
            if r:
                context['producer_color_name'], context['producer_code'] = r[0] or '', r[1] or ''

            cursor.execute(
                "SELECT ps.name FROM products p LEFT JOIN product_series ps ON p.series_id = ps.id WHERE p.id = %s",
                [mapped_product_uid],
            )
            r = cursor.fetchone()
            if r:
                context['series_name'] = r[0] or ''

            cursor.execute("SELECT path_id FROM product_path WHERE product_id = %s", [mapped_product_uid])
            context['selected_paths'] = [row[0] for row in cursor.fetchall()]

            cursor.execute("SELECT attribute_id FROM product_attributes WHERE product_id = %s", [mapped_product_uid])
            context['selected_attributes'] = [row[0] for row in cursor.fetchall()]

            cursor.execute("SELECT unit FROM products WHERE id = %s", [mapped_product_uid])
            r = cursor.fetchone()
            if r and r[0] is not None:
                context['selected_unit_id'] = r[0]

    return context
