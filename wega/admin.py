from django.contrib import admin
from django.http import JsonResponse
from django.db import connections
from django.urls import path
from django.shortcuts import render
import json
import logging
from rapidfuzz import fuzz
from .models import (
    Manufacturer,
    Category,
    Product,
    ProductImage,
    ProductAttribute,
    Promotion,
    New,
    RelatedProduct,
)

logger = logging.getLogger(__name__)


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ['name', 'manufacturer_id', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'manufacturer_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_id', 'parent', 'is_filter', 'created_at']
    list_filter = ['is_filter', 'created_at', 'parent']
    search_fields = ['name', 'category_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    raw_id_fields = ['parent']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['url', 'is_main', 'order']


class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 1
    fields = ['size', 'color', 'available', 'ean', 'color_image_url']


class RelatedProductInline(admin.TabularInline):
    model = RelatedProduct
    extra = 1
    fields = ['related_product_id']
    fk_name = 'product'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'product_id',
        'category',
        'manufacturer',
        'price',
        'gross_price',
        'is_new',
        'is_promotion',
        'is_mapped',
        'mapped_product_uid',
        'created_at',
    ]
    list_filter = [
        'is_new',
        'is_promotion',
        'is_mapped',
        'category',
        'manufacturer',
        'created_at',
        'updated_at',
    ]
    search_fields = ['name', 'product_id', 'symbol', 'description']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync', 'mapped_product_uid']
    ordering = ['name']
    raw_id_fields = ['category', 'manufacturer']
    inlines = [ProductImageInline, ProductAttributeInline, RelatedProductInline]
    
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('product_id', 'name', 'url', 'symbol')
        }),
        ('Kategorie i producent', {
            'fields': ('category', 'manufacturer')
        }),
        ('Ceny', {
            'fields': ('price', 'gross_price', 'pcs_in_a_box')
        }),
        ('Status', {
            'fields': ('is_new', 'is_promotion')
        }),
        ('Opis i szczegóły', {
            'fields': ('description', 'material', 'size_chart')
        }),
        ('Mapowanie MPD', {
            'fields': ('mapped_product_uid', 'is_mapped'),
            'classes': ('collapse',)
        }),
        ('Synchronizacja', {
            'fields': ('created_at', 'updated_at', 'last_api_sync'),
            'classes': ('collapse',)
        }),
    )

    def get_urls(self):
        from django.urls import path as url_path
        urls = super().get_urls()
        custom_urls = [
            url_path('mpd-update/<int:product_id>/',
                     self.admin_site.admin_view(self.mpd_update), name='mpd-update'),
            url_path('mpd-create/<int:product_id>/',
                     self.admin_site.admin_view(self.mpd_create), name='mpd-create'),
            url_path('assign-mapping/<int:product_id>/<int:mpd_product_id>/',
                     self.admin_site.admin_view(self.assign_mapping), name='assign-mapping'),
            url_path('mpd-update-field/<int:product_id>/<str:field_name>/',
                     self.admin_site.admin_view(self.mpd_update_field), name='mpd-update-field'),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Dodaj dane MPD do kontekstu"""
        extra_context = extra_context or {}
        
        try:
            product = Product.objects.get(id=object_id)
            is_mapped = bool(product.mapped_product_uid)
            
            # Pobierz dane MPD jeśli produkt jest zmapowany
            mpd_data = {}
            suggested_products = []
            main_colors = []
            mpd_paths = []
            selected_paths = []
            units = []
            
            # Inicjalizuj zmienne
            producer_color_name = ''
            producer_code = ''
            series_name = ''
            
            if is_mapped:
                # Pobierz dane produktu z MPD
                with connections['MPD'].cursor() as cursor:
                    cursor.execute("""
                        SELECT p.name, p.description, p.short_description, b.name as brand_name
                        FROM products p 
                        LEFT JOIN brands b ON p.brand_id = b.id 
                        WHERE p.id = %s
                    """, [product.mapped_product_uid])
                    result = cursor.fetchone()
                    if result:
                        mpd_data = {
                            'name': result[0] or '',
                            'description': result[1] or '',
                            'short_description': result[2] or '',
                            'brand': result[3] or ''
                        }
                    
                    # Pobierz główne kolory
                    cursor.execute(
                        "SELECT id, name FROM colors WHERE parent_id IS NULL ORDER BY name")
                    main_colors = [{'id': row[0], 'name': row[1]}
                                   for row in cursor.fetchall()]
                    
                    # Pobierz kolory producenta
                    cursor.execute(
                        "SELECT id, name, parent_id FROM colors WHERE parent_id IS NOT NULL ORDER BY name")
                    producer_colors = [{'id': row[0], 'name': row[1], 'parent_id': row[2]}
                                       for row in cursor.fetchall()]
                    
                    # Pobierz producer_color_name i producer_code
                    cursor.execute("""
                        SELECT c.name, pv.producer_code
                        FROM product_variants pv
                        LEFT JOIN colors c ON pv.producer_color_id = c.id
                        WHERE pv.product_id = %s
                        LIMIT 1
                    """, [product.mapped_product_uid])
                    result = cursor.fetchone()
                    if result:
                        producer_color_name = result[0] or ''
                        producer_code = result[1] or ''
                    
                    # Pobierz nazwę serii
                    cursor.execute("""
                        SELECT ps.name
                        FROM products p
                        LEFT JOIN product_series ps ON p.series_id = ps.id
                        WHERE p.id = %s
                    """, [product.mapped_product_uid])
                    series_result = cursor.fetchone()
                    if series_result:
                        series_name = series_result[0] or ''
            else:
                # Jeśli produkt nie jest zmapowany, pobierz tylko kolory
                with connections['MPD'].cursor() as cursor:
                    cursor.execute(
                        "SELECT id, name FROM colors WHERE parent_id IS NULL ORDER BY name")
                    main_colors = [{'id': row[0], 'name': row[1]}
                                   for row in cursor.fetchall()]
                    
                    cursor.execute(
                        "SELECT id, name, parent_id FROM colors WHERE parent_id IS NOT NULL ORDER BY name")
                    producer_colors = [{'id': row[0], 'name': row[1], 'parent_id': row[2]}
                                       for row in cursor.fetchall()]
            
            # Pobierz ścieżki, jednostki, atrybuty, marki, kategorie rozmiarów, fabric
            with connections['MPD'].cursor() as cursor:
                cursor.execute("SELECT id, name, path FROM path ORDER BY name")
                mpd_paths = [{'id': row[0], 'name': row[1], 'path': row[2]} 
                            for row in cursor.fetchall()]
                
                if is_mapped:
                    cursor.execute("SELECT path_id FROM product_path WHERE product_id = %s", 
                                 [product.mapped_product_uid])
                    selected_paths = [row[0] for row in cursor.fetchall()]
                    
                    cursor.execute("SELECT attribute_id FROM product_attributes WHERE product_id = %s", 
                                 [product.mapped_product_uid])
                    selected_attributes = [row[0] for row in cursor.fetchall()]
                else:
                    selected_paths = []
                    selected_attributes = []
                
                cursor.execute("SELECT unit_id, name FROM units ORDER BY name")
                units = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
                
                cursor.execute("SELECT id, name FROM attributes ORDER BY name")
                mpd_attributes = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
                
                cursor.execute("SELECT id, name FROM brands ORDER BY name")
                mpd_brands = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
                
                cursor.execute(
                    "SELECT DISTINCT category FROM sizes WHERE category IS NOT NULL ORDER BY category")
                size_categories = [row[0] for row in cursor.fetchall()]
                
                cursor.execute("SELECT id, name FROM fabric_component ORDER BY name")
                fabric_components = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
            
            # Pobierz sugerowane produkty z fuzzy search
            try:
                if product.manufacturer:
                    manufacturer_name = product.manufacturer.name if hasattr(
                        product.manufacturer, 'name') else str(product.manufacturer)
                    logger.info(f"[wega_fuzzy] Product: {product.name}, Manufacturer: {manufacturer_name}")
                    with connections['MPD'].cursor() as cursor:
                        # Pobierz wszystkie produkty z MPD (nie filtruj po marce, żeby pokazać markę dla każdego)
                        cursor.execute("""
                            SELECT p.id, p.name, COALESCE(b.name, '') as brand_name
                            FROM products p 
                            LEFT JOIN brands b ON p.brand_id = b.id 
                            ORDER BY p.name
                        """)
                        all_products = cursor.fetchall()
                        logger.info(f"[wega_fuzzy] Found {len(all_products)} products in MPD")
                        
                        scored = []
                        for row in all_products:
                            similarity = fuzz.token_sort_ratio(product.name, row[1])
                            suggested_words = set(row[1].lower().replace(
                                '(', '').replace(')', '').replace('-', ' ').split())
                            query_words = set(product.name.lower().replace(
                                '(', '').replace(')', '').replace('-', ' ').split())
                            if suggested_words:
                                suggested_in_query = int(
                                    100 * len(suggested_words & query_words) / len(suggested_words))
                            else:
                                suggested_in_query = 0
                            
                            # Upewnij się, że brand_name jest poprawnie obsłużony
                            brand_name = row[2] if row[2] else ''
                            
                            scored.append({
                                'id': row[0],
                                'name': row[1],
                                'brand': brand_name,
                                'similarity': similarity,
                                'suggested_in_query': suggested_in_query
                            })
                        
                        # Sortuj według podobieństwa i weź top 5
                        suggested_products = sorted(
                            scored, key=lambda x: x['similarity'], reverse=True)[:5]
                        logger.info(f"[wega_fuzzy] Final suggested_products count: {len(suggested_products)}")
                        if suggested_products:
                            logger.info(f"[wega_fuzzy] First suggested: {suggested_products[0]}")
                else:
                    suggested_products = []
            except Exception as e:
                logger.error(f"Błąd fuzzy search w wega: {e}")
                suggested_products = []
            
            # Przygotuj JSON dla atrybutów (wariantów)
            variants_data = []
            for attr in product.attributes.all():
                variants_data.append({
                    'size': attr.size or '',
                    'color': attr.color or '',
                    'available': attr.available or 0,
                    'ean': attr.ean or ''
                })
            variants_json = json.dumps(variants_data)
            
            extra_context.update({
                'is_mapped': is_mapped,
                'mpd_data': mpd_data,
                'suggested_products': suggested_products,
                'main_colors': main_colors,
                'producer_colors': producer_colors if 'producer_colors' in locals() else [],
                'mpd_paths': mpd_paths,
                'selected_paths': selected_paths,
                'units': units,
                'mpd_attributes': mpd_attributes,
                'selected_attributes': selected_attributes,
                'mpd_brands': mpd_brands,
                'size_categories': size_categories,
                'producer_color_name': producer_color_name,
                'producer_code': producer_code,
                'series_name': series_name,
                'selected_unit_id': None,
                'fabric_components': fabric_components,
                'variants_json': variants_json
            })
            
        except Exception as e:
            logger.error("Błąd podczas pobierania danych MPD: %s", e)
            extra_context.update({
                'is_mapped': False,
                'mpd_data': {},
                'suggested_products': [],
                'main_colors': [],
                'producer_colors': [],
                'mpd_paths': [],
                'selected_paths': [],
                'units': [],
                'mpd_attributes': [],
                'selected_attributes': [],
                'mpd_brands': [],
                'size_categories': [],
                'producer_color_name': '',
                'producer_code': '',
                'series_name': '',
                'selected_unit_id': None,
                'fabric_components': [],
                'variants_json': '[]'
            })
        
        return super().change_view(request, object_id, form_url, extra_context)

    def mpd_create(self, request, product_id):
        """Tworzy nowy produkt w bazie MPD przez API"""
        logger.info(f"🔄 mpd_create: Rozpoczynam dla produktu {product_id}")
        
        if request.method == 'POST':
            try:
                name = request.POST.get('mpd_name')
                description = request.POST.get('mpd_description')
                short_description = request.POST.get('mpd_short_description')
                brand_name = request.POST.get('mpd_brand')
                size_category = request.POST.get('mpd_size_category')
                main_color_id = request.POST.get('main_color_id')
                producer_code = request.POST.get('producer_code')
                producer_color_name = request.POST.get('producer_color_name')
                series_name = request.POST.get('series_name')
                unit_id = request.POST.get('unit_id')

                if not name:
                    return JsonResponse({'success': False, 'error': 'Nazwa jest wymagana'})

                # Przygotuj dane składu (fabric)
                fabric_components_ids = request.POST.getlist('fabric_component[]')
                fabric_percentages = request.POST.getlist('fabric_percentage[]')
                fabric_data = []
                for comp_id, perc in zip(fabric_components_ids, fabric_percentages):
                    if comp_id and perc and comp_id.strip() and perc.strip():
                        try:
                            fabric_data.append({
                                'component_id': int(comp_id),
                                'percentage': int(perc)
                            })
                        except (ValueError, TypeError):
                            pass

                converted_unit_id = int(unit_id) if unit_id and unit_id.isdigit() else None

                mpd_product_data = {
                    'name': name,
                    'description': description or '',
                    'short_description': short_description or '',
                    'brand_name': brand_name or '',
                    'size_category': size_category or '',
                    'main_color_id': main_color_id or None,
                    'producer_color_name': producer_color_name or '',
                    'producer_code': producer_code or '',
                    'series_name': series_name or '',
                    'unit_id': converted_unit_id,
                    'visibility': False,
                    'attributes': request.POST.getlist('mpd_attributes'),
                    'paths': request.POST.getlist('mpd_paths'),
                    'fabric': fabric_data
                }

                # Przygotuj dane dla wega (do mapowania przez Sagę)
                wega_data = {
                    'product_id': product_id
                }

                # Użyj Saga Pattern - najpierw musimy stworzyć saga.py dla wega
                # Na razie użyjmy bezpośredniego podejścia
                from wega.saga import SagaService

                logger.info(f"Sending data to Saga - MPD: {mpd_product_data}, WEGA: {wega_data}")

                saga_result = SagaService.create_product_with_mapping(
                    wega_data, mpd_product_data)

                if saga_result.status.value != 'completed':
                    error_msg = f"Saga failed: {saga_result.error}"
                    logger.error(error_msg)
                    return JsonResponse({'success': False, 'error': error_msg})

                # Pobierz mpd_product_id z wyniku Sagi
                mpd_product_id = None
                for step in saga_result.steps:
                    if step.name == 'create_mpd_product' and step.result:
                        mpd_product_id = step.result.get('mpd_product_id')
                        break

                if not mpd_product_id:
                    return JsonResponse({'success': False, 'error': 'Nie udało się pobrać ID produktu MPD'})

                logger.info(f"MPD product created with ID: {mpd_product_id}")

                variant_info = None
                for step in saga_result.steps:
                    if step.name == 'create_mpd_variants' and step.result:
                        variant_info = step.result
                        break

                message = f'Utworzono produkt w MPD (ID: {mpd_product_id})'
                if variant_info:
                    created_count = variant_info.get("created_variants", 0)
                    if created_count > 0:
                        message += f'. Dodano {created_count} wariantów'

                return JsonResponse({
                    'success': True,
                    'message': message,
                    'variant_info': variant_info
                })

            except Exception as e:
                logger.error("Błąd podczas tworzenia produktu MPD: %s", e)
                return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})

    def assign_mapping(self, request, product_id, mpd_product_id):
        """Przypisuje istniejący produkt MPD do produktu wega"""
        if request.method == 'POST':
            try:
                producer_code = request.POST.get('producer_code')
                producer_color_name = request.POST.get('producer_color_name')
                main_color_id = request.POST.get('main_color_id')
                producer_color_id = None

                # Obsługa koloru producenta
                if producer_color_name and main_color_id:
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute("SELECT id FROM colors WHERE name = %s", [producer_color_name])
                        pc_result = cursor.fetchone()
                        if pc_result:
                            producer_color_id = pc_result[0]
                        else:
                            cursor.execute("INSERT INTO colors (name, parent_id) VALUES (%s, %s) RETURNING id",
                                           [producer_color_name, main_color_id])
                            producer_color_id = cursor.fetchone()[0]

                # Zaktualizuj mapped_product_uid i is_mapped
                with connections['wega'].cursor() as cursor:
                    cursor.execute("""
                        UPDATE wega_product 
                        SET mapped_product_uid = %s, is_mapped = true, updated_at = NOW()
                        WHERE id = %s
                    """, [mpd_product_id, product_id])

                # Pobierz kategorię rozmiarową z MPD
                with connections['MPD'].cursor() as mpd_cursor:
                    mpd_cursor.execute("""
                        SELECT s.category
                        FROM product_variants pv
                        JOIN sizes s ON pv.size_id = s.id
                        WHERE pv.product_id = %s
                        LIMIT 1
                    """, [mpd_product_id])
                    size_cat_result = mpd_cursor.fetchone()
                    size_category = size_cat_result[0] if size_cat_result and size_cat_result[0] else None

                mapping_info = {}
                if size_category:
                    # Dodaj warianty do MPD
                    from wega.saga_variants import create_mpd_variants
                    try:
                        mapping_info = create_mpd_variants(
                            mpd_product_id, product_id, size_category,
                            producer_code, main_color_id, producer_color_name
                        )
                    except Exception as e:
                        logger.error(f"Błąd podczas dodawania wariantów: {e}")
                        mapping_info = {'error': f'Błąd wariantów: {str(e)}'}

                    # Upload zdjęć do bucketa
                    try:
                        from wega.saga import SagaService
                        upload_result = SagaService._upload_product_images(
                            mpd_product_id, product_id, producer_color_name
                        )
                        mapping_info['uploaded_images'] = upload_result.get('uploaded_images', 0)
                    except Exception as e:
                        logger.error(f"Błąd podczas uploadu zdjęć: {e}")
                        mapping_info['upload_error'] = str(e)
                else:
                    mapping_info = {'error': 'Brak kategorii rozmiarowej w MPD'}

                return JsonResponse({
                    'success': True,
                    'message': f'Produkt został przypisany do MPD ID {mpd_product_id}.',
                    'mapping_info': mapping_info
                })

            except Exception as e:
                logger.error("Błąd podczas przypisywania mapowania: %s", e)
                return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})

    def mpd_update(self, request, product_id):
        """Aktualizuje dane produktu w MPD"""
        if request.method == 'POST':
            try:
                product = Product.objects.get(id=product_id)
                if not product.mapped_product_uid:
                    return JsonResponse({'success': False, 'error': 'Produkt nie jest zmapowany'})

                # Dodawanie ścieżek
                mpd_paths = request.POST.getlist('mpd_paths')
                if mpd_paths:
                    with connections['MPD'].cursor() as cursor:
                        for path_id in mpd_paths:
                            cursor.execute(
                                "INSERT INTO product_path (product_id, path_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                [product.mapped_product_uid, path_id]
                            )
                    return JsonResponse({'success': True, 'message': 'Dodano ścieżki.'})

                # Usuwanie ścieżki
                remove_path_id = request.POST.get('remove_path_id')
                if remove_path_id:
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM product_path WHERE product_id = %s AND path_id = %s",
                            [product.mapped_product_uid, remove_path_id]
                        )
                    return JsonResponse({'success': True, 'message': 'Usunięto ścieżkę.'})

                # Dodawanie atrybutów
                mpd_attributes = request.POST.getlist('mpd_attributes')
                if mpd_attributes and len(request.POST) == 1:
                    with connections['MPD'].cursor() as cursor:
                        for attribute_id in mpd_attributes:
                            cursor.execute(
                                "INSERT INTO product_attributes (product_id, attribute_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                [product.mapped_product_uid, attribute_id]
                            )
                    return JsonResponse({'success': True, 'message': 'Dodano atrybuty.'})

                # Usuwanie atrybutu
                remove_attribute_id = request.POST.get('remove_attribute_id')
                if remove_attribute_id and len(request.POST) == 1:
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM product_attributes WHERE product_id = %s AND attribute_id = %s",
                            [product.mapped_product_uid, remove_attribute_id]
                        )
                    return JsonResponse({'success': True, 'message': 'Usunięto atrybut.'})

                return JsonResponse({'success': False, 'error': 'Brak danych do aktualizacji'})

            except Exception as e:
                logger.error("Błąd podczas aktualizacji produktu MPD: %s", e)
                return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})

    def mpd_update_field(self, request, product_id, field_name):
        """Aktualizuje pojedyncze pole w MPD przez API"""
        if request.method == 'POST':
            try:
                import requests
                from django.conf import settings

                data = json.loads(request.body)
                value = data.get('value')

                product = Product.objects.get(id=product_id)
                if not product.mapped_product_uid:
                    return JsonResponse({'success': False, 'error': 'Produkt nie jest zmapowany'})

                update_data = {field_name: value}

                mpd_api_url = f"{settings.MPD_API_URL}/products/{product.mapped_product_uid}/update/"
                response = requests.patch(mpd_api_url, json=update_data, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'success':
                        return JsonResponse({'success': True, 'message': 'Zaktualizowano pole'})
                    else:
                        return JsonResponse({
                            'success': False,
                            'error': result.get('message', 'Błąd API MPD')
                        })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Błąd API MPD: {response.status_code}'
                    })

            except Exception as e:
                logger.error("Błąd podczas aktualizacji pola MPD: %s", e)
                return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['product', 'value', 'start_date', 'end_date', 'created_at']
    list_filter = ['start_date', 'end_date', 'created_at']
    search_fields = ['product__name', 'product__product_id']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['product']
    ordering = ['-start_date']


@admin.register(New)
class NewAdmin(admin.ModelAdmin):
    list_display = ['product', 'start_date', 'end_date', 'created_at']
    list_filter = ['start_date', 'end_date', 'created_at']
    search_fields = ['product__name', 'product__product_id']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['product']
    ordering = ['-start_date']


