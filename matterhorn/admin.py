from django.contrib import admin  # type: ignore
from .models import Products, UpdateLog, Images, StockHistory
from django.utils.html import format_html
from django.http import JsonResponse
from django.db import connections, transaction
import logging
import os
from rapidfuzz import fuzz
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .defs_import import get_popular_products, get_stock_trends, get_stock_statistics, clean_old_stock_history

logger = logging.getLogger(__name__)

# Logger do osobnego pliku dla mapowania wariantów
variant_logger = logging.getLogger('matterhorn.variant_mapping')
if not variant_logger.handlers:
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(
        log_dir, 'matterhorn_variant_mapping.log'), encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(formatter)
    variant_logger.addHandler(fh)
    variant_logger.setLevel(logging.INFO)

# Register your models here.
# admin.site.register(Products)


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_per_page = 30
    fields = ['active', 'name', 'description', 'creation_date', 'color', 'category_name', 'category_path', 'brand', 'url_link', 'new_collection',
              'price', 'mapped_product_id', 'get_product_images', 'get_variants', 'get_other_colors', 'get_product_in_set', 'get_size_table_html',]
    list_display = ['id', 'product_thumbnail', 'active', 'name', 'color', 'category_name', 'brand', 'new_collection', 'price',
                    'timestamp', 'url_link', 'is_mapped', 'mapped_product_id', 'get_variant_names', 'get_other_colors_ids', 'get_product_in_set_ids']
    list_filter = ['active', 'category_name', 'is_mapped']
    readonly_fields = ["active", "name", "description", "creation_date", 'url', 'url_link', "color", "category_name", "category_path", "brand", "new_collection", "size_table",
                       "size_table_txt", "size_table_html", "price", "mapped_product_id", "is_mapped", "get_product_images", "get_variants", "get_other_colors", "get_product_in_set", "get_size_table_html"]
    search_fields = ['id', 'name', 'brand',
                     'category_name', 'mapped_product_id']

    def get_list_filter(self, request):
        # Pobierz aktualnie wybraną kategorię z parametrów URL
        category = request.GET.get('category_name__exact')

        # Jeśli kategoria jest wybrana, zwróć tylko aktywne filtry
        if category:
            return ['active', 'category_name', 'category_path', 'is_mapped']

        # Jeśli kategoria nie jest wybrana, zwróć wszystkie filtry
        return ['active', 'category_name', 'category_path', 'brand', 'is_mapped']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        category = request.GET.get('category_name__exact')

        if category:
            self.brand_choices = list(queryset.filter(
                category_name=category).values_list('brand', flat=True).distinct())
        else:
            self.brand_choices = list(
                queryset.values_list('brand', flat=True).distinct())

        # Optymalizacja zapytań do relacji używanych w list_display i metodach
        return queryset.select_related('brand').prefetch_related('images', 'variants', 'other_colors', 'product_in_set')

    def lookup_allowed(self, lookup, value):
        # Zezwól na filtrowanie po kategorii i marce
        if lookup in ('category_name__exact', 'brand__exact'):
            return True
        return super().lookup_allowed(lookup, value)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('mpd-update/<int:product_id>/',
                 self.admin_site.admin_view(self.mpd_update), name='mpd-update'),
            path('mpd-create/<int:product_id>/',
                 self.admin_site.admin_view(self.mpd_create), name='mpd-create'),
            path('assign-mapping/<int:product_id>/<int:mpd_product_id>/',
                 self.admin_site.admin_view(self.assign_mapping), name='assign-mapping'),
            path('add-missing-variants/<int:product_id>/', self.admin_site.admin_view(
                self.add_missing_variants), name='add-missing-variants'),
            path('add-to-set/<int:product_id>/',
                 self.admin_site.admin_view(self.add_to_set), name='add-to-set'),
            path('mpd-update-field/<int:product_id>/<str:field_name>/',
                 self.admin_site.admin_view(self.mpd_update_field), name='mpd-update-field'),
        ]
        return custom_urls + urls

    def mpd_update(self, request, product_id):
        if request.method == 'POST':
            try:
                with connections['matterhorn'].cursor() as cursor:
                    cursor.execute(
                        "SELECT mapped_product_id FROM products WHERE id = %s", [product_id])
                    result = cursor.fetchone()
                    if not result or not result[0]:
                        return JsonResponse({'success': False, 'error': 'Produkt nie jest zmapowany'})
                    mapped_product_id = result[0]

                # Dodawanie ścieżek (nie usuwaj istniejących)
                mpd_paths = request.POST.getlist('mpd_paths')
                if mpd_paths and len(request.POST) == 1:
                    with connections['MPD'].cursor() as cursor:
                        for path_id in mpd_paths:
                            cursor.execute(
                                "INSERT INTO product_path (product_id, path_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                [mapped_product_id, path_id]
                            )
                    return JsonResponse({'success': True, 'message': 'Dodano ścieżki.'})

                # Dodawanie atrybutów (nie usuwaj istniejących)
                mpd_attributes = request.POST.getlist('mpd_attributes')
                if mpd_attributes and len(request.POST) == 1:
                    with connections['MPD'].cursor() as cursor:
                        for attribute_id in mpd_attributes:
                            cursor.execute(
                                "INSERT INTO product_attributes (product_id, attribute_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                [mapped_product_id, attribute_id]
                            )
                    return JsonResponse({'success': True, 'message': 'Dodano atrybuty.'})

                # Usuwanie ścieżki
                remove_path_id = request.POST.get('remove_path_id')
                if remove_path_id and len(request.POST) == 1:
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM product_path WHERE product_id = %s AND path_id = %s",
                            [mapped_product_id, remove_path_id]
                        )
                        connections['MPD'].commit()
                    return JsonResponse({'success': True, 'message': 'Usunięto ścieżkę.'})

                # Usuwanie atrybutu
                remove_attribute_id = request.POST.get('remove_attribute_id')
                if remove_attribute_id and len(request.POST) == 1:
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM product_attributes WHERE product_id = %s AND attribute_id = %s",
                            [mapped_product_id, remove_attribute_id]
                        )
                        connections['MPD'].commit()
                    return JsonResponse({'success': True, 'message': 'Usunięto atrybut.'})

                # Aktualizacja nazwy
                if 'mpd_name' in request.POST and len(request.POST) == 1:
                    name = request.POST.get('mpd_name')
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute("UPDATE products SET name = %s WHERE id = %s", [
                                       name, mapped_product_id])
                    return JsonResponse({'success': True, 'message': 'Zaktualizowano nazwę.'})

                # Aktualizacja opisu
                if 'mpd_description' in request.POST and len(request.POST) == 1:
                    description = request.POST.get('mpd_description')
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute("UPDATE products SET description = %s WHERE id = %s", [
                                       description, mapped_product_id])
                    return JsonResponse({'success': True, 'message': 'Zaktualizowano opis.'})

                # Aktualizacja marki
                if 'mpd_brand' in request.POST and len(request.POST) == 1:
                    brand = request.POST.get('mpd_brand')
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute(
                            "SELECT id FROM brands WHERE name = %s", [brand])
                        brand_result = cursor.fetchone()
                        if not brand_result:
                            return JsonResponse({'success': False, 'error': 'Nie znaleziono marki w bazie MPD'})
                        brand_id = brand_result[0]
                        cursor.execute("UPDATE products SET brand_id = %s WHERE id = %s", [
                                       brand_id, mapped_product_id])
                    return JsonResponse({'success': True, 'message': 'Zaktualizowano markę.'})

                # Aktualizacja kodu producenta
                if 'producer_code' in request.POST and len(request.POST) == 1:
                    producer_code = request.POST.get('producer_code')
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute("UPDATE products SET producer_code = %s WHERE id = %s", [
                                       producer_code, mapped_product_id])
                    return JsonResponse({'success': True, 'message': 'Zaktualizowano kod producenta.'})

                # Aktualizacja serii
                if 'series_name' in request.POST and len(request.POST) == 1:
                    series_name = request.POST.get('series_name')
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute(
                            "SELECT id FROM product_series WHERE name = %s", [series_name])
                        row = cursor.fetchone()
                        if row:
                            series_id = row[0]
                        else:
                            cursor.execute(
                                "INSERT INTO product_series (name) VALUES (%s) RETURNING id", [series_name])
                            series_id = cursor.fetchone()[0]
                        cursor.execute("UPDATE products SET series_id = %s WHERE id = %s", [
                                       series_id, mapped_product_id])
                    return JsonResponse({'success': True, 'message': 'Zaktualizowano serię.'})

                # Analogicznie możesz dodać kolejne pola...

                return JsonResponse({'success': False, 'error': 'Nieprawidłowe pole lub brak obsługi.'})

            except Exception as e:
                logger.error(
                    f"Błąd podczas aktualizacji produktu {product_id}: {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda żądania'})

    def add_new_variants_to_mpd(self, product_id, mapped_product_id, size_category, producer_color_id=None, producer_code=None):
        variant_logger.info(
            f"[add_new_variants_to_mpd] START: product_id={product_id}, mapped_product_id={mapped_product_id}, size_category={size_category}, producer_color_id={producer_color_id}, producer_code={producer_code}")
        missing_sizes = []
        missing_colors = False
        added_variants = 0
        skipped_existing = 0
        total_variants = 0
        try:
            with connections['matterhorn'].cursor() as matterhorn_cursor, connections['MPD'].cursor() as mpd_cursor:
                # Pobierz kolor i cenę produktu
                matterhorn_cursor.execute("""
                    SELECT color, price FROM products WHERE id = %s
                """, [product_id])
                color_result = matterhorn_cursor.fetchone()
                if not color_result:
                    variant_logger.error(
                        f"[add_new_variants_to_mpd] Brak koloru dla produktu {product_id}")
                    return {'added': 0, 'skipped_existing': 0, 'missing_sizes': [], 'missing_color': True, 'total': 0}
                product_color, product_price = color_result
                variant_logger.info(
                    f"[add_new_variants_to_mpd] Kolor produktu: {product_color}, cena: {product_price}")

                # Pobierz ID koloru w MPD
                mpd_cursor.execute(
                    "SELECT id FROM colors WHERE name = %s", [product_color])
                color_result = mpd_cursor.fetchone()
                if not color_result:
                    variant_logger.error(
                        f"[add_new_variants_to_mpd] Brak koloru {product_color} w bazie MPD")
                    missing_colors = True
                    return {'added': 0, 'skipped_existing': 0, 'missing_sizes': [], 'missing_color': True, 'total': 0}
                color_id = color_result[0]
                variant_logger.info(
                    f"[add_new_variants_to_mpd] ID koloru w MPD: {color_id}")

                # Pobierz warianty produktu z Matterhorna
                matterhorn_cursor.execute("""
                    SELECT name, stock, ean, variant_uid FROM variants WHERE product_id = %s
                """, [product_id])
                variants = matterhorn_cursor.fetchall()
                variant_logger.info(
                    f"[add_new_variants_to_mpd] Znaleziono {len(variants)} wariantów do sprawdzenia dla produktu {product_id}")
                total_variants = len(variants)

                for size_name, stock, ean, variant_uid in variants:
                    variant_logger.info(
                        f"[add_new_variants_to_mpd] Próba dodania wariantu: size_name={size_name}, stock={stock}, ean={ean}, variant_uid={variant_uid}")
                    # Pobierz ID rozmiaru tylko z wybranej kategorii
                    mpd_cursor.execute("SELECT id FROM sizes WHERE UPPER(name) = UPPER(%s) AND category = %s", [
                                       size_name, size_category])
                    size_result = mpd_cursor.fetchone()
                    if not size_result:
                        variant_logger.warning(
                            f"[add_new_variants_to_mpd] Brak rozmiaru {size_name} w grupie {size_category} w bazie MPD")
                        missing_sizes.append(size_name)
                        continue
                    size_id = size_result[0]
                    variant_logger.info(
                        f"[add_new_variants_to_mpd] Znaleziono rozmiar: {size_name} (id={size_id}) w kategorii {size_category}")

                    # Sprawdź, czy wariant już istnieje w MPD
                    mpd_cursor.execute("""
                        SELECT variant_id FROM product_variants WHERE variant_uid = %s AND product_id = %s AND source_id = %s
                    """, [variant_uid, mapped_product_id, 2])
                    variant_result = mpd_cursor.fetchone()
                    if variant_result:
                        variant_logger.info(
                            f"[add_new_variants_to_mpd] Wariant {variant_uid} już istnieje w MPD - pomijam")
                        skipped_existing += 1
                        continue

                    # Dodaj nowy wariant
                    mpd_cursor.execute(
                        "SELECT COALESCE(MAX(variant_id), 0) + 1 FROM product_variants")
                    variant_id = mpd_cursor.fetchone()[0]
                    variant_logger.info(
                        f"[add_new_variants_to_mpd] Dodaję nowy wariant {variant_uid} jako variant_id {variant_id} (product_id={mapped_product_id}, color_id={color_id}, size_id={size_id}, ean={ean}, producer_color_id={producer_color_id}, producer_code={producer_code})")

                    try:
                        if producer_color_id:
                            mpd_cursor.execute("""
                                INSERT INTO product_variants (variant_id, product_id, color_id, producer_color_id, size_id, ean, variant_uid, source_id, producer_code)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, [variant_id, mapped_product_id, color_id, producer_color_id, size_id, ean, variant_uid, 2, producer_code])
                        else:
                            mpd_cursor.execute("""
                                INSERT INTO product_variants (variant_id, product_id, color_id, size_id, ean, variant_uid, source_id, producer_code)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, [variant_id, mapped_product_id, color_id, size_id, ean, variant_uid, 2, producer_code])
                        variant_logger.info(
                            f"[add_new_variants_to_mpd] Dodano wariant {variant_uid} do product_variants")
                    except Exception as e:
                        variant_logger.error(
                            f"[add_new_variants_to_mpd] Błąd podczas dodawania wariantu {variant_uid} do product_variants: {e}")
                        continue

                    try:
                        # Sprawdź czy rekord już istnieje
                        mpd_cursor.execute("""
                            SELECT variant_id FROM stock_and_prices 
                            WHERE variant_id = %s AND source_id = %s
                        """, [variant_id, 2])
                        existing_record = mpd_cursor.fetchone()

                        if existing_record:
                            # Aktualizuj istniejący rekord
                            mpd_cursor.execute("""
                                UPDATE stock_and_prices 
                                SET stock = %s, price = %s, currency = 'PLN'
                                WHERE variant_id = %s AND source_id = %s
                            """, [stock, product_price, variant_id, 2])
                        else:
                            # Dodaj nowy rekord
                            mpd_cursor.execute("""
                                INSERT INTO stock_and_prices 
                                (variant_id, source_id, stock, price, currency)
                                VALUES (%s, %s, %s, %s, 'PLN')
                            """, [variant_id, 2, stock, product_price])
                    except Exception as e:
                        variant_logger.error(
                            f"[add_new_variants_to_mpd] Błąd podczas dodawania/uzupełniania stock_and_prices dla wariantu {variant_uid}: {e}")
                        continue

                    try:
                        matterhorn_cursor.execute("""
                            UPDATE variants SET mapped_variant_id = %s, is_mapped = true, last_updated = NOW() WHERE variant_uid = %s
                        """, [variant_id, variant_uid])
                        variant_logger.info(
                            f"[add_new_variants_to_mpd] Zaktualizowano mapped_variant_id w Matterhornie dla wariantu {variant_uid}")
                    except Exception as e:
                        variant_logger.error(
                            f"[add_new_variants_to_mpd] Błąd podczas aktualizacji mapped_variant_id w Matterhornie dla wariantu {variant_uid}: {e}")
                        continue
                    added_variants += 1
                connections['matterhorn'].commit()
                variant_logger.info(
                    f"[add_new_variants_to_mpd] Podsumowanie mapowania wariantów: dodano {added_variants}, pominięto {skipped_existing} (istniały), brak rozmiarów: {missing_sizes}, brak koloru: {missing_colors}")
                return {
                    'added': added_variants,
                    'skipped_existing': skipped_existing,
                    'missing_sizes': missing_sizes,
                    'missing_color': missing_colors,
                    'total': total_variants
                }
        except Exception as e:
            variant_logger.error(
                f"[add_new_variants_to_mpd] Błąd podczas dodawania nowych wariantów do MPD: {str(e)}")
            return {'added': added_variants, 'skipped_existing': skipped_existing, 'missing_sizes': missing_sizes, 'missing_color': missing_colors, 'total': total_variants}
        finally:
            variant_logger.info(
                f"[add_new_variants_to_mpd] END: product_id={product_id}, mapped_product_id={mapped_product_id}, size_category={size_category}, producer_color_id={producer_color_id}, producer_code={producer_code}")

    def mpd_create(self, request, product_id):
        variant_logger.info(
            f"[mpd_create] START: product_id={product_id}, method={request.method}")
        if request.method == 'POST':
            try:
                name = request.POST.get('mpd_name')
                description = request.POST.get('mpd_description')
                brand = request.POST.get('mpd_brand')
                size_category = request.POST.get('mpd_size_category')
                main_color_id = request.POST.get('main_color_id')
                producer_code = request.POST.get('producer_code')
                series_name = request.POST.get('series_name')
                producer_color_name = request.POST.get('producer_color_name')
                product_set_id = request.POST.get('product_set')
                variant_logger.info(
                    f"[mpd_create] POST data: name={name}, description={description}, brand={brand}, size_category={size_category}, main_color_id={main_color_id}, producer_code={producer_code}, series_name={series_name}, producer_color_name={producer_color_name}, product_set_id={product_set_id}")

                if not size_category:
                    variant_logger.warning(
                        f"[mpd_create] Brak wybranej grupy rozmiarowej dla produktu {product_id}")
                    return JsonResponse({'success': False, 'error': 'Wybierz grupę rozmiarową przed mapowaniem produktu.'})
                if not main_color_id:
                    variant_logger.warning(
                        f"[mpd_create] Brak wybranego głównego koloru dla produktu {product_id}")
                    return JsonResponse({'success': False, 'error': 'Wybierz główny kolor przed mapowaniem produktu.'})

                logger.info(
                    f"Rozpoczynam mapowanie produktu {product_id} z grupą rozmiarową: {size_category} i kolorem: {main_color_id}")

                # --- MAPOWANIE SERII ---
                # Pobierz powiązane produkty z Matterhorn
                with connections['matterhorn'].cursor() as matterhorn_cursor:
                    matterhorn_cursor.execute("""
                        SELECT set_product_id FROM product_in_set WHERE product_id = %s
                    """, [product_id])
                    related_ids = [row[0]
                                   for row in matterhorn_cursor.fetchall()]

                    # Pobierz mapped_product_id dla powiązanych produktów
                    mapped_ids = []
                    if related_ids:
                        format_strings = ','.join(['%s'] * len(related_ids))
                        matterhorn_cursor.execute(
                            f"SELECT id, mapped_product_id FROM products WHERE id IN ({format_strings})", related_ids)
                        mapped_ids = [row[1]
                                      for row in matterhorn_cursor.fetchall() if row[1]]

                # Dodajemy też nowo tworzony produkt (będzie miał new_product_id po utworzeniu)
                series_id = None
                # Sprawdź, czy któryś z powiązanych produktów w MPD ma już series_id
                if mapped_ids:
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute("SELECT series_id FROM products WHERE id IN %s AND series_id IS NOT NULL LIMIT 1", [
                                       tuple(mapped_ids)])
                        row = cursor.fetchone()
                        if row and row[0]:
                            series_id = row[0]
                # Jeśli nie ma, sprawdź czy seria o tej nazwie już istnieje
                if not series_id and series_name:
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute(
                            "SELECT id FROM product_series WHERE name = %s", [series_name])
                        row = cursor.fetchone()
                        if row:
                            series_id = row[0]
                        else:
                            # Jeśli seria nie istnieje, utwórz nową
                            cursor.execute(
                                "INSERT INTO product_series (name) VALUES (%s) RETURNING id", [series_name])
                            series_id = cursor.fetchone()[0]

                with transaction.atomic(using='MPD'):
                    # Utwórz nowy produkt w bazie MPD
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute(
                            "SELECT id FROM brands WHERE name = %s", [brand])
                        brand_result = cursor.fetchone()
                        if not brand_result:
                            logger.error(
                                f"Nie znaleziono marki {brand} w bazie MPD")
                            raise Exception('Marka nie istnieje w bazie MPD')
                        brand_id = brand_result[0]

                        cursor.execute("""
                            INSERT INTO products (name, description, brand_id, series_id)
                            VALUES (%s, %s, %s, %s)
                            RETURNING id
                        """, [name, description, brand_id, series_id])
                        new_product_id = cursor.fetchone()[0]
                        logger.info(
                            f"Utworzono nowy produkt w MPD z ID {new_product_id}")

                        # --- DODAJ: zapis ścieżek produktu ---
                        mpd_paths = request.POST.getlist('mpd_paths')
                        if mpd_paths:
                            for path_id in mpd_paths:
                                cursor.execute(
                                    "INSERT INTO product_path (product_id, path_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                    [new_product_id, path_id]
                                )

                        # --- DODAJ: zapis atrybutów produktu ---
                        mpd_attributes = request.POST.getlist('mpd_attributes')
                        if mpd_attributes:
                            for attribute_id in mpd_attributes:
                                cursor.execute(
                                    "INSERT INTO product_attributes (product_id, attribute_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                    [new_product_id, attribute_id]
                                )

                        # --- LOGIKA ZESTAWÓW (wiele-do-wielu) ---
                        if product_set_id:
                            # Sprawdź czy produkt o podanym ID istnieje
                            cursor.execute("SELECT id FROM products WHERE id = %s", [
                                           product_set_id])
                            if not cursor.fetchone():
                                return JsonResponse({'success': False, 'error': f'Produkt o ID {product_set_id} nie istnieje w bazie MPD'})
                            # Utwórz nowy zestaw
                            cursor.execute("""
                                INSERT INTO product_set (name, description, mapped_product_id)
                                VALUES (%s, %s, %s)
                                RETURNING id
                            """, [f"Zestaw {name}", f"Zestaw zawierający {name}", new_product_id])
                            new_set_id = cursor.fetchone()[0]
                            # Dodaj oba produkty do tabeli pośredniej
                            cursor.execute("""
                                INSERT INTO product_set_items (product_set_id, product_id)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                            """, [new_set_id, new_product_id])
                            cursor.execute("""
                                INSERT INTO product_set_items (product_set_id, product_id)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                            """, [new_set_id, product_set_id])
                        # --- KONIEC LOGIKI ZESTAWÓW ---

                        # Prześlij zdjęcia do bucketu i zaktualizuj ścieżki
                        with connections['matterhorn'].cursor() as matterhorn_cursor:
                            matterhorn_cursor.execute("""
                                SELECT image_path FROM images WHERE product_id = %s
                            """, [product_id])
                            images = matterhorn_cursor.fetchall()

                            for idx, image_path in enumerate(images, start=1):
                                if image_path[0]:
                                    from matterhorn.defs_db import upload_image_to_bucket_and_get_url
                                    new_image_path = upload_image_to_bucket_and_get_url(
                                        image_path[0], new_product_id, producer_color_name, image_number=idx)
                                    if new_image_path:
                                        cursor.execute("""
                                            INSERT INTO product_images (product_id, file_path)
                                            VALUES (%s, %s)
                                        """, [new_product_id, new_image_path])

                        # Przypisz series_id wszystkim powiązanym produktom w MPD
                        if mapped_ids:
                            cursor.execute(
                                f"UPDATE products SET series_id = %s WHERE id IN ({','.join(['%s']*len(mapped_ids))})", [series_id] + mapped_ids)

                        # Pobierz kolor produktu
                        with connections['matterhorn'].cursor() as matterhorn_cursor:
                            matterhorn_cursor.execute("""
                                SELECT color, price FROM products WHERE id = %s
                            """, [product_id])
                            color_result = matterhorn_cursor.fetchone()
                            if not color_result:
                                logger.error(
                                    f"Brak koloru dla produktu {product_id}")
                                raise Exception('Brak koloru dla produktu')
                            product_color, product_price = color_result
                            logger.info(
                                f"Pobrano kolor {product_color} i cenę {product_price}")

                            # Główny kolor (color_id)
                            try:
                                color_id = int(main_color_id)
                            except (TypeError, ValueError):
                                logger.error(
                                    f"Nieprawidłowy main_color_id: {main_color_id}")
                                raise Exception(
                                    f"Nieprawidłowy główny kolor (main_color_id): {main_color_id}")

                            # Pobierz lub utwórz producer_color_id powiązany z color_id
                            producer_color_id_to_use = None
                            if producer_color_name:
                                cursor.execute("SELECT id FROM colors WHERE name = %s AND parent_id = %s", [
                                               producer_color_name, color_id])
                                pc_row = cursor.fetchone()
                                if pc_row:
                                    producer_color_id_to_use = pc_row[0]
                                else:
                                    cursor.execute("INSERT INTO colors (name, parent_id) VALUES (%s, %s) RETURNING id", [
                                                   producer_color_name, color_id])
                                    pc_row = cursor.fetchone()
                                    if pc_row:
                                        producer_color_id_to_use = pc_row[0]

                            # Pobierz warianty produktu
                            matterhorn_cursor.execute("""
                                SELECT name, stock, ean, variant_uid 
                                FROM variants 
                                WHERE product_id = %s
                            """, [product_id])
                            variants = matterhorn_cursor.fetchall()
                            logger.info(
                                f"Znaleziono {len(variants)} wariantów dla produktu {product_id}")

                            if not variants:
                                logger.error(
                                    f"Brak wariantów dla produktu {product_id}")
                                raise Exception('Brak wariantów dla produktu')

                            # Dodaj warianty do MPD tylko z wybranej kategorii rozmiarowej
                            for size_name, stock, ean, variant_uid in variants:
                                logger.info(
                                    f"Przetwarzam wariant: {size_name}, stock: {stock}, ean: {ean}, uid: {variant_uid}")
                                # Pobierz ID rozmiaru tylko z wybranej kategorii
                                cursor.execute("SELECT id FROM sizes WHERE UPPER(name) = UPPER(%s) AND category = %s", [
                                               size_name, size_category])
                                size_result = cursor.fetchone()
                                if not size_result:
                                    logger.warning(
                                        f"Brak rozmiaru {size_name} w grupie {size_category} w bazie MPD")
                                    continue
                                size_id = size_result[0]

                                cursor.execute("""
                                    SELECT variant_id 
                                    FROM product_variants 
                                    WHERE variant_uid = %s AND source_id = %s
                                """, [variant_uid, 2])
                                variant_result = cursor.fetchone()

                                if variant_result:
                                    variant_id = variant_result[0]
                                    logger.info(
                                        f"Znaleziono istniejący wariant z ID {variant_id}")
                                else:
                                    cursor.execute("""
                                        SELECT COALESCE(MAX(variant_id), 0) + 1 
                                        FROM product_variants
                                    """)
                                    variant_id = cursor.fetchone()[0]
                                    logger.info(
                                        f"Utworzono nowy wariant z ID {variant_id}")

                                    # Dodaj wariant z odpowiednim producer_color_id
                                    cursor.execute("""
                                        INSERT INTO product_variants 
                                        (variant_id, product_id, color_id, size_id, ean, variant_uid, source_id, producer_color_id, producer_code)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, [variant_id, new_product_id, color_id, size_id, ean, variant_uid, 2, producer_color_id_to_use, producer_code])

                                # Sprawdź czy rekord już istnieje
                                cursor.execute("""
                                    SELECT variant_id FROM stock_and_prices 
                                    WHERE variant_id = %s AND source_id = %s
                                """, [variant_id, 2])
                                existing_record = cursor.fetchone()

                                if existing_record:
                                    # Aktualizuj istniejący rekord
                                    cursor.execute("""
                                        UPDATE stock_and_prices 
                                        SET stock = %s, price = %s, currency = 'PLN'
                                        WHERE variant_id = %s AND source_id = %s
                                    """, [stock, product_price, variant_id, 2])
                                else:
                                    # Dodaj nowy rekord
                                    cursor.execute("""
                                        INSERT INTO stock_and_prices 
                                        (variant_id, source_id, stock, price, currency)
                                        VALUES (%s, %s, %s, %s, 'PLN')
                                    """, [variant_id, 2, stock, product_price])

                                # Zaktualizuj informacje o wariancie w Matterhorn
                                with connections['matterhorn'].cursor() as matterhorn_cursor2:
                                    matterhorn_cursor2.execute("""
                                        UPDATE variants 
                                        SET mapped_variant_id = %s,
                                            is_mapped = true,
                                            last_updated = NOW()
                                        WHERE variant_uid = %s
                                    """, [variant_id, variant_uid])
                            connections['matterhorn'].commit()

                        with connections['matterhorn'].cursor() as matterhorn_cursor:
                            matterhorn_cursor.execute("""
                                UPDATE products 
                                SET mapped_product_id = %s,
                                    is_mapped = true,
                                    last_updated = NOW()
                                WHERE id = %s
                            """, [new_product_id, product_id])
                            connections['matterhorn'].commit()
                            logger.info(
                                f"Zaktualizowano produkt {product_id} w bazie Matterhorn")

                return JsonResponse({'success': True, 'message': 'Produkt został pomyślnie zmapowany'})
            except Exception as e:
                logger.error(
                    f"Błąd podczas mapowania produktu {product_id}: {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda żądania'})

    def assign_mapping(self, request, product_id, mpd_product_id):
        variant_logger.info(
            f"[assign_mapping] START: product_id={product_id}, mpd_product_id={mpd_product_id}, method={request.method}")
        if request.method == 'POST':
            try:
                producer_code = request.POST.get('producer_code')
                producer_color_name = request.POST.get('producer_color_name')
                main_color_id = request.POST.get('main_color_id')
                producer_color_id = None

                if producer_color_name and main_color_id:
                    with connections['MPD'].cursor() as cursor:
                        # Najpierw sprawdź czy kolor o takiej nazwie już istnieje
                        cursor.execute("SELECT id FROM colors WHERE name = %s", [
                                       producer_color_name])
                        pc_result = cursor.fetchone()
                        if pc_result:
                            producer_color_id = pc_result[0]
                            logger.info(
                                f"[assign_mapping] Użyto istniejącego koloru producenta: {producer_color_name} (id={producer_color_id})")
                        else:
                            # Jeśli nie istnieje, dodaj nowy kolor
                            cursor.execute("INSERT INTO colors (name, parent_id) VALUES (%s, %s) RETURNING id", [
                                           producer_color_name, main_color_id])
                            producer_color_id = cursor.fetchone()[0]
                            logger.info(
                                f"[assign_mapping] Dodano nowy kolor producenta: {producer_color_name} (id={producer_color_id})")

                with connections['matterhorn'].cursor() as cursor:
                    cursor.execute("""
                        UPDATE products
                        SET mapped_product_id = %s, is_mapped = true, last_updated = NOW()
                        WHERE id = %s
                    """, [mpd_product_id, product_id])
                    connections['matterhorn'].commit()
                    variant_logger.info(
                        f"[assign_mapping] Przypisano mapped_product_id={mpd_product_id} do produktu {product_id}")

                # Pobierz kategorię rozmiarową z MPD na podstawie mapped_product_id i pierwszego wariantu
                with connections['MPD'].cursor() as mpd_cursor:
                    mpd_cursor.execute("""
                        SELECT s.category
                        FROM product_variants pv
                        JOIN sizes s ON pv.size_id = s.id
                        WHERE pv.product_id = %s
                        LIMIT 1
                    """, [mpd_product_id])
                    size_cat_result = mpd_cursor.fetchone()
                    if not size_cat_result or not size_cat_result[0]:
                        variant_logger.warning(
                            f"[assign_mapping] Nie można ustalić kategorii rozmiarowej dla produktu MPD {mpd_product_id}")
                        size_category = None
                    else:
                        size_category = size_cat_result[0]

                if size_category:
                    variant_logger.info(
                        f"[assign_mapping] Wywołanie add_new_variants_to_mpd({product_id}, {mpd_product_id}, {size_category}, {producer_color_id}, {producer_code})")
                    mapping_info = self.add_new_variants_to_mpd(
                        product_id, mpd_product_id, size_category, producer_color_id, producer_code)
                    variant_logger.info(
                        f"[assign_mapping] Wynik add_new_variants_to_mpd: {mapping_info}")

                    # --- DODAJ: upload zdjęć do bucketa i zapis do bazy MPD (jak w mpd_create) ---
                    from matterhorn.defs_db import upload_image_to_bucket_and_get_url
                    with connections['matterhorn'].cursor() as matterhorn_cursor, connections['MPD'].cursor() as mpd_cursor:
                        matterhorn_cursor.execute(
                            "SELECT image_path FROM images WHERE product_id = %s", [product_id])
                        images = matterhorn_cursor.fetchall()
                        for idx, image_path in enumerate(images, start=1):
                            if image_path[0]:
                                new_image_path = upload_image_to_bucket_and_get_url(
                                    image_path[0], mpd_product_id, producer_color_name, image_number=idx)
                                if new_image_path:
                                    mpd_cursor.execute("""
                                        INSERT INTO product_images (product_id, file_path)
                                        VALUES (%s, %s)
                                        ON CONFLICT (product_id, file_path) DO NOTHING
                                    """, [mpd_product_id, new_image_path])
                        connections['MPD'].commit()
                    # --- KONIEC DODATKU ---
                else:
                    mapping_info = {
                        'error': 'Brak kategorii rozmiarowej w MPD'}

                return JsonResponse({'success': True, 'message': f'Produkt został przypisany do MPD ID {mpd_product_id}.', 'mapping_info': mapping_info})
            except Exception as e:
                variant_logger.error(f"[assign_mapping] Błąd: {e}")
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda żądania'})

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related(
            'variants', 'other_colors', 'product_in_set')
        return queryset

    def get_product_images(self, obj):
        images = Images.objects.filter(product=obj)
        if images:
            html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
            for image in images:
                if image.image_path:
                    html += f'<a href="{image.image_path}" target="_blank" rel="noopener noreferrer"><img src="{image.image_path}" style="max-height: 100px; max-width: 100px; margin: 5px; cursor: pointer;" /></a>'
            html += '</div>'
            return format_html(html)
        return "-"
    get_product_images.short_description = 'Images'

    def get_variants(self, obj):
        variants = obj.variants.all()
        if variants:
            html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
            for variant in variants:
                is_mapped = variant.is_mapped
                border_color = 'green' if is_mapped else 'red'
                is_mapped_label = f'<span style="color: {border_color}; font-weight: bold;">{is_mapped}</span>'
                html += f'''
                    <div style="border: 2px solid {border_color}; padding: 10px; border-radius: 5px; min-width: 200px;">
                        <div><strong>Nazwa:</strong> {variant.name or '-'}</div>
                        <div><strong>Stan:</strong> {variant.stock or '-'}</div>
                        <div><strong>EAN:</strong> {variant.ean or '-'}</div>
                        <div><strong>Czas przetwarzania:</strong> {variant.max_processing_time or '-'}</div>
                        <div><strong>Mapped variant ID:</strong> {variant.mapped_variant_id or '-'}</div>
                        <div><strong>Is mapped:</strong> {is_mapped_label}</div>
                    </div>
                '''
            html += '</div>'
            return format_html(html)
        return "-"
    get_variants.short_description = 'Variants'

    def get_other_colors(self, obj):
        other_colors = obj.other_colors.all()
        if other_colors:
            html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
            for color in other_colors:
                if color.color_product:
                    first_image = Images.objects.filter(
                        product=color.color_product).first()
                    image_html = ''
                    if first_image and first_image.image_path:
                        image_html = f'<a href="{first_image.image_path}" target="_blank" rel="noopener noreferrer"><img src="{first_image.image_path}" style="max-height: 100px; max-width: 100px; margin: 5px; cursor: pointer;" /></a>'
                    is_mapped = color.color_product.is_mapped
                    border_color = 'green' if is_mapped else 'red'
                    is_mapped_label = f'<span style="color: {border_color}; font-weight: bold;">{is_mapped}</span>'
                    html += f'''
                        <div style="border: 2px solid {border_color}; padding: 10px; border-radius: 5px; min-width: 200px;">
                            <div style="text-align: center; margin-bottom: 10px;">{image_html}</div>
                            <div><strong>ID:</strong> {color.color_product.id}</div>
                            <div><strong>Nazwa:</strong> {color.color_product.name or '-'}</div>
                            <div><strong>Kolor:</strong> {color.color_product.color or '-'}</div>
                            <div><strong>Is mapped:</strong> {is_mapped_label}</div>
                            <div style="margin-top: 10px;">
                                <a href="/admin/matterhorn/products/{color.color_product.id}/change/" class="button" style="background-color: #417690; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">Zobacz produkt</a>
                            </div>
                        </div>
                    '''
            html += '</div>'
            return format_html(html)
        return "-"
    get_other_colors.short_description = 'Other Colors'

    def get_product_in_set(self, obj):
        products_in_set = obj.product_in_set.all()
        if products_in_set:
            html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
            for product in products_in_set:
                if product.set_product:
                    first_image = Images.objects.filter(
                        product=product.set_product).first()
                    image_html = ''
                    if first_image and first_image.image_path:
                        image_html = f'<a href="{first_image.image_path}" target="_blank" rel="noopener noreferrer"><img src="{first_image.image_path}" style="max-height: 100px; max-width: 100px; margin: 5px; cursor: pointer;" /></a>'
                    is_mapped = product.set_product.is_mapped
                    border_color = 'green' if is_mapped else 'red'
                    is_mapped_label = f'<span style="color: {border_color}; font-weight: bold;">{is_mapped}</span>'
                    html += f'''
                        <div style="border: 2px solid {border_color}; padding: 10px; border-radius: 5px; min-width: 200px;">
                            <div style="text-align: center; margin-bottom: 10px;">{image_html}</div>
                            <div><strong>ID:</strong> {product.set_product.id}</div>
                            <div><strong>Nazwa:</strong> {product.set_product.name or '-'}</div>
                            <div><strong>Kolor:</strong> {product.set_product.color or '-'}</div>
                            <div><strong>Is mapped:</strong> {is_mapped_label}</div>
                            <div><strong>Mapped product ID:</strong> {getattr(product.set_product, 'mapped_product_id', '-') or '-'}</div>
                            <div style="margin-top: 10px;">
                                <a href="/admin/matterhorn/products/{product.set_product.id}/change/" class="button" style="background-color: #417690; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">Edytuj produkt</a>
                            </div>
                        </div>
                    '''
            html += '</div>'
            return format_html(html)
        return "-"
    get_product_in_set.short_description = 'Products in Series'

    def url_link(self, obj):
        if obj.url:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">🌐</a>',
                obj.url
            )
        return "-"
    url_link.short_description = "URL"

    def get_product_color_id(self, obj):
        return obj.mapped_product_id

    def get_variant_names(self, obj):
        variants = obj.variants.all()
        if variants:
            return ", ".join([variant.name for variant in variants])
        return "-"

    get_variant_names.short_description = "Rozmiary"

    def get_other_colors_ids(self, obj):
        other_colors = obj.other_colors.all()
        if other_colors:
            return ", ".join([str(color.color_product.id) for color in other_colors if color.color_product])
        return "-"
    get_other_colors_ids.short_description = 'Other Colors IDs'

    def get_product_in_set_ids(self, obj):
        products_in_set = obj.product_in_set.all()
        if products_in_set:
            return ", ".join([str(product.set_product.id) for product in products_in_set if product.set_product])
        return "-"
    get_product_in_set_ids.short_description = 'Products in Series IDs'

    def get_mpd_data(self, product_id):
        """Pobiera dane produktu z MPD na podstawie mapped_product_id"""
        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute("""
                    SELECT name, description, brand 
                    FROM products 
                    WHERE id = %s
                """, [product_id])
                row = cursor.fetchone()
                if row:
                    return {
                        'name': row[0],
                        'description': row[1],
                        'brand': row[2]
                    }
        except Exception as e:
            logger.error(f"Błąd pobierania danych z MPD: {e}")
        return None

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        product = self.get_object(request, object_id)
        # Pobierz dostępne ścieżki z MPD
        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute("SELECT id, name, path FROM path ORDER BY name")
                mpd_paths = [{'id': row[0], 'name': row[1], 'path': row[2]}
                             for row in cursor.fetchall()]
            extra_context['mpd_paths'] = mpd_paths
        except Exception as e:
            logger.error(f"Błąd pobierania ścieżek z MPD: {e}")
            extra_context['mpd_paths'] = []

        # Pobierz dostępne atrybuty z MPD
        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute("SELECT id, name FROM attributes ORDER BY name")
                mpd_attributes = [{'id': row[0], 'name': row[1]}
                                  for row in cursor.fetchall()]
            extra_context['mpd_attributes'] = mpd_attributes
        except Exception as e:
            logger.error(f"Błąd pobierania atrybutów z MPD: {e}")
            extra_context['mpd_attributes'] = []

        # Pobierz aktualnie przypisane ścieżki do produktu (jeśli zmapowany)
        mapped_id = getattr(product, 'mapped_product_id', None)
        if mapped_id:
            with connections['MPD'].cursor() as cursor:
                cursor.execute(
                    "SELECT path_id FROM product_path WHERE product_id = %s", [mapped_id])
                selected_paths = [row[0] for row in cursor.fetchall()]
            extra_context['selected_paths'] = selected_paths

            # Pobierz aktualnie przypisane atrybuty do produktu
            with connections['MPD'].cursor() as cursor:
                cursor.execute(
                    "SELECT attribute_id FROM product_attributes WHERE product_id = %s", [mapped_id])
                selected_attributes = [row[0] for row in cursor.fetchall()]
            extra_context['selected_attributes'] = selected_attributes
        else:
            extra_context['selected_paths'] = []
            extra_context['selected_attributes'] = []

        # Pobierz kategorie rozmiarów z MPD
        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute(
                    "SELECT DISTINCT category FROM sizes WHERE category IS NOT NULL ORDER BY category")
                size_categories = [row[0] for row in cursor.fetchall()]
            extra_context['size_categories'] = size_categories
        except Exception as e:
            logger.error(f"Błąd pobierania kategorii rozmiarów z MPD: {e}")
            extra_context['size_categories'] = []

        # Pobierz główne kolory i kolory producenta z MPD
        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute(
                    "SELECT id, name FROM colors WHERE parent_id IS NULL ORDER BY name")
                main_colors = [{'id': row[0], 'name': row[1]}
                               for row in cursor.fetchall()]
                cursor.execute(
                    "SELECT id, name, parent_id FROM colors WHERE parent_id IS NOT NULL ORDER BY name")
                producer_colors = [{'id': row[0], 'name': row[1],
                                    'parent_id': row[2]} for row in cursor.fetchall()]
            extra_context['main_colors'] = main_colors
            extra_context['producer_colors'] = producer_colors
        except Exception as e:
            logger.error(f"Błąd pobierania kolorów z MPD: {e}")
            extra_context['main_colors'] = []
            extra_context['producer_colors'] = []

        # Pobierz listę zestawów powiązanych z produktem w MPD
        product_sets = []
        if mapped_id:
            with connections['MPD'].cursor() as cursor:
                # Najpierw pobierz ID zestawów, do których należy produkt
                cursor.execute('''
                    SELECT psi.product_set_id
                    FROM product_set_items psi
                    WHERE psi.product_id = %s
                ''', [mapped_id])
                set_ids = [row[0] for row in cursor.fetchall()]
                if set_ids:
                    # Pobierz wszystkie produkty z tych zestawów
                    format_strings = ','.join(['%s'] * len(set_ids))
                    cursor.execute(f'''
                        SELECT ps.id, ps.name, array_agg(psi.product_id)
                        FROM product_set ps
                        JOIN product_set_items psi ON psi.product_set_id = ps.id
                        WHERE ps.id IN ({format_strings})
                        GROUP BY ps.id, ps.name
                    ''', set_ids)
                    for row in cursor.fetchall():
                        product_sets.append(
                            {'id': row[0], 'name': row[1], 'items': list(row[2])})
        extra_context['product_sets'] = product_sets

        # Pobierz warianty z MPD wraz z kolorem producenta
        mpd_variants = []
        if mapped_id:
            with connections['MPD'].cursor() as cursor:
                cursor.execute('''
                    SELECT pv.variant_id, pv.ean, sp.stock, pv.size_id, s.name as size_name, pv.producer_code, c.name as producer_color_name
                    FROM product_variants pv
                    LEFT JOIN colors c ON pv.producer_color_id = c.id
                    LEFT JOIN sizes s ON pv.size_id = s.id
                    LEFT JOIN stock_and_prices sp ON pv.variant_id = sp.variant_id AND sp.source_id = 2
                    WHERE pv.product_id = %s
                    ORDER BY pv.variant_id
                ''', [mapped_id])
                for row in cursor.fetchall():
                    mpd_variants.append({
                        'variant_id': row[0],
                        'ean': row[1],
                        'stock': row[2],
                        'size_id': row[3],
                        'size_name': row[4],
                        'producer_code': row[5],
                        'producer_color_name': row[6] or ''
                    })
        extra_context['mpd_variants'] = mpd_variants

        # Pobierz mapped_variant_id pierwszego wariantu z Matterhorn
        mapped_variant_id = None
        if hasattr(product, 'variants'):
            first_variant = product.variants.first()
            if first_variant and getattr(first_variant, 'mapped_variant_id', None):
                mapped_variant_id = first_variant.mapped_variant_id

        producer_color_name = ''
        if mapped_variant_id:
            with connections['MPD'].cursor() as cursor:
                cursor.execute('''
                    SELECT c.name
                    FROM product_variants pv
                    LEFT JOIN colors c ON pv.producer_color_id = c.id
                    WHERE pv.variant_id = %s
                    LIMIT 1
                ''', [mapped_variant_id])
                row = cursor.fetchone()
                if row:
                    producer_color_name = row[0] or ''
            logger.info(
                f"[change_view] mapped_variant_id: {mapped_variant_id}, producer_color_name: {producer_color_name}")
        extra_context['producer_color_name'] = producer_color_name

        # Dodaj sugerowane produkty z fuzzy search (RapidFuzz po stronie Pythona)
        suggested_products = []
        if product:
            try:
                with connections['MPD'].cursor() as cursor:
                    cursor.execute("""
                        SELECT p.id, p.name, b.name as brand
                        FROM products p
                        JOIN brands b ON p.brand_id = b.id
                        WHERE b.name = %s
                    """, [product.brand])
                    all_products = cursor.fetchall()
                    # all_products: [(id, name, brand), ...]
                    scored = []
                    for row in all_products:
                        score = fuzz.token_sort_ratio(product.name, row[1])
                        # Nowa metryka: ile % słów sugerowanego produktu jest w nazwie szukanego produktu
                        suggested_words = set(row[1].lower().replace(
                            '(', '').replace(')', '').replace('-', ' ').split())
                        query_words = set(product.name.lower().replace(
                            '(', '').replace(')', '').replace('-', ' ').split())
                        if suggested_words:
                            suggested_in_query = int(
                                100 * len(suggested_words & query_words) / len(suggested_words))
                        else:
                            suggested_in_query = 0
                        scored.append(
                            {'id': row[0], 'name': row[1], 'brand': row[2], 'similarity': score, 'suggested_in_query': suggested_in_query})
                    suggested_products = sorted(
                        scored, key=lambda x: x['similarity'], reverse=True)[:5]
            except Exception as e:
                logger.error(
                    f"Błąd fuzzy search sugerowanych produktów (RapidFuzz): {e}")
        extra_context['suggested_products'] = suggested_products

        if product and product.mapped_product_id:
            # Pobierz dane z MPD
            with connections['MPD'].cursor() as cursor:
                cursor.execute("""
                    SELECT p.name, p.description, b.name as brand
                    FROM products p
                    JOIN brands b ON p.brand_id = b.id
                    WHERE p.id = %s
                """, [product.mapped_product_id])
                row = cursor.fetchone()
                if row:
                    extra_context['is_mapped'] = True
                    # Sprawdź czy produkt ma warianty
                    cursor.execute(
                        "SELECT COUNT(*) FROM product_variants WHERE product_id = %s", [product.mapped_product_id])
                    variant_count = cursor.fetchone()[0]
                    extra_context['mpd_data'] = {
                        'name': row[0],
                        'description': row[1],
                        'brand': row[2],
                        'has_variants': variant_count > 0
                    }
                else:
                    extra_context['is_mapped'] = False
                    extra_context['mpd_data'] = {
                        'name': product.name,
                        'description': product.description,
                        'brand': product.brand,
                        'has_variants': False
                    }
        else:
            extra_context['is_mapped'] = False
            extra_context['mpd_data'] = {
                'name': product.name,
                'description': product.description,
                'brand': product.brand,
                'has_variants': False
            }

        # Pobierz domyślne wartości dla kodu producenta, koloru producenta i serii
        producer_code = ''
        series_name = ''
        if mapped_id:
            # Pobierz color_id produktu (główny kolor)
            main_color_id = None
            if product.color:
                with connections['MPD'].cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM colors WHERE name = %s AND parent_id IS NULL", [product.color])
                    color_row = cursor.fetchone()
                    if color_row:
                        main_color_id = color_row[0]
            if main_color_id:
                with connections['MPD'].cursor() as cursor:
                    # Pobierz wariant z tym samym color_id
                    cursor.execute('''
                        SELECT pv.producer_code, c.name as producer_color_name
                        FROM product_variants pv
                        LEFT JOIN colors c ON pv.producer_color_id = c.id
                        WHERE pv.product_id = %s AND pv.color_id = %s
                        LIMIT 1
                    ''', [mapped_id, main_color_id])
                    row = cursor.fetchone()
                    if row and len(row) > 1:
                        producer_code = row[0] or ''
                        producer_color_name = row[1] or ''
            # Nazwa serii
            with connections['MPD'].cursor() as cursor:
                cursor.execute('''
                    SELECT ps.name
                    FROM products p
                    JOIN product_series ps ON p.series_id = ps.id
                    WHERE p.id = %s
                    LIMIT 1
                ''', [mapped_id])
                row = cursor.fetchone()
                if row and len(row) > 0:
                    series_name = row[0] or ''
        extra_context['producer_code'] = producer_code
        extra_context['series_name'] = series_name

        return super().change_view(request, object_id, form_url, extra_context)

    def product_thumbnail(self, obj):
        image = Images.objects.filter(product=obj).first()
        if image and getattr(image, 'image_path', None):
            return format_html('<img src="{}" style="max-height:40px; max-width:40px;" />', image.image_path)
        return "-"
    product_thumbnail.short_description = "Miniatura"

    def add_missing_variants(self, request, product_id):
        if request.method == 'POST':
            try:
                # Pobierz mapped_product_id
                with connections['matterhorn'].cursor() as cursor:
                    cursor.execute(
                        "SELECT mapped_product_id FROM products WHERE id = %s", [product_id])
                    result = cursor.fetchone()
                    if not result or not result[0]:
                        return JsonResponse({'success': False, 'error': 'Produkt nie jest zmapowany'})
                    mapped_product_id = result[0]

                # Pobierz grupę rozmiarową i producer_color_id/producer_code z istniejących wariantów
                with connections['MPD'].cursor() as mpd_cursor:
                    mpd_cursor.execute("""
                        SELECT DISTINCT s.category, pv.producer_color_id, pv.producer_code
                        FROM product_variants pv 
                        JOIN sizes s ON pv.size_id = s.id 
                        WHERE pv.product_id = %s 
                        LIMIT 1
                    """, [mapped_product_id])
                    existing_variant = mpd_cursor.fetchone()
                    if not existing_variant or not existing_variant[0]:
                        return JsonResponse({'success': False, 'error': 'Nie można ustalić grupy rozmiarowej'})
                    size_category, producer_color_id, producer_code = existing_variant

                # Pobierz brakujące warianty (te bez mapped_variant_id)
                with connections['matterhorn'].cursor() as matterhorn_cursor:
                    matterhorn_cursor.execute("""
                        SELECT name, stock, ean, variant_uid 
                        FROM variants 
                        WHERE product_id = %s AND mapped_variant_id IS NULL
                    """, [product_id])
                    variants = matterhorn_cursor.fetchall()
                    if not variants:
                        return JsonResponse({'success': True, 'message': 'Brak wariantów do dodania.'})

                    # Pobierz kolor i cenę produktu
                    matterhorn_cursor.execute(
                        "SELECT color, price FROM products WHERE id = %s", [product_id])
                    color_result = matterhorn_cursor.fetchone()
                    if not color_result:
                        return JsonResponse({'success': False, 'error': 'Brak koloru dla produktu'})
                    product_color, product_price = color_result

                    # Pobierz ID koloru w MPD
                    with connections['MPD'].cursor() as mpd_cursor:
                        mpd_cursor.execute(
                            "SELECT id FROM colors WHERE name = %s", [product_color])
                        color_result = mpd_cursor.fetchone()
                        if not color_result:
                            return JsonResponse({'success': False, 'error': f'Brak koloru {product_color} w bazie MPD'})
                        color_id = color_result[0]

                        # Dodaj brakujące warianty
                        for size_name, stock, ean, variant_uid in variants:
                            # Pobierz ID rozmiaru
                            mpd_cursor.execute("""
                                SELECT id FROM sizes 
                                WHERE UPPER(name) = UPPER(%s) 
                                AND category = %s
                            """, [size_name, size_category])
                            size_result = mpd_cursor.fetchone()
                            if not size_result:
                                continue
                            size_id = size_result[0]

                            # Pobierz następny variant_id
                            mpd_cursor.execute(
                                "SELECT COALESCE(MAX(variant_id), 0) + 1 FROM product_variants")
                            variant_id = mpd_cursor.fetchone()[0]

                            # Pobierz producer_color_id powiązany z color_id
                            mpd_cursor.execute("""
                                SELECT producer_color_id 
                                FROM product_variants 
                                WHERE product_id = %s AND color_id = %s AND producer_color_id IS NOT NULL
                                LIMIT 1
                            """, [mapped_product_id, color_id])
                            pc_row = mpd_cursor.fetchone()
                            producer_color_id_to_use = pc_row[0] if pc_row else None

                            # Dodaj wariant z odpowiednim producer_color_id
                            mpd_cursor.execute("""
                                INSERT INTO product_variants 
                                (variant_id, product_id, color_id, size_id, ean, variant_uid, source_id, producer_color_id, producer_code)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, [variant_id, mapped_product_id, color_id, size_id, ean, variant_uid, 2, producer_color_id_to_use, producer_code])

                            # Dodaj stan magazynowy i cenę
                            mpd_cursor.execute("""
                                INSERT INTO stock_and_prices 
                                (variant_id, source_id, stock, price, currency)
                                VALUES (%s, %s, %s, %s, 'PLN')
                            """, [variant_id, 2, stock, product_price])

                            # Zaktualizuj informacje o wariancie w Matterhorn
                            matterhorn_cursor.execute("""
                                UPDATE variants 
                                SET mapped_variant_id = %s,
                                    is_mapped = true,
                                    last_updated = NOW()
                                WHERE variant_uid = %s
                            """, [variant_id, variant_uid])

                connections['matterhorn'].commit()
                connections['MPD'].commit()
                return JsonResponse({'success': True, 'message': 'Brakujące warianty zostały dodane.'})

            except Exception as e:
                logger.error(
                    f"Błąd podczas dodawania brakujących wariantów produktu {product_id}: {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda żądania'})

    def add_to_set(self, request, product_id):
        if request.method == 'POST':
            try:
                # Pobierz mapped_product_id dla aktualnego produktu
                with connections['matterhorn'].cursor() as mh_cursor:
                    mh_cursor.execute(
                        "SELECT mapped_product_id FROM products WHERE id = %s", [product_id])
                    row = mh_cursor.fetchone()
                    if not row or not row[0]:
                        return JsonResponse({'success': False, 'error': f'Produkt (Matterhorn) o ID {product_id} nie jest zmapowany do MPD.'})
                    mpd_product_id = row[0]
                related_product_id = request.POST.get('related_product_id')
                set_name = request.POST.get(
                    'set_name') or f'Zestaw {mpd_product_id} + {related_product_id}'
                if not related_product_id:
                    return JsonResponse({'success': False, 'error': 'Nie podano ID produktu do powiązania.'})
                # Jeśli podano ID z Matterhorna, pobierz mapped_product_id
                with connections['matterhorn'].cursor() as mh_cursor:
                    mh_cursor.execute("SELECT mapped_product_id FROM products WHERE id = %s", [
                                      related_product_id])
                    row = mh_cursor.fetchone()
                    if row and row[0]:
                        related_product_id = row[0]
                with connections['MPD'].cursor() as cursor:
                    # Sprawdź czy oba produkty istnieją w MPD
                    cursor.execute("SELECT id FROM products WHERE id = %s", [
                                   related_product_id])
                    if not cursor.fetchone():
                        return JsonResponse({'success': False, 'error': f'Produkt o ID {related_product_id} nie istnieje w MPD.'})
                    cursor.execute("SELECT id FROM products WHERE id = %s", [
                                   mpd_product_id])
                    if not cursor.fetchone():
                        return JsonResponse({'success': False, 'error': f'Produkt o ID {mpd_product_id} nie istnieje w MPD.'})
                    # Utwórz nowy zestaw
                    cursor.execute("""
                        INSERT INTO product_set (name, description, mapped_product_id)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, [set_name, f'Zestaw: {set_name}', mpd_product_id])
                    new_set_id = cursor.fetchone()[0]
                    # Dodaj oba produkty do tabeli pośredniej
                    cursor.execute("""
                        INSERT INTO product_set_items (product_set_id, product_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, [new_set_id, mpd_product_id])
                    cursor.execute("""
                        INSERT INTO product_set_items (product_set_id, product_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, [new_set_id, related_product_id])
                return JsonResponse({'success': True, 'message': 'Produkty zostały powiązane w nowym zestawie.'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda żądania'})

    @method_decorator(csrf_exempt, name='dispatch')
    def mpd_update_field(self, request, product_id, field_name):
        if request.method == 'POST':
            value = json.loads(request.body).get('value')
            # Pola z tabeli products
            products_fields = ['name', 'description', 'brand_id', 'series_id']
            # Pola z tabeli product_variants
            variants_fields = ['producer_code',
                               'producer_color_id', 'color_id']
            try:
                with connections['MPD'].cursor() as cursor:
                    if field_name in products_fields:
                        if field_name == 'brand_id':
                            try:
                                brand_id = int(value)
                            except ValueError:
                                with connections['MPD'].cursor() as c2:
                                    c2.execute(
                                        "SELECT id FROM brands WHERE LOWER(name) = LOWER(%s)", [value])
                                    row = c2.fetchone()
                                    if not row:
                                        return JsonResponse({'success': False, 'error': f'Nie znaleziono marki o nazwie {value}'})
                                    brand_id = row[0]
                            cursor.execute("UPDATE products SET brand_id = %s WHERE id = %s", [
                                           brand_id, product_id])
                        elif field_name == 'series_id':
                            try:
                                series_id = int(value)
                            except ValueError:
                                cursor.execute(
                                    "SELECT id FROM product_series WHERE LOWER(name) = LOWER(%s)", [value])
                                row = cursor.fetchone()
                                if row:
                                    series_id = row[0]
                                else:
                                    cursor.execute(
                                        "INSERT INTO product_series (name) VALUES (%s) RETURNING id", [value])
                                    series_id = cursor.fetchone()[0]
                            cursor.execute("UPDATE products SET series_id = %s WHERE id = %s", [
                                           series_id, product_id])
                        else:
                            cursor.execute(f"UPDATE products SET {field_name} = %s WHERE id = %s", [
                                           value, product_id])
                    elif field_name in ['producer_color_id', 'color_id']:
                        try:
                            color_id = int(value)
                        except ValueError:
                            cursor.execute(
                                "SELECT id FROM colors WHERE LOWER(name) = LOWER(%s)", [value])
                            row = cursor.fetchone()
                            if row:
                                color_id = row[0]
                            else:
                                cursor.execute(
                                    "INSERT INTO colors (name) VALUES (%s) RETURNING id", [value])
                                color_id = cursor.fetchone()[0]
                        cursor.execute(f"UPDATE product_variants SET {field_name} = %s WHERE product_id = %s", [
                                       color_id, product_id])
                    elif field_name in variants_fields:
                        cursor.execute(f"UPDATE product_variants SET {field_name} = %s WHERE product_id = %s", [
                                       value, product_id])
                    else:
                        return JsonResponse({'success': False, 'error': 'Nieprawidłowe pole'})
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})


@admin.register(UpdateLog)
class UpdateLogAdmin(admin.ModelAdmin):
    fields = ['last_update', 'description', 'data_items', 'data_inventory',]
    list_display = ['id', 'last_update', 'description',]
    readonly_fields = ['last_update', 'description',
                       'data_items', 'data_inventory',]
    list_per_page = 20


@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'product_id', 'product_name', 'variant_uid', 'variant_name',
                    'old_stock', 'new_stock', 'stock_change', 'change_type', 'timestamp']
    list_filter = ['change_type', 'timestamp']
    readonly_fields = ['id', 'variant_uid', 'product_id', 'product_name', 'variant_name',
                       'old_stock', 'new_stock', 'stock_change', 'change_type', 'timestamp']
    search_fields = ['product_id', 'product_name',
                     'variant_uid', 'variant_name']
    list_per_page = 50
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-timestamp')

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('popular-products/', self.admin_site.admin_view(
                self.popular_products_view), name='popular-products'),
            path('stock-statistics/', self.admin_site.admin_view(
                self.stock_statistics_view), name='stock-statistics'),
            path('clean-history/', self.admin_site.admin_view(self.clean_history_view),
                 name='clean-history'),


        ]
        return custom_urls + urls

    def popular_products_view(self, request):
        from django.shortcuts import render
        days = int(request.GET.get('days', 30))
        popular_products = get_popular_products(days=days, limit=50)

        context = {
            'popular_products': popular_products,
            'days': days,
            'title': f'Najbardziej popularne produkty (ostatnie {days} dni)'
        }
        return render(request, 'admin/stock_history/popular_products.html', context)

    def stock_statistics_view(self, request):
        from django.shortcuts import render
        days = int(request.GET.get('days', 30))
        stats = get_stock_statistics(days=days)

        context = {
            'stats': stats,
            'days': days,
            'title': f'Statystyki stanów magazynowych (ostatnie {days} dni)'
        }
        return render(request, 'admin/stock_history/statistics.html', context)

    def clean_history_view(self, request):
        from django.shortcuts import redirect
        from django.contrib import messages

        if request.method == 'POST':
            days_to_keep = int(request.POST.get('days_to_keep', 90))
            result = clean_old_stock_history(days_to_keep)
            messages.success(request, result)

        return redirect('admin:matterhorn_stockhistory_changelist')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_actions'] = True
        extra_context['actions'] = [
            {
                'name': 'popular_products',
                'url': 'popular-products/',
                'label': 'Popularne produkty',
                'description': 'Pokaż najbardziej popularne produkty'
            },
            {
                'name': 'statistics',
                'url': 'stock-statistics/',
                'label': 'Statystyki',
                'description': 'Pokaż statystyki stanów magazynowych'
            },
            {
                'name': 'clean_history',
                'url': 'clean-history/',
                'label': 'Wyczyść historię',
                'description': 'Usuń stare rekordy z historii'
            },


        ]
        return super().changelist_view(request, extra_context)
