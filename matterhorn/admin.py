from django.contrib import admin  # type: ignore
from .models import Products, UpdateLog, ProductsProxy, ProductsProxyAdminForm, Images
from .defs_import import export_to_products
from django.utils.html import format_html
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import connections
from django.contrib.auth.decorators import user_passes_test
import logging
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

# Register your models here.
# admin.site.register(Products)


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_per_page = 30
    fields = ['active', 'name', 'description', 'creation_date', 'color', 'category_name', 'category_path', 'brand',  'url_link', 'new_collection', 'size_table', 'size_table_txt', 'size_table_html', 'price', 'get_product_images', 'get_variants', 'get_other_colors', 'get_product_in_set', ]
    list_display = ['id', 'active', 'name', 'color', 'category_name', 'brand', 'new_collection', 'price', 'timestamp', 'url_link', 'is_mapped', 'mapped_product_id', 'get_variant_names', 'get_other_colors_ids', 'get_product_in_set_ids']
    list_filter = ['active', 'category_name', 'brand', 'is_mapped']
    readonly_fields = ["active", "name", "description", "creation_date", 'url', 'url_link', "color", "category_name", "category_path", "brand", "new_collection", "size_table", "size_table_txt", "size_table_html", "price", "mapped_product_id", "is_mapped", "get_product_images", "get_variants", "get_other_colors", "get_product_in_set"]
    search_fields = ['id', 'name', 'brand', 'category_name']

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('mpd-update/<int:product_id>/', self.admin_site.admin_view(self.mpd_update), name='mpd-update'),
            path('mpd-create/<int:product_id>/', self.admin_site.admin_view(self.mpd_create), name='mpd-create'),
            path('assign-mapping/<int:product_id>/<int:mpd_product_id>/', self.admin_site.admin_view(self.assign_mapping), name='assign-mapping'),
        ]
        return custom_urls + urls

    def mpd_update(self, request, product_id):
        if request.method == 'POST':
            try:
                # Pobierz mapped_product_id
                with connections['matterhorn'].cursor() as cursor:
                    cursor.execute("SELECT mapped_product_id FROM products WHERE id = %s", [product_id])
                    result = cursor.fetchone()
                    if not result or not result[0]:
                        return JsonResponse({'success': False, 'error': 'Produkt nie jest zmapowany'})
                    mapped_product_id = result[0]

                # Pobierz kategorię rozmiarową z już zmapowanych wariantów
                with connections['matterhorn'].cursor() as cursor:
                    cursor.execute("SELECT mapped_variant_id FROM variants WHERE product_id = %s AND mapped_variant_id IS NOT NULL LIMIT 1", [product_id])
                    variant_result = cursor.fetchone()
                    if not variant_result or not variant_result[0]:
                        return JsonResponse({'success': False, 'error': 'Brak zmapowanych wariantów – nie można ustalić grupy rozmiarowej.'})
                    mapped_variant_id = variant_result[0]

                with connections['MPD'].cursor() as cursor:
                    cursor.execute("SELECT size_id FROM product_variants WHERE variant_id = %s", [mapped_variant_id])
                    size_result = cursor.fetchone()
                    if not size_result or not size_result[0]:
                        return JsonResponse({'success': False, 'error': 'Nie można ustalić size_id dla zmapowanego wariantu.'})
                    size_id = size_result[0]

                    cursor.execute("SELECT category FROM sizes WHERE id = %s", [size_id])
                    cat_result = cursor.fetchone()
                    if not cat_result or not cat_result[0]:
                        return JsonResponse({'success': False, 'error': 'Nie można ustalić grupy rozmiarowej na podstawie size_id.'})
                    size_category = cat_result[0]

                # Pobierz warianty z Matterhorn, które nie są jeszcze zmapowane
                with connections['matterhorn'].cursor() as matterhorn_cursor:
                    matterhorn_cursor.execute("""
                        SELECT name, stock, ean, variant_uid 
                        FROM variants 
                        WHERE product_id = %s AND mapped_variant_id IS NULL
                    """, [product_id])
                    variants = matterhorn_cursor.fetchall()

                    if not variants:
                        return JsonResponse({'success': True, 'message': 'Brak nowych wariantów do dodania.'})

                    # Pobierz kolor i cenę produktu
                    matterhorn_cursor.execute("SELECT color, price FROM products WHERE id = %s", [product_id])
                    color_result = matterhorn_cursor.fetchone()
                    if not color_result:
                        return JsonResponse({'success': False, 'error': 'Brak koloru dla produktu'})
                    product_color, product_price = color_result

                with connections['MPD'].cursor() as cursor:
                    # Pobierz ID koloru z MPD
                    cursor.execute("SELECT id FROM colors WHERE name = %s", [product_color])
                    color_result = cursor.fetchone()
                    if not color_result:
                        return JsonResponse({'success': False, 'error': f'Brak koloru {product_color} w bazie MPD'})
                    color_id = color_result[0]

                    for size_name, stock, ean, variant_uid in variants:
                        # Pobierz ID rozmiaru tylko z ustalonej kategorii
                        cursor.execute("SELECT id FROM sizes WHERE name = %s AND category = %s", [size_name, size_category])
                        size_result = cursor.fetchone()
                        if not size_result:
                            continue
                        size_id = size_result[0]

                        # Utwórz nowy wariant
                        cursor.execute("SELECT COALESCE(MAX(variant_id), 0) + 1 FROM product_variants")
                        variant_id = cursor.fetchone()[0]
                        cursor.execute("""
                            INSERT INTO product_variants 
                            (variant_id, product_id, color_id, size_id, ean, variant_uid, source_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, [variant_id, mapped_product_id, color_id, size_id, ean, variant_uid, 2])

                        cursor.execute("""
                            INSERT INTO stock_and_prices 
                            (variant_id, source_id, stock, price, currency)
                            VALUES (%s, %s, %s, %s, 'PLN')
                            ON CONFLICT (variant_id, source_id) DO UPDATE SET
                            stock = EXCLUDED.stock,
                            price = EXCLUDED.price
                        """, [variant_id, 2, stock, product_price])

                        with connections['matterhorn'].cursor() as matterhorn_cursor:
                            matterhorn_cursor.execute("""
                                UPDATE variants 
                                SET mapped_variant_id = %s,
                                    is_mapped = true,
                                    last_updated = NOW()
                                WHERE variant_uid = %s
                            """, [variant_id, variant_uid])
                    connections['matterhorn'].commit()

                return JsonResponse({'success': True, 'message': 'Nowe warianty zostały dodane do MPD (jeśli były do dodania).'})
            except Exception as e:
                logger.error(f"Błąd podczas aktualizacji wariantów produktu {product_id}: {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda żądania'})

    def mpd_create(self, request, product_id):
        if request.method == 'POST':
            try:
                name = request.POST.get('mpd_name')
                description = request.POST.get('mpd_description')
                brand = request.POST.get('mpd_brand')
                size_category = request.POST.get('mpd_size_category')

                if not size_category:
                    return JsonResponse({'success': False, 'error': 'Wybierz grupę rozmiarową przed mapowaniem produktu.'})

                logger.info(f"Rozpoczynam mapowanie produktu {product_id} z grupą rozmiarową: {size_category}")

                # Sprawdź czy produkt ma powiązane kolory
                with connections['matterhorn'].cursor() as cursor:
                    cursor.execute("""
                        SELECT p.mapped_product_id 
                        FROM products p
                        JOIN other_colors oc ON p.id = oc.product_id
                        WHERE oc.color_product_id = %s AND p.mapped_product_id IS NOT NULL
                        LIMIT 1
                    """, [product_id])
                    result = cursor.fetchone()
                    
                    if result and result[0]:
                        mapped_product_id = result[0]
                        logger.info(f"Znaleziono powiązany produkt z ID {mapped_product_id}")
                        
                        cursor.execute("""
                            UPDATE products 
                            SET mapped_product_id = %s,
                                last_updated = NOW()
                            WHERE id = %s
                        """, [mapped_product_id, product_id])
                        connections['matterhorn'].commit()
                        
                        return JsonResponse({
                            'success': True, 
                            'message': f'Produkt został przypisany do istniejącego ID {mapped_product_id} z powiązanego koloru'
                        })

                # Utwórz nowy produkt w bazie MPD
                with connections['MPD'].cursor() as cursor:
                    cursor.execute("SELECT id FROM brands WHERE name = %s", [brand])
                    brand_result = cursor.fetchone()
                    if not brand_result:
                        logger.error(f"Nie znaleziono marki {brand} w bazie MPD")
                        return JsonResponse({'success': False, 'error': 'Marka nie istnieje w bazie MPD'})
                    brand_id = brand_result[0]

                    cursor.execute("""
                        INSERT INTO products (name, description, brand_id)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, [name, description, brand_id])
                    new_product_id = cursor.fetchone()[0]
                    logger.info(f"Utworzono nowy produkt w MPD z ID {new_product_id}")

                    # Pobierz kolor produktu
                    with connections['matterhorn'].cursor() as matterhorn_cursor:
                        matterhorn_cursor.execute("""
                            SELECT color, price FROM products WHERE id = %s
                        """, [product_id])
                        color_result = matterhorn_cursor.fetchone()
                        if not color_result:
                            logger.error(f"Brak koloru dla produktu {product_id}")
                            return JsonResponse({'success': False, 'error': 'Brak koloru dla produktu'})
                        product_color, product_price = color_result
                        logger.info(f"Pobrano kolor {product_color} i cenę {product_price}")

                        cursor.execute("SELECT id FROM colors WHERE name = %s", [product_color])
                        color_result = cursor.fetchone()
                        if not color_result:
                            logger.error(f"Brak koloru {product_color} w bazie MPD")
                            return JsonResponse({'success': False, 'error': f'Brak koloru {product_color} w bazie MPD'})
                        color_id = color_result[0]

                        # Pobierz warianty produktu
                        matterhorn_cursor.execute("""
                            SELECT name, stock, ean, variant_uid 
                            FROM variants 
                            WHERE product_id = %s
                        """, [product_id])
                        variants = matterhorn_cursor.fetchall()
                        logger.info(f"Znaleziono {len(variants)} wariantów dla produktu {product_id}")

                        if not variants:
                            logger.error(f"Brak wariantów dla produktu {product_id}")
                            return JsonResponse({'success': False, 'error': 'Brak wariantów dla produktu'})

                        # Dodaj warianty do MPD tylko z wybranej kategorii rozmiarowej
                        for size_name, stock, ean, variant_uid in variants:
                            logger.info(f"Przetwarzam wariant: {size_name}, stock: {stock}, ean: {ean}, uid: {variant_uid}")
                            
                            # Pobierz ID rozmiaru tylko z wybranej kategorii
                            cursor.execute("SELECT id FROM sizes WHERE name = %s AND category = %s", [size_name, size_category])
                            size_result = cursor.fetchone()
                            if not size_result:
                                logger.warning(f"Brak rozmiaru {size_name} w grupie {size_category} w bazie MPD")
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
                                logger.info(f"Znaleziono istniejący wariant z ID {variant_id}")
                            else:
                                cursor.execute("""
                                    SELECT COALESCE(MAX(variant_id), 0) + 1 
                                    FROM product_variants
                                """)
                                variant_id = cursor.fetchone()[0]
                                logger.info(f"Utworzono nowy wariant z ID {variant_id}")

                                cursor.execute("""
                                    INSERT INTO product_variants 
                                    (variant_id, product_id, color_id, size_id, ean, variant_uid, source_id)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, [variant_id, new_product_id, color_id, size_id, ean, variant_uid, 2])

                            cursor.execute("""
                                INSERT INTO stock_and_prices 
                                (variant_id, source_id, stock, price, currency)
                                VALUES (%s, %s, %s, %s, 'PLN')
                                ON CONFLICT (variant_id, source_id) DO UPDATE SET
                                stock = EXCLUDED.stock,
                                price = EXCLUDED.price
                            """, [variant_id, 2, stock, product_price])

                            matterhorn_cursor.execute("""
                                UPDATE variants 
                                SET mapped_variant_id = %s,
                                    is_mapped = true,
                                    last_updated = NOW()
                                WHERE variant_uid = %s
                            """, [variant_id, variant_uid])
                            logger.info(f"Zaktualizowano wariant {variant_uid} w bazie Matterhorn")

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
                        logger.info(f"Zaktualizowano produkt {product_id} w bazie Matterhorn")

                return JsonResponse({'success': True, 'message': 'Produkt został pomyślnie zmapowany'})
            except Exception as e:
                logger.error(f"Błąd podczas mapowania produktu {product_id}: {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda żądania'})

    def assign_mapping(self, request, product_id, mpd_product_id):
        if request.method == 'POST':
            try:
                with connections['matterhorn'].cursor() as cursor:
                    cursor.execute("""
                        UPDATE products
                        SET mapped_product_id = %s, is_mapped = true, last_updated = NOW()
                        WHERE id = %s
                    """, [mpd_product_id, product_id])
                    connections['matterhorn'].commit()
                return JsonResponse({'success': True, 'message': f'Produkt został przypisany do MPD ID {mpd_product_id}.'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda żądania'})

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('variants', 'other_colors', 'product_in_set')
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
                html += f'''
                    <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; min-width: 200px;">
                        <div><strong>Nazwa:</strong> {variant.name or '-'}</div>
                        <div><strong>Stan:</strong> {variant.stock or '-'}</div>
                        <div><strong>EAN:</strong> {variant.ean or '-'}</div>
                        <div><strong>Czas przetwarzania:</strong> {variant.max_processing_time or '-'}</div>
                        <div><strong>Mapped variant ID:</strong> {variant.mapped_variant_id or '-'}</div>
                        <div><strong>Is mapped:</strong> {variant.is_mapped or '-'}</div>
                    </div>
                '''
            html += '</div>'
            return format_html(html)
        return "-"
    get_variants.short_description = 'Variants'

    def get_other_colors(self, obj):
        other_colors = obj.other_colors.all()
        if other_colors:
            # W widoku listy zawsze zwracamy tylko ID
            if obj._state.adding or not hasattr(obj, '_meta'):
                return ", ".join([str(color.color_product.id) for color in other_colors if color.color_product])
            # Dla widoku szczegółów zachowujemy obecną funkcjonalność
            html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
            for color in other_colors:
                if color.color_product:
                    first_image = Images.objects.filter(product=color.color_product).first()
                    image_html = ''
                    if first_image and first_image.image_path:
                        image_html = f'<a href="{first_image.image_path}" target="_blank" rel="noopener noreferrer"><img src="{first_image.image_path}" style="max-height: 100px; max-width: 100px; margin: 5px; cursor: pointer;" /></a>'
                    
                    html += f'''
                        <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; min-width: 200px;">
                            <div style="text-align: center; margin-bottom: 10px;">{image_html}</div>
                            <div><strong>ID:</strong> {color.color_product.id}</div>
                            <div><strong>Nazwa:</strong> {color.color_product.name or '-'}</div>
                            <div><strong>Kolor:</strong> {color.color_product.color or '-'}</div>
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
                    # Pobierz pierwsze zdjęcie produktu
                    first_image = Images.objects.filter(product=product.set_product).first()
                    image_html = ''
                    if first_image and first_image.image_path:
                        image_html = f'<a href="{first_image.image_path}" target="_blank" rel="noopener noreferrer"><img src="{first_image.image_path}" style="max-height: 100px; max-width: 100px; margin: 5px; cursor: pointer;" /></a>'
                    
                    html += f'''
                        <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; min-width: 200px;">
                            <div style="text-align: center; margin-bottom: 10px;">{image_html}</div>
                            <div><strong>ID:</strong> {product.set_product.id}</div>
                            <div><strong>Nazwa:</strong> {product.set_product.name or '-'}</div>
                            <div><strong>Kolor:</strong> {product.set_product.color or '-'}</div>
                            <div style="margin-top: 10px;">
                                <a href="/admin/matterhorn/products/{product.set_product.id}/change/" class="button" style="background-color: #417690; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">Edytuj produkt</a>
                            </div>
                        </div>
                    '''
            html += '</div>'
            return format_html(html)
        return "-"
    get_product_in_set.short_description = 'Products in Set'

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
    get_product_in_set_ids.short_description = 'Products in Set IDs'

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
        
        # Pobierz kategorie rozmiarów z MPD
        try:
            with connections['MPD'].cursor() as cursor:
                cursor.execute("SELECT DISTINCT category FROM sizes WHERE category IS NOT NULL ORDER BY category")
                size_categories = [row[0] for row in cursor.fetchall()]
            extra_context['size_categories'] = size_categories
        except Exception as e:
            logger.error(f"Błąd pobierania kategorii rozmiarów z MPD: {e}")
            extra_context['size_categories'] = []

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
                        scored.append({'id': row[0], 'name': row[1], 'brand': row[2], 'similarity': score})
                    suggested_products = sorted(scored, key=lambda x: x['similarity'], reverse=True)[:5]
            except Exception as e:
                logger.error(f"Błąd fuzzy search sugerowanych produktów (RapidFuzz): {e}")
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
                    extra_context['mpd_data'] = {
                        'name': row[0],
                        'description': row[1],
                        'brand': row[2]
                    }
                else:
                    extra_context['is_mapped'] = False
                    extra_context['mpd_data'] = {
                        'name': product.name,
                        'description': product.description,
                        'brand': product.brand
                    }
        else:
            extra_context['is_mapped'] = False
            extra_context['mpd_data'] = {
                'name': product.name,
                'description': product.description,
                'brand': product.brand
            }
        
        return super().change_view(request, object_id, form_url, extra_context)


'''@admin.register(ProductsProxy)
class MapperAdmin(admin.ModelAdmin):
    form = ProductsProxyAdminForm
    list_per_page = 30
    fields = ['active', 'name', 'description', 'creation_date', 'color', 'category_name', 'category_path', 'brand', 'url', 'new_collection', 'size_table', 'size_table_txt', 'size_table_html', 'price', 
              'mapped_product_id', 'is_mapped', 'get_product_color_id', 'get_variant_names', 'get_product_in_set']
    list_display = ('id', 'name', 'color', 'category_name', 'brand', 'timestamp', 'mapped_product_id', 'is_mapped', 'get_product_color_id', 'get_variant_names', 'get_product_in_set', 'last_updated', )
    list_filter = ('category_name', 'brand', 'is_mapped', )
    readonly_fields = ["active", "name", "description", "creation_date", "color", "category_name", "category_path", "brand", "new_collection", "size_table", "size_table_txt", "size_table_html", "price",
                       "mapped_product_id", "is_mapped", 'get_product_color_id', 'get_variant_names', 'get_product_in_set'] 
    search_fields = ('id', 'name', 'brand')
    actions = [export_to_products]

    def get_product_color_id(self, obj):
        return obj.mapped_product_id

    def get_variant_names(self, obj):
        variants = obj.variants.all()
        if variants:
            return ", ".join([variant.name for variant in variants])
        return "-"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions'''


@admin.register(UpdateLog)
class UpdateLogAdmin(admin.ModelAdmin):
    fields = ['last_update', 'description', 'data_items', 'data_inventory',]
    list_display = ['id', 'last_update', 'description',]
    readonly_fields = ['last_update', 'description', 'data_items', 'data_inventory',]
    list_per_page = 20


'''@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'level', 'message')
    list_filter = ('level', 'timestamp')
    search_fields = ('message',)'''
