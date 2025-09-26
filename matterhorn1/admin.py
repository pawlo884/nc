from django.contrib import admin
from django.http import JsonResponse
from django.db import connections, transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html
import json
import logging
import requests
from rapidfuzz import fuzz
from .models import (
    Brand, Category, Product, ProductDetails, ProductImage,
    ProductVariant, ApiSyncLog, Saga, SagaStep, StockHistory
)
from .transaction_logger import logged_transaction, DatabaseOperationTracker
from .database_utils import DatabaseUtils, SafeCrossDatabaseOperations

logger = logging.getLogger(__name__)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['brand_id', 'name', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['brand_id', 'name']
    readonly_fields = ['brand_id', 'created_at', 'updated_at']
    ordering = ['name']

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('brand_id', 'name')
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_id', 'name', 'path', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['category_id', 'name', 'path']
    readonly_fields = ['category_id', 'created_at', 'updated_at']
    ordering = ['name']

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('category_id', 'name', 'path')
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ProductDetailsInline(admin.StackedInline):
    model = ProductDetails
    extra = 0
    fields = ['weight', 'size_table', 'size_table_txt', 'size_table_html']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ['image_url', 'order']
    readonly_fields = ['image_url']


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ['variant_uid', 'name', 'stock', 'ean',
              'max_processing_time', 'is_mapped', 'mapped_variant_uid']
    readonly_fields = ['variant_uid', 'mapped_variant_uid']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'product_uid', 'name', 'brand', 'category', 'active',
        'stock_total', 'is_mapped', 'mapped_product_uid', 'created_at', 'updated_at'
    ]
    list_display_links = ['product_uid', 'name']
    list_filter = [
        'brand', 'category', 'active', 'is_mapped', 'created_at', 'updated_at'
    ]
    search_fields = [
        'product_uid', 'name', 'description', 'brand__name', 'category__name'
    ]
    readonly_fields = [
        'product_uid', 'mapped_product_uid', 'created_at', 'updated_at', 'stock_total'
    ]
    ordering = ['-product_uid']
    inlines = [ProductDetailsInline, ProductImageInline, ProductVariantInline]
    actions = ('bulk_map_to_mpd_action',
               'bulk_create_mpd_action', 'sync_with_mpd_action')

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': (
                'product_uid', 'name', 'description', 'brand', 'category'
            )
        }),
        ('Ceny i dostępność', {
            'fields': ('prices', 'active', 'new_collection')
        }),
        ('Dodatkowe dane', {
            'fields': (
                'color', 'url', 'products_in_set', 'other_colors'
            ),
            'classes': ('collapse',)
        }),
        ('Mapowanie MPD', {
            'fields': ('mapped_product_uid',),
            'classes': ('collapse',)
        }),
        ('Metadane', {
            'fields': ('creation_date', 'last_api_sync', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def stock_total(self, obj):
        """Wyświetl całkowity stan magazynowy"""
        return obj.stock_total
    stock_total.short_description = 'Stan magazynowy'
    stock_total.admin_order_field = 'productvariant__stock'

    def get_queryset(self, request):
        """Optymalizacja zapytań"""
        return super().get_queryset(request).select_related(
            'brand', 'category'
        ).prefetch_related('variants')

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
            # Nowe zaawansowane funkcjonalności
            url_path('bulk-map-to-mpd/',
                     self.admin_site.admin_view(self.bulk_map_to_mpd), name='bulk-map-to-mpd'),
            url_path('bulk-create-mpd/',
                     self.admin_site.admin_view(self.bulk_create_mpd), name='bulk-create-mpd'),
            url_path('upload-images/<int:product_id>/',
                     self.admin_site.admin_view(self.upload_images), name='upload-images'),
            url_path('auto-map-variants/<int:product_id>/',
                     self.admin_site.admin_view(self.auto_map_variants), name='auto-map-variants'),
            path('sync-with-mpd/<int:product_id>/',
                 self.admin_site.admin_view(self.sync_with_mpd), name='sync-with-mpd'),
            path('add-variants/<int:product_id>/',
                 self.admin_site.admin_view(self.add_variants), name='add-variants'),
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

                    # Pobierz główne kolory (bez parent_id)
                    cursor.execute(
                        "SELECT id, name FROM colors WHERE parent_id IS NULL ORDER BY name")
                    main_colors = [{'id': row[0], 'name': row[1]}
                                   for row in cursor.fetchall()]

                    # Pobierz kolory producenta (z parent_id - podkolory)
                    cursor.execute(
                        "SELECT id, name, parent_id FROM colors WHERE parent_id IS NOT NULL ORDER BY name")
                    producer_colors = [{'id': row[0], 'name': row[1], 'parent_id': row[2]}
                                       for row in cursor.fetchall()]

                    # Pobierz producer_color_name z pierwszego wariantu
                    cursor.execute("""
                        SELECT c.name 
                        FROM product_variants pv
                        LEFT JOIN colors c ON pv.producer_color_id = c.id
                        WHERE pv.product_id = %s
                        LIMIT 1
                    """, [product.mapped_product_uid])
                    result = cursor.fetchone()
                    if result:
                        producer_color_name = result[0] or ''
            else:
                # Jeśli produkt nie jest zmapowany, pobierz tylko kolory
                with connections['MPD'].cursor() as cursor:
                    # Pobierz główne kolory (bez parent_id)
                    cursor.execute(
                        "SELECT id, name FROM colors WHERE parent_id IS NULL ORDER BY name")
                    main_colors = [{'id': row[0], 'name': row[1]}
                                   for row in cursor.fetchall()]

                    # Pobierz kolory producenta (z parent_id - podkolory)
                    cursor.execute(
                        "SELECT id, name, parent_id FROM colors WHERE parent_id IS NOT NULL ORDER BY name")
                    producer_colors = [{'id': row[0], 'name': row[1], 'parent_id': row[2]}
                                       for row in cursor.fetchall()]

            # Pobierz ścieżki (dla wszystkich produktów)
            with connections['MPD'].cursor() as cursor:
                cursor.execute(
                    "SELECT id, name, path FROM path ORDER BY name")
                mpd_paths = [{'id': row[0], 'name': row[1],
                              'path': row[2]} for row in cursor.fetchall()]

                # Pobierz przypisane ścieżki (tylko dla zmapowanych produktów)
                if is_mapped:
                    cursor.execute("SELECT path_id FROM product_path WHERE product_id = %s", [
                                   product.mapped_product_uid])
                    selected_paths = [row[0] for row in cursor.fetchall()]

                    # Pobierz przypisane atrybuty
                    cursor.execute("SELECT attribute_id FROM product_attributes WHERE product_id = %s", [
                                   product.mapped_product_uid])
                    selected_attributes = [row[0] for row in cursor.fetchall()]
                else:
                    selected_paths = []
                    selected_attributes = []

                # Pobierz jednostki
                cursor.execute("SELECT id, name FROM units ORDER BY name")
                units = [{'id': row[0], 'name': row[1]}
                         for row in cursor.fetchall()]

                # Pobierz atrybuty
                cursor.execute("SELECT id, name FROM attributes ORDER BY name")
                mpd_attributes = [{'id': row[0], 'name': row[1]}
                                  for row in cursor.fetchall()]

                # Pobierz marki
                cursor.execute("SELECT id, name FROM brands ORDER BY name")
                mpd_brands = [{'id': row[0], 'name': row[1]}
                              for row in cursor.fetchall()]

                # Pobierz kategorie rozmiarów
                cursor.execute(
                    "SELECT DISTINCT category FROM sizes WHERE category IS NOT NULL ORDER BY category")
                size_categories = [row[0] for row in cursor.fetchall()]

            # Pobierz sugerowane produkty (tylko dla niezmapowanych produktów)
            if not is_mapped:
                with connections['MPD'].cursor() as cursor:
                    cursor.execute("""
                        SELECT p.id, p.name, b.name as brand_name
                        FROM products p 
                        LEFT JOIN brands b ON p.brand_id = b.id 
                        WHERE LOWER(p.name) LIKE LOWER(%s)
                        ORDER BY p.name
                        LIMIT 10
                    """, [f'%{product.name[:20]}%'])
                    suggested_products = [
                        {
                            'id': row[0],
                            'name': row[1],
                            'brand': row[2] or '',
                            'similarity': 85.0,  # Placeholder
                            'suggested_in_query': 75.0  # Placeholder
                        }
                        for row in cursor.fetchall()
                    ]

            extra_context.update({
                'is_mapped': is_mapped,
                'mpd_data': mpd_data,
                'suggested_products': suggested_products,
                'main_colors': main_colors,
                'producer_colors': producer_colors,
                'mpd_paths': mpd_paths,
                'selected_paths': selected_paths,
                'units': units,
                'mpd_attributes': mpd_attributes,
                'selected_attributes': selected_attributes,
                'mpd_brands': mpd_brands,
                'size_categories': size_categories,
                'producer_color_name': producer_color_name,
                'producer_code': '',
                'series_name': '',
                'selected_unit_id': None
            })

        except Exception as e:
            logger.error("Błąd podczas pobierania danych MPD: %s", e)
            # Pobierz kolory i jednostki dla niezmapowanych produktów
            with connections['MPD'].cursor() as cursor:
                # Pobierz główne kolory (bez parent_id)
                cursor.execute(
                    "SELECT id, name FROM colors WHERE parent_id IS NULL ORDER BY name")
                main_colors = [{'id': row[0], 'name': row[1]}
                               for row in cursor.fetchall()]

                # Pobierz kolory producenta (z parent_id - podkolory)
                cursor.execute(
                    "SELECT id, name, parent_id FROM colors WHERE parent_id IS NOT NULL ORDER BY name")
                producer_colors = [{'id': row[0], 'name': row[1], 'parent_id': row[2]}
                                   for row in cursor.fetchall()]

                # Pobierz jednostki
                cursor.execute("SELECT id, name FROM units ORDER BY name")
                units = [{'id': row[0], 'name': row[1]}
                         for row in cursor.fetchall()]

                # Pobierz atrybuty
                cursor.execute("SELECT id, name FROM attributes ORDER BY name")
                mpd_attributes = [{'id': row[0], 'name': row[1]}
                                  for row in cursor.fetchall()]

                # Pobierz marki
                cursor.execute("SELECT id, name FROM brands ORDER BY name")
                mpd_brands = [{'id': row[0], 'name': row[1]}
                              for row in cursor.fetchall()]

                # Pobierz kategorie rozmiarów
                cursor.execute(
                    "SELECT DISTINCT category FROM sizes WHERE category IS NOT NULL ORDER BY category")
                size_categories = [row[0] for row in cursor.fetchall()]

                # Pobierz ścieżki
                cursor.execute("SELECT id, name, path FROM path ORDER BY name")
                mpd_paths = [{'id': row[0], 'name': row[1], 'path': row[2]}
                             for row in cursor.fetchall()]

            extra_context.update({
                'is_mapped': False,
                'mpd_data': {},
                'suggested_products': [],
                'main_colors': main_colors,
                'producer_colors': producer_colors,
                'mpd_paths': mpd_paths,
                'selected_paths': [],
                'units': units,
                'mpd_attributes': mpd_attributes,
                'selected_attributes': [],
                'producer_color_name': producer_color_name,
                'producer_code': '',
                'series_name': '',
                'selected_unit_id': None
            })

        return super().change_view(request, object_id, form_url, extra_context)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def mpd_create(self, request, product_id):
        """Tworzy nowy produkt w bazie MPD przez API"""
        if request.method == 'POST':
            try:
                import requests
                from django.conf import settings

                name = request.POST.get('mpd_name')
                description = request.POST.get('mpd_description')
                short_description = request.POST.get('mpd_short_description')
                brand_name = request.POST.get('mpd_brand')
                size_category = request.POST.get('mpd_size_category')
                main_color_id = request.POST.get('main_color_id')
                producer_code = request.POST.get('producer_code')
                producer_color_name = request.POST.get('producer_color_name')
                unit_id = request.POST.get('unit_id')

                logger.info(
                    f"Form data: name='{name}', description='{description}', brand_name='{brand_name}', size_category='{size_category}', main_color_id='{main_color_id}', unit_id='{unit_id}'")

                if not name:
                    return JsonResponse({'success': False, 'error': 'Nazwa jest wymagana'})

                # KROK 6: Nazwa + Opis + Krótki opis + Atrybuty + Marka + Grupa rozmiarowa + Główny kolor + Kolor producenta
                mpd_data = {
                    'name': name,
                    'description': description or '',
                    'short_description': short_description or '',
                    'brand_name': brand_name or '',
                    'size_category': size_category or '',
                    'main_color_id': main_color_id or None,
                    'producer_color_name': producer_color_name or '',
                    'producer_code': producer_code or '',
                    'unit_id': None,   # Wyłączone na razie
                    'visibility': False
                }

                # Warianty wyłączone na razie
                # variants = []

                # Wyślij żądanie do API MPD (bulk create)
                mpd_api_url = f"{settings.MPD_API_URL}/bulk-create/"
                logger.info(f"Sending data to MPD: {mpd_data}")
                response = requests.post(
                    mpd_api_url, json={'products': [mpd_data]}, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Bulk create response: {result}")
                    logger.info(f"Response status: {result.get('status')}")
                    logger.info(
                        f"Created products count: {len(result.get('created_products', []))}")
                    logger.info(
                        f"Errors count: {len(result.get('errors', []))}")
                    logger.info(
                        f"Total created: {result.get('total_created', 0)}")

                    if result.get('status') == 'success':
                        created_products = result.get('created_products', [])
                        errors = result.get('errors', [])
                        logger.info(f"Created products: {created_products}")
                        logger.info(f"Errors: {errors}")

                        if created_products:
                            mpd_product_id = created_products[0].get('id')
                            logger.info(f"MPD product ID: {mpd_product_id}")
                        else:
                            logger.error("No products created in response")
                            error_msg = "Nie utworzono produktu"
                            if errors:
                                error_msg += f". Błędy: {', '.join(errors)}"
                            return JsonResponse({'success': False, 'error': error_msg})

                        # Użyj Saga Pattern do bezpiecznej operacji między bazami
                        from matterhorn1.saga import SagaService

                        # Przygotuj dane dla Saga
                        matterhorn_data = {
                            'product_id': product_id,
                            'mpd_product_id': mpd_product_id
                        }

                        mpd_data = {
                            'mpd_product_id': mpd_product_id,
                            'attributes': request.POST.getlist('mpd_attributes')
                        }

                        # Wykonaj operację używając Saga Pattern
                        saga_result = SagaService.create_product_with_mapping(
                            matterhorn_data, mpd_data)

                        if saga_result.status.value != 'completed':
                            error_msg = f"Saga failed: {saga_result.error}"
                            logger.error(error_msg)
                            return JsonResponse({'success': False, 'error': error_msg})

                        # Dodaj warianty jeśli podano size_category
                        variant_info = None
                        if size_category:
                            logger.info(
                                f"Dodawanie wariantów dla produktu {product_id} z kategorią rozmiarów: {size_category}")

                            # Utwórz producer_color_id z producer_color_name i main_color_id
                            producer_color_id_to_use = None
                            if producer_color_name and main_color_id:
                                try:
                                    with connections['MPD'].cursor() as cursor:
                                        # Sprawdź czy kolor producenta już istnieje
                                        cursor.execute("SELECT id FROM colors WHERE name = %s AND parent_id = %s",
                                                       [producer_color_name, main_color_id])
                                        pc_row = cursor.fetchone()
                                        if pc_row:
                                            producer_color_id_to_use = pc_row[0]
                                        else:
                                            # Utwórz nowy kolor producenta
                                            cursor.execute("INSERT INTO colors (name, parent_id) VALUES (%s, %s) RETURNING id",
                                                           [producer_color_name, main_color_id])
                                            row = cursor.fetchone()
                                            if row:
                                                producer_color_id_to_use = row[0]
                                                logger.info(
                                                    f"Utworzono nowy kolor producenta: {producer_color_name} (ID: {producer_color_id_to_use})")
                                except Exception as e:
                                    logger.error(
                                        f"Błąd podczas tworzenia koloru producenta: {e}")

                            variant_info = self.add_new_variants_to_mpd(
                                product_id, mpd_product_id, size_category,
                                producer_color_id=producer_color_id_to_use, producer_code=producer_code
                            )
                            logger.info(
                                f"Wynik dodawania wariantów: {variant_info}")

                        message = f'Utworzono produkt w MPD (ID: {mpd_product_id})'
                        if variant_info:
                            message += f'. Dodano {variant_info.get("added", 0)} wariantów'
                            if variant_info.get('missing_sizes'):
                                message += f'. Brakujące rozmiary: {", ".join(variant_info["missing_sizes"])}'

                        return JsonResponse({
                            'success': True,
                            'message': message,
                            'variant_info': variant_info
                        })
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
                logger.error("Błąd podczas tworzenia produktu MPD: %s", e)
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

                # Aktualizacja koloru producenta
                if 'producer_color_name' in request.POST and len(request.POST) == 1:
                    producer_color_name = request.POST.get(
                        'producer_color_name')
                    main_color_id = request.POST.get('main_color_id')

                    if not main_color_id:
                        return JsonResponse({'success': False, 'error': 'Brak głównego koloru'})

                    with connections['MPD'].cursor() as cursor:
                        # Pobierz kolor aktualnego produktu z matterhorn1
                        with connections['matterhorn1'].cursor() as matterhorn_cursor:
                            matterhorn_cursor.execute(
                                "SELECT color FROM product WHERE id = %s", [product_id])
                            color_result = matterhorn_cursor.fetchone()
                            if not color_result:
                                return JsonResponse({'success': False, 'error': 'Brak koloru dla produktu'})
                            product_color = color_result[0]

                        # Pobierz ID koloru w MPD
                        cursor.execute(
                            "SELECT id FROM colors WHERE name = %s", [product_color])
                        color_row = cursor.fetchone()
                        if not color_row:
                            return JsonResponse({'success': False, 'error': f'Brak koloru {product_color} w bazie MPD'})
                        color_id = color_row[0]

                        # Sprawdź czy kolor producenta już istnieje
                        cursor.execute("SELECT id FROM colors WHERE name = %s AND parent_id = %s",
                                       [producer_color_name, color_id])
                        pc_row = cursor.fetchone()
                        if pc_row:
                            producer_color_id = pc_row[0]
                        else:
                            # Utwórz nowy kolor producenta
                            cursor.execute("INSERT INTO colors (name, parent_id) VALUES (%s, %s) RETURNING id",
                                           [producer_color_name, color_id])
                            row = cursor.fetchone()
                            if row:
                                producer_color_id = row[0]
                            else:
                                return JsonResponse({'success': False, 'error': 'Nie udało się utworzyć koloru producenta'})

                        # Aktualizuj tylko warianty z tym samym color_id (tym samym kolorem produktu)
                        cursor.execute("""
                            UPDATE product_variants 
                            SET producer_color_id = %s, updated_at = NOW() 
                            WHERE product_id = %s AND color_id = %s
                        """, [producer_color_id, product.mapped_product_uid, color_id])

                        updated_count = cursor.rowcount

                    return JsonResponse({'success': True, 'message': f'Zaktualizowano kolor producenta dla {updated_count} wariantów.'})

                return JsonResponse({'success': False, 'error': 'Brak danych do aktualizacji'})

            except Exception as e:
                logger.error("Błąd podczas aktualizacji produktu MPD: %s", e)
                return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})

    def assign_mapping(self, request, product_id, mpd_product_id):
        """Przypisuje istniejący produkt MPD do produktu matterhorn1"""
        if request.method == 'POST':
            try:
                # Zaktualizuj mapped_product_id
                with connections['default'].cursor() as cursor:
                    cursor.execute(
                        "UPDATE product SET mapped_product_uid = %s WHERE id = %s",
                        [mpd_product_id, product_id]
                    )

                return JsonResponse({
                    'success': True,
                    'message': f'Przypisano produkt MPD (ID: {mpd_product_id})'
                })

            except Exception as e:
                logger.error("Błąd podczas przypisywania mapowania: %s", e)
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

                # Przygotuj dane do aktualizacji
                update_data = {field_name: value}

                # Wyślij żądanie do API MPD
                mpd_api_url = f"{settings.MPD_API_URL}/products/{product.mapped_product_uid}/update/"
                response = requests.patch(
                    mpd_api_url, json=update_data, timeout=30)

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

    # ===== ZAAWANSOWANE FUNKCJONALNOŚCI =====

    def bulk_map_to_mpd_action(self, request, queryset):
        """Akcja masowa - mapuj wybrane produkty do istniejących w MPD"""
        if request.POST.get('post'):
            # Pobierz sugerowane mapowania
            mappings = []
            for product in queryset.filter(is_mapped=False):
                suggestions = self._get_suggested_mappings(product)
                mappings.append({
                    'product': product,
                    'suggestions': suggestions
                })

            # Przygotuj dane dla React
            mappings_data = []
            for mapping in mappings:
                mappings_data.append({
                    'product': {
                        'id': mapping['product'].id,
                        'product_id': mapping['product'].product_id,
                        'name': mapping['product'].name,
                        'brand': {
                            'name': mapping['product'].brand.name if mapping['product'].brand else None
                        },
                        'category': {
                            'name': mapping['product'].category.name if mapping['product'].category else None
                        }
                    },
                    'suggestions': mapping['suggestions']
                })

            return render(request, 'admin/matterhorn1/product/bulk_map_confirm.html', {
                'mappings': json.dumps(mappings_data),
                'queryset': queryset,
                'action_name': 'bulk_map_to_mpd_action'
            })
        else:
            return render(request, 'admin/matterhorn1/product/bulk_map_confirm.html', {
                'mappings': [],
                'queryset': queryset,
                'action_name': 'bulk_map_to_mpd_action'
            })
    bulk_map_to_mpd_action.short_description = "Mapuj do istniejących produktów MPD"

    def bulk_create_mpd_action(self, request, queryset):
        """Akcja masowa - utwórz nowe produkty w MPD"""
        if request.POST.get('post'):
            # Pobierz dane do tworzenia
            products_data = []
            for product in queryset.filter(is_mapped=False):
                products_data.append({
                    'matterhorn_product_id': product.product_uid,
                    'name': product.name,
                    'description': product.description,
                    'brand_name': product.brand.name if product.brand else '',
                    'variants': self._prepare_variants_data(product)
                })

            return render(request, 'admin/matterhorn1/product/bulk_create_confirm.html', {
                'products_data': json.dumps(products_data),
                'queryset': queryset,
                'action_name': 'bulk_create_mpd_action'
            })
        else:
            return render(request, 'admin/matterhorn1/product/bulk_create_confirm.html', {
                'products_data': [],
                'queryset': queryset,
                'action_name': 'bulk_create_mpd_action'
            })
    bulk_create_mpd_action.short_description = "Utwórz nowe produkty w MPD"

    def sync_with_mpd_action(self, request, queryset):
        """Akcja masowa - synchronizuj z MPD"""
        synced_count = 0
        for product in queryset.filter(is_mapped=True):
            if self._sync_product_with_mpd(product):
                synced_count += 1

        self.message_user(
            request, f"Zsynchronizowano {synced_count} produktów z MPD.")
    sync_with_mpd_action.short_description = "Synchronizuj z MPD"

    def bulk_map_to_mpd(self, request):
        """Endpoint do masowego mapowania produktów"""
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                mappings = data.get('mappings', [])

                success_count = 0
                errors = []

                with transaction.atomic():
                    for mapping in mappings:
                        try:
                            product_id = mapping.get('product_id')
                            mpd_product_id = mapping.get('mpd_product_id')

                            if not product_id or not mpd_product_id:
                                continue

                            # Zaktualizuj mapowanie
                            product = Product.objects.get(id=product_id)
                            product.mapped_product_uid = mpd_product_id
                            product.is_mapped = True
                            product.save()

                            # Automatycznie zmapuj warianty
                            self._auto_map_variants(product, mpd_product_id)

                            success_count += 1

                        except Exception as e:
                            errors.append(
                                f"Błąd mapowania produktu {product_id}: {str(e)}")

                return JsonResponse({
                    'success': True,
                    'message': f'Zamapowano {success_count} produktów',
                    'errors': errors
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})

    def bulk_create_mpd(self, request):
        """Endpoint do masowego tworzenia produktów w MPD"""
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                products_data = data.get('products', [])

                created_products = []
                errors = []

                # Użyj API MPD do bulk create
                mpd_api_url = f"{request.scheme}://{request.get_host()}/mpd/bulk-create/"
                response = requests.post(
                    mpd_api_url, json={'products': products_data}, timeout=60)

                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'success':
                        # Zaktualizuj mapped_product_uid w matterhorn1
                        for created_product in result.get('created_products', []):
                            try:
                                product = Product.objects.get(
                                    product_id=created_product['matterhorn_product_id']
                                )
                                product.mapped_product_uid = created_product['mpd_product_id']
                                product.is_mapped = True
                                product.save()
                                created_products.append(created_product)
                            except Product.DoesNotExist:
                                errors.append(
                                    f"Nie znaleziono produktu {created_product['matterhorn_product_id']}")
                    else:
                        errors.append(result.get('message', 'Błąd API MPD'))
                else:
                    errors.append(f"Błąd API MPD: {response.status_code}")

                return JsonResponse({
                    'success': True,
                    'message': f'Utworzono {len(created_products)} produktów w MPD',
                    'created_products': created_products,
                    'errors': errors
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})

    def upload_images(self, request, product_id):
        """Upload obrazów produktu do bucketa i zapis do MPD"""
        if request.method == 'POST':
            try:
                product = Product.objects.get(id=product_id)
                if not product.is_mapped:
                    return JsonResponse({
                        'success': False,
                        'error': 'Produkt musi być zmapowany do MPD'
                    })

                uploaded_images = []
                for i, image in enumerate(product.images.all().order_by('order'), 1):
                    if image.image_url:
                        # Upload do bucketa
                        bucket_url = self._upload_image_to_bucket(
                            image_url=image.image_url,
                            product_id=product.mapped_product_uid,
                            color_name=product.color,
                            image_number=i
                        )
                        if bucket_url:
                            # Zapisz do MPD
                            self._save_image_to_mpd(
                                product.mapped_product_uid, bucket_url)
                            uploaded_images.append({
                                'original_url': image.image_url,
                                'uploaded_url': bucket_url,
                                'order': image.order
                            })

                return JsonResponse({
                    'success': True,
                    'message': f'Uploadowano {len(uploaded_images)} obrazów',
                    'images': uploaded_images
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})

    def auto_map_variants(self, request, product_id):
        """Automatyczne mapowanie wariantów produktu"""
        if request.method == 'POST':
            try:
                product = Product.objects.get(id=product_id)
                if not product.is_mapped:
                    return JsonResponse({
                        'success': False,
                        'error': 'Produkt musi być zmapowany do MPD'
                    })

                mapped_variants = self._auto_map_variants(
                    product, product.mapped_product_uid)

                return JsonResponse({
                    'success': True,
                    'message': f'Zamapowano {len(mapped_variants)} wariantów',
                    'variants': mapped_variants
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})

    def sync_with_mpd(self, request, product_id):
        """Synchronizacja produktu z MPD"""
        if request.method == 'POST':
            try:
                product = Product.objects.get(id=product_id)
                if not product.is_mapped:
                    return JsonResponse({
                        'success': False,
                        'error': 'Produkt musi być zmapowany do MPD'
                    })

                # Pobierz aktualne dane z MPD
                mpd_data = self._get_mpd_product_data(
                    product.mapped_product_uid)
                if mpd_data:
                    # Zaktualizuj dane w matterhorn1
                    product.name = mpd_data.get('name', product.name)
                    product.description = mpd_data.get(
                        'description', product.description)
                    product.save()

                    return JsonResponse({
                        'success': True,
                        'message': 'Zsynchronizowano z MPD'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Nie można pobrać danych z MPD'
                    })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })

        return JsonResponse({'success': False, 'error': 'Nieprawidłowa metoda'})

    # ===== METODY POMOCNICZE =====

    def _get_suggested_mappings(self, product):
        """Pobierz sugerowane mapowania produktu"""
        suggestions = []

        with connections['MPD'].cursor() as cursor:
            # Wyszukaj podobne produkty w MPD
            cursor.execute("""
                SELECT p.id, p.name, b.name as brand_name
                FROM products p 
                LEFT JOIN brands b ON p.brand = b.id 
                WHERE LOWER(p.name) LIKE LOWER(%s)
                ORDER BY p.name
                LIMIT 5
            """, [f'%{product.name[:20]}%'])

            for row in cursor.fetchall():
                similarity = fuzz.ratio(product.name.lower(), row[1].lower())
                suggestions.append({
                    'id': row[0],
                    'name': row[1],
                    'brand': row[2] or '',
                    'similarity': similarity
                })

        return sorted(suggestions, key=lambda x: x['similarity'], reverse=True)

    def _prepare_variants_data(self, product):
        """Przygotuj dane wariantów do mapowania"""
        variants = []
        for variant in product.variants.all():
            variants.append({
                'size_name': variant.name,
                'stock': variant.stock,
                'ean': variant.ean,
                'producer_code': f"{product.product_uid}_{variant.name}"
            })
        return variants

    def _auto_map_variants(self, product, mpd_product_id):
        """Automatyczne mapowanie wariantów"""
        mapped_variants = []

        with connections['MPD'].cursor() as cursor:
            for variant in product.variants.all():
                # Znajdź lub utwórz rozmiar
                size_id = self._get_or_create_size(variant.name)

                # Znajdź lub utwórz kolor
                color_id = self._get_or_create_color(
                    product.color or 'Brak koloru')

                # Utwórz wariant w MPD
                cursor.execute("""
                    INSERT INTO product_variants (product_id, size_id, color_id, producer_code)
                    VALUES (%s, %s, %s, %s)
                    RETURNING variant_id
                """, [mpd_product_id, size_id, color_id, f"{product.product_uid}_{variant.name}"])

                variant_id = cursor.fetchone()[0]
                mapped_variants.append(variant_id)

        return mapped_variants

    def _get_or_create_size(self, size_name):
        """Pobierz lub utwórz rozmiar w MPD"""
        with connections['MPD'].cursor() as cursor:
            cursor.execute("SELECT id FROM sizes WHERE name = %s", [size_name])
            result = cursor.fetchone()

            if result:
                return result[0]
            else:
                cursor.execute("""
                    INSERT INTO sizes (name, category, name_lower)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, [size_name, 'default', size_name.lower()])
                return cursor.fetchone()[0]

    def _get_or_create_color(self, color_name):
        """Pobierz lub utwórz kolor w MPD"""
        with connections['MPD'].cursor() as cursor:
            cursor.execute(
                "SELECT id FROM colors WHERE name = %s", [color_name])
            result = cursor.fetchone()

            if result:
                return result[0]
            else:
                cursor.execute("""
                    INSERT INTO colors (name)
                    VALUES (%s)
                    RETURNING id
                """, [color_name])
                return cursor.fetchone()[0]

    def _upload_image_to_bucket(self, image_url, product_id, color_name=None, image_number=1):
        """Upload obrazu do bucketa"""
        from .defs_db import upload_image_to_bucket_and_get_url
        return upload_image_to_bucket_and_get_url(
            image_url=image_url,
            product_id=product_id,
            color_name=color_name,
            image_number=image_number
        )

    def _save_image_to_mpd(self, mpd_product_id, image_url):
        """Zapisz obraz do MPD"""
        with connections['MPD'].cursor() as cursor:
            cursor.execute("""
                INSERT INTO product_images (product_id, file_path)
                VALUES (%s, %s)
            """, [mpd_product_id, image_url])

    def _get_mpd_product_data(self, mpd_product_id):
        """Pobierz dane produktu z MPD"""
        with connections['MPD'].cursor() as cursor:
            cursor.execute("""
                SELECT p.name, p.description, p.short_description
                FROM products p 
                WHERE p.id = %s
            """, [mpd_product_id])

            result = cursor.fetchone()
            if result:
                return {
                    'name': result[0],
                    'description': result[1],
                    'short_description': result[2]
                }
        return None

    def _sync_product_with_mpd(self, product):
        """Synchronizuj pojedynczy produkt z MPD"""
        try:
            mpd_data = self._get_mpd_product_data(product.mapped_product_uid)
            if mpd_data:
                product.name = mpd_data.get('name', product.name)
                product.description = mpd_data.get(
                    'description', product.description)
                product.save()
                return True
        except Exception as e:
            logger.error(f"Błąd synchronizacji produktu {product.id}: {e}")
        return False

    def add_new_variants_to_mpd(self, product_id, mapped_product_id, size_category, producer_color_id=None, producer_code=None):
        """Dodaje nowe warianty do MPD z filtrowaniem według kategorii rozmiarów"""
        variant_logger = logging.getLogger('matterhorn1.variants')

        # Użyj nowego systemu logowania transakcji
        with logged_transaction("add_new_variants_to_mpd", "matterhorn1.variants") as tx_logger:
            tx_logger.log_cross_database_operation(
                "matterhorn1", "MPD",
                "add_variants",
                {
                    'product_id': product_id,
                    'mapped_product_id': mapped_product_id,
                    'size_category': size_category,
                    'producer_color_id': producer_color_id,
                    'producer_code': producer_code
                }
            )

            variant_logger.info(
                "[add_new_variants_to_mpd] START: product_id=%s, mapped_product_id=%s, size_category=%s, producer_color_id=%s, producer_code=%s",
                product_id, mapped_product_id, size_category, producer_color_id, producer_code)

            missing_sizes = []
            missing_colors = False
            added_variants = 0
            skipped_existing = 0
            total_variants = 0

            try:
                with connections['matterhorn1'].cursor() as matterhorn_cursor, connections['MPD'].cursor() as mpd_cursor:
                    # Pobierz kolor i cenę produktu z matterhorn1
                    tx_logger.log_operation("SELECT", "matterhorn1", "product", "get_product_color_price", {
                                            "product_id": product_id})
                    matterhorn_cursor.execute("""
                        SELECT color, prices FROM product WHERE id = %s
                    """, [product_id])
                    color_result = matterhorn_cursor.fetchone()
                if not color_result:
                    variant_logger.error(
                        f"[add_new_variants_to_mpd] Brak koloru dla produktu {product_id}")
                    return {'added': 0, 'skipped_existing': 0, 'missing_sizes': [], 'missing_color': True, 'total': 0}

                product_color, product_prices = color_result
                variant_logger.info(
                    f"[add_new_variants_to_mpd] Raw color_result: {color_result}")
                variant_logger.info(
                    f"[add_new_variants_to_mpd] product_prices typ: {type(product_prices)}, wartość: {product_prices}")

                # Wyciągnij cenę PLN z JSON
                if isinstance(product_prices, str):
                    try:
                        import json
                        product_prices = json.loads(product_prices)
                    except (json.JSONDecodeError, ValueError):
                        product_prices = {}

                product_price = product_prices.get(
                    'PLN', 0) if isinstance(product_prices, dict) else 0
                variant_logger.info(
                    f"[add_new_variants_to_mpd] product_price przed konwersją: {product_price}, typ: {type(product_price)}")

                # Konwertuj na float jeśli to string
                if isinstance(product_price, str):
                    try:
                        product_price = float(product_price)
                    except ValueError:
                        product_price = 0

                variant_logger.info(
                    f"[add_new_variants_to_mpd] Kolor produktu: {product_color}, cena PLN: {product_price}")
                variant_logger.info(
                    f"[add_new_variants_to_mpd] Pełne dane prices: {product_prices}, typ: {type(product_prices)}")
                variant_logger.info(
                    f"[add_new_variants_to_mpd] product_price po konwersji: {product_price}, typ: {type(product_price)}")

                # Sprawdź czy cena jest większa od 0 (tymczasowo włączone dla debugowania)
                if product_price <= 0:
                    variant_logger.warning(
                        f"[add_new_variants_to_mpd] Produkt {product_id} ma cenę {product_price} - pomijam dodawanie wariantów")
                    return {'added': 0, 'skipped_existing': 0, 'missing_sizes': [], 'missing_color': False, 'total': 0, 'error': 'Cena produktu wynosi 0'}

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

                # Generuj nowy iai_product_id dla tego koloru produktu
                mpd_cursor.execute("""
                    INSERT INTO iai_product_counter (counter_value) 
                    VALUES (1) 
                    ON CONFLICT (id) 
                    DO UPDATE SET counter_value = iai_product_counter.counter_value + 1 
                    RETURNING counter_value
                """)
                iai_product_id_result = mpd_cursor.fetchone()
                iai_product_id = iai_product_id_result[0] if iai_product_id_result else 1
                variant_logger.info(
                    f"[add_new_variants_to_mpd] Wygenerowano nowy iai_product_id: {iai_product_id} dla koloru {product_color}")

                # Pobierz warianty produktu z matterhorn1
                matterhorn_cursor.execute("""
                    SELECT name, stock, ean, variant_uid FROM productvariant WHERE product_id = %s
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
                        SELECT variant_id FROM product_variants_sources WHERE variant_uid = %s AND source_id = %s
                    """, [variant_uid, 2])
                    variant_result = mpd_cursor.fetchone()
                    if variant_result:
                        variant_logger.info(
                            f"[add_new_variants_to_mpd] Wariant {variant_uid} już istnieje w MPD - pomijam")
                        skipped_existing += 1
                        continue

                    # Dodaj nowy wariant
                    mpd_cursor.execute(
                        "SELECT COALESCE(MAX(variant_id), 0) + 1 FROM product_variants")
                    row = mpd_cursor.fetchone()
                    variant_id = row[0] if row else 1

                    variant_logger.info(
                        f"[add_new_variants_to_mpd] Dodaję nowy wariant {variant_uid} jako variant_id {variant_id} (product_id={mapped_product_id}, color_id={color_id}, size_id={size_id}, ean={ean}, producer_color_id={producer_color_id}, producer_code={producer_code})")

                    try:
                        if producer_color_id:
                            mpd_cursor.execute("""
                                INSERT INTO product_variants (variant_id, product_id, color_id, producer_color_id, size_id, producer_code, iai_product_id, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                            """, [variant_id, mapped_product_id, color_id, producer_color_id, size_id, producer_code, iai_product_id])
                        else:
                            mpd_cursor.execute("""
                                INSERT INTO product_variants (variant_id, product_id, color_id, size_id, producer_code, iai_product_id, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """, [variant_id, mapped_product_id, color_id, size_id, producer_code, iai_product_id])

                        # Dodaj wpis do product_variants_sources
                        mpd_cursor.execute("""
                            INSERT INTO product_variants_sources (variant_id, ean, variant_uid, source_id)
                            VALUES (%s, %s, %s, %s)
                        """, [variant_id, ean, variant_uid, 2])
                        variant_logger.info(
                            f"[add_new_variants_to_mpd] Dodano wariant {variant_uid} do product_variants i product_variants_sources")
                    except Exception as e:
                        variant_logger.error(
                            f"[add_new_variants_to_mpd] Błąd podczas dodawania wariantu {variant_uid} do product_variants: {e}")
                        continue

                    # Aktualizuj mapped_variant_id w matterhorn1 (przed stock_and_prices)
                    try:
                        matterhorn_cursor.execute("""
                            UPDATE productvariant SET mapped_variant_id = %s, is_mapped = true, updated_at = NOW() WHERE variant_uid = %s
                        """, [variant_id, variant_uid])
                        variant_logger.info(
                            f"[add_new_variants_to_mpd] Zaktualizowano mapped_variant_id w matterhorn1 dla wariantu {variant_uid}")
                    except Exception as e:
                        variant_logger.error(
                            f"[add_new_variants_to_mpd] Błąd podczas aktualizacji mapped_variant_id w matterhorn1 dla wariantu {variant_uid}: {e}")
                        continue

                    try:
                        # Sprawdź czy rekord już istnieje
                        mpd_cursor.execute("""
                            SELECT variant_id FROM stock_and_prices 
                            WHERE variant_id = %s AND source_id = %s
                        """, [variant_id, 2])
                        existing_record = mpd_cursor.fetchone()

                        variant_logger.info(
                            f"[add_new_variants_to_mpd] Dodawanie do stock_and_prices: variant_id={variant_id}, stock={stock}, price={product_price}")
                        variant_logger.info(
                            f"[add_new_variants_to_mpd] product_price w momencie zapisywania: {product_price}, typ: {type(product_price)}")

                        if existing_record:
                            # Aktualizuj istniejący rekord
                            mpd_cursor.execute("""
                                UPDATE stock_and_prices 
                                SET stock = %s, price = %s, currency = 'PLN'
                                WHERE variant_id = %s AND source_id = %s
                            """, [stock, product_price, variant_id, 2])
                            variant_logger.info(
                                f"[add_new_variants_to_mpd] Zaktualizowano istniejący rekord w stock_and_prices")
                        else:
                            # Dodaj nowy rekord
                            mpd_cursor.execute("""
                                INSERT INTO stock_and_prices 
                                (variant_id, source_id, stock, price, currency)
                                VALUES (%s, %s, %s, %s, 'PLN')
                            """, [variant_id, 2, stock, product_price])
                            variant_logger.info(
                                f"[add_new_variants_to_mpd] Dodano nowy rekord do stock_and_prices")
                    except Exception as e:
                        variant_logger.error(
                            f"[add_new_variants_to_mpd] Błąd podczas dodawania/uzupełniania stock_and_prices dla wariantu {variant_uid}: {e}")
                        # Nie continue tutaj - mapped_variant_id już zostało zaktualizowane

                    added_variants += 1
                    variant_logger.info(
                        f"[add_new_variants_to_mpd] Pomyślnie dodano wariant {variant_uid}")

                # Transakcje zostaną automatycznie zatwierdzone przez Django ORM
                variant_logger.info(
                    "[add_new_variants_to_mpd] Wszystkie operacje zakończone pomyślnie")

            except Exception as e:
                variant_logger.error(
                    f"[add_new_variants_to_mpd] Błąd ogólny: {e}")
                connections['MPD'].rollback()
                connections['matterhorn1'].rollback()
                return {'added': 0, 'skipped_existing': 0, 'missing_sizes': [], 'missing_color': True, 'total': 0}

            return {'added': added_variants, 'skipped_existing': skipped_existing, 'missing_sizes': missing_sizes, 'missing_color': missing_colors, 'total': total_variants, 'iai_product_id': None}

    def add_variants(self, request, product_id):
        """Dodaje warianty do istniejącego produktu w MPD"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Tylko metoda POST jest obsługiwana'})

        try:
            size_category = request.POST.get('size_category')
            producer_color_id = request.POST.get('producer_color_id')
            producer_code = request.POST.get('producer_code')

            if not size_category:
                return JsonResponse({'success': False, 'error': 'Wybierz grupę rozmiarową'})

            # Pobierz produkt
            product = Product.objects.get(id=product_id)
            if not product.is_mapped or not product.mapped_product_uid:
                return JsonResponse({'success': False, 'error': 'Produkt nie jest zmapowany do MPD'})

            logger.info("Dodawanie wariantów dla produktu %s (MPD ID: %s) z kategorią: %s",
                        product_id, product.mapped_product_uid, size_category)

            # Wywołaj add_new_variants_to_mpd
            variant_info = self.add_new_variants_to_mpd(
                product_id, product.mapped_product_uid, size_category,
                producer_color_id, producer_code
            )

            message = f'Dodano {variant_info.get("added", 0)} wariantów'
            if variant_info.get('missing_sizes'):
                message += f'. Brakujące rozmiary: {", ".join(variant_info["missing_sizes"])}'
            if variant_info.get('skipped_existing', 0) > 0:
                message += f'. Pominięto {variant_info["skipped_existing"]} istniejących wariantów'

            return JsonResponse({
                'success': True,
                'message': message,
                'variant_info': variant_info
            })

        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Produkt nie istnieje'})
        except Exception as e:
            logger.error(
                f"Błąd dodawania wariantów dla produktu {product_id}: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


@admin.register(ProductDetails)
class ProductDetailsAdmin(admin.ModelAdmin):
    list_display = ['product', 'weight', 'has_size_table', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['product__name', 'product__product_uid']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Produkt', {
            'fields': ('product',)
        }),
        ('Wymiary i waga', {
            'fields': ('weight',)
        }),
        ('Tabela rozmiarów', {
            'fields': ('size_table', 'size_table_txt', 'size_table_html'),
            'classes': ('collapse',)
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_size_table(self, obj):
        """Sprawdź czy ma tabelę rozmiarów"""
        return bool(obj.size_table or obj.size_table_txt or obj.size_table_html)
    has_size_table.boolean = True
    has_size_table.short_description = 'Ma tabelę rozmiarów'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_url', 'order', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name', 'product__product_uid', 'image_url']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Produkt', {
            'fields': ('product',)
        }),
        ('Obraz', {
            'fields': ('image_url', 'order')
        }),
        ('Metadane', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        'variant_uid', 'product', 'name', 'stock', 'ean',
        'max_processing_time', 'is_mapped', 'mapped_variant_uid', 'created_at'
    ]
    list_filter = ['created_at', 'updated_at',
                   'max_processing_time', 'is_mapped']
    search_fields = [
        'variant_uid', 'name', 'ean', 'product__name', 'product__product_uid'
    ]
    readonly_fields = ['variant_uid',
                       'mapped_variant_uid', 'created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('variant_uid', 'product', 'name')
        }),
        ('Stan magazynowy', {
            'fields': ('stock', 'ean')
        }),
        ('Przetwarzanie', {
            'fields': ('max_processing_time',)
        }),
        ('Mapowanie do MPD', {
            'fields': ('is_mapped', 'mapped_variant_uid'),
            'classes': ('collapse',)
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ApiSyncLog)
class ApiSyncLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'sync_type', 'status', 'started_at', 'completed_at',
        'duration', 'records_created', 'records_updated', 'records_errors'
    ]
    list_filter = ['sync_type', 'status', 'started_at', 'completed_at']
    search_fields = ['sync_type', 'status']
    readonly_fields = [
        'id', 'started_at', 'completed_at', 'duration', 'records_created',
        'records_updated', 'records_errors', 'error_details'
    ]
    ordering = ['-started_at']

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('id', 'sync_type', 'status')
        }),
        ('Czas wykonania', {
            'fields': ('started_at', 'completed_at', 'duration', 'duration_seconds')
        }),
        ('Statystyki', {
            'fields': ('records_processed', 'records_created', 'records_updated', 'records_errors')
        }),
        ('Błędy', {
            'fields': ('error_details',),
            'classes': ('collapse',)
        }),
    )

    def duration(self, obj):
        """Oblicz czas trwania synchronizacji"""
        if obj.started_at and obj.completed_at:
            delta = obj.completed_at - obj.started_at
            total_seconds = int(delta.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "-"
    duration.short_description = 'Czas trwania'

    def has_add_permission(self, request):
        """Wyłącz dodawanie nowych logów przez admin"""
        return False

    def has_change_permission(self, request, obj=None):
        """Wyłącz edycję logów przez admin"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Zezwól na usuwanie starych logów"""
        return True


# Konfiguracja admin site
admin.site.site_header = "Matterhorn1 Administration"
admin.site.site_title = "Matterhorn1 Admin"
admin.site.index_title = "Zarządzanie danymi Matterhorn1"

# Dodatkowe filtry i akcje


class ProductStatusFilter(admin.SimpleListFilter):
    title = 'Status produktu'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Aktywne'),
            ('inactive', 'Nieaktywne'),
            ('no_stock', 'Brak stanu'),
            ('with_stock', 'Ze stanem'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(active=True)
        elif self.value() == 'inactive':
            return queryset.filter(active=False)
        elif self.value() == 'no_stock':
            return queryset.filter(variants__stock=0).distinct()
        elif self.value() == 'with_stock':
            return queryset.filter(variants__stock__gt=0).distinct()


# Dodaj filtr do ProductAdmin
ProductAdmin.list_filter.append(ProductStatusFilter)

# Akcje masowe


@admin.action(description='Oznacz jako aktywne')
def make_active(modeladmin, request, queryset):
    queryset.update(active=True)
    modeladmin.message_user(
        request, f"Oznaczono {queryset.count()} produktów jako aktywne.")


@admin.action(description='Oznacz jako nieaktywne')
def make_inactive(modeladmin, request, queryset):
    queryset.update(active=False)
    modeladmin.message_user(
        request, f"Oznaczono {queryset.count()} produktów jako nieaktywne.")


ProductAdmin.actions = (make_active, make_inactive)


# Saga Pattern Admin Interface
@admin.register(Saga)
class SagaAdmin(admin.ModelAdmin):
    """Admin interface dla Saga operations"""

    list_display = [
        'saga_id', 'saga_type', 'status', 'created_at',
        'completed_at', 'total_steps', 'completed_steps'
    ]
    list_filter = ['status', 'saga_type', 'created_at']
    search_fields = ['saga_id', 'saga_type', 'error_message']
    readonly_fields = [
        'saga_id', 'created_at', 'started_at', 'completed_at',
        'total_steps', 'completed_steps', 'failed_step'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('saga_id', 'saga_type', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
        ('Statistics', {
            'fields': ('total_steps', 'completed_steps', 'failed_step')
        }),
        ('Data', {
            'fields': ('input_data', 'output_data'),
            'classes': ('collapse',)
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Użyj bazy matterhorn1"""
        return super().get_queryset(request).using('matterhorn1')


@admin.register(SagaStep)
class SagaStepAdmin(admin.ModelAdmin):
    """Admin interface dla Saga steps"""

    list_display = [
        'saga', 'step_order', 'step_name', 'status',
        'started_at', 'completed_at', 'compensation_attempted'
    ]
    list_filter = ['status', 'compensation_attempted',
                   'compensation_successful']
    search_fields = ['step_name', 'error_message']
    readonly_fields = [
        'saga', 'step_order', 'step_name', 'started_at',
        'completed_at', 'compensated_at', 'compensation_attempted',
        'compensation_successful'
    ]
    ordering = ['saga', 'step_order']

    fieldsets = (
        ('Step Info', {
            'fields': ('saga', 'step_order', 'step_name', 'status')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at', 'compensated_at')
        }),
        ('Compensation', {
            'fields': ('compensation_attempted', 'compensation_successful')
        }),
        ('Data', {
            'fields': ('input_data', 'output_data'),
            'classes': ('collapse',)
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Użyj bazy matterhorn1"""
        return super().get_queryset(request).using('matterhorn1')

    def has_add_permission(self, request):
        """Nie pozwalaj na ręczne dodawanie kroków"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Nie pozwalaj na usuwanie kroków"""
        return False


@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    """Admin interface dla historii stanów magazynowych"""

    list_display = [
        'id', 'product_uid_link', 'product_name', 'variant_uid', 'variant_name',
        'old_stock', 'new_stock', 'stock_change', 'change_type', 'timestamp'
    ]
    list_display_links = ['product_uid_link']

    def product_uid_link(self, obj):
        """Renderuje product_uid jako link do produktu"""
        if obj.product_uid:
            product_url = obj.get_product_url()
            if product_url:
                return format_html(
                    '<a href="{}" target="_blank">{}</a>',
                    product_url,
                    obj.product_uid
                )
        return obj.product_uid
    product_uid_link.short_description = 'Product UID'
    product_uid_link.admin_order_field = 'product_uid'
    list_filter = ['change_type', 'timestamp', 'product_uid']
    search_fields = [
        'product_uid', 'product_name', 'variant_uid', 'variant_name'
    ]
    readonly_fields = [
        'id', 'variant_uid', 'product_uid', 'product_name', 'variant_name',
        'old_stock', 'new_stock', 'stock_change', 'change_type', 'timestamp'
    ]
    ordering = ['-timestamp']
    list_per_page = 50

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('id', 'product_uid', 'product_name', 'variant_uid', 'variant_name')
        }),
        ('Zmiany stanu', {
            'fields': ('old_stock', 'new_stock', 'stock_change', 'change_type')
        }),
        ('Metadane', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Użyj bazy matterhorn1"""
        return super().get_queryset(request).using('matterhorn1')

    def has_add_permission(self, request):
        """Wyłącz dodawanie nowych rekordów przez admin"""
        return False

    def has_change_permission(self, request, obj=None):
        """Wyłącz edycję rekordów przez admin"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Zezwól na usuwanie starych rekordów"""
        return True

    def get_urls(self):
        """Dodaj custom URLs dla stock history"""
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
        """Widok popularnych produktów"""
        from django.shortcuts import render
        days = int(request.GET.get('days', 30))
        popular_products = self._get_popular_products(days=days, limit=50)

        context = {
            'popular_products': popular_products,
            'days': days,
            'title': f'Najbardziej popularne produkty (ostatnie {days} dni)'
        }
        return render(request, 'admin/matterhorn1/stock_history/popular_products.html', context)

    def stock_statistics_view(self, request):
        """Widok statystyk stanów magazynowych"""
        from django.shortcuts import render
        days = int(request.GET.get('days', 30))
        stats = self._get_stock_statistics(days=days)

        context = {
            'stats': stats,
            'days': days,
            'title': f'Statystyki stanów magazynowych (ostatnie {days} dni)'
        }
        return render(request, 'admin/matterhorn1/stock_history/statistics.html', context)

    def clean_history_view(self, request):
        """Widok czyszczenia historii"""
        from django.shortcuts import redirect
        from django.contrib import messages

        if request.method == 'POST':
            days_to_keep = int(request.POST.get('days_to_keep', 90))
            result = self._clean_old_stock_history(days_to_keep)
            messages.success(request, result)

        return redirect('admin:matterhorn1_stockhistory_changelist')

    def changelist_view(self, request, extra_context=None):
        """Dodaj akcje do changelist"""
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

    def _get_popular_products(self, days=30, limit=20):
        """Pobierz popularne produkty na podstawie spadków stanów"""
        from django.db import connections
        from django.utils import timezone
        from datetime import timedelta

        try:
            with connections['matterhorn1'].cursor() as cursor:
                cutoff_date = timezone.now() - timedelta(days=days)

                query = """
                    SELECT 
                        sh.product_uid,
                        sh.product_name,
                        COUNT(*) as total_decreases,
                        SUM(ABS(sh.stock_change)) as total_stock_sold,
                        AVG(ABS(sh.stock_change)) as avg_stock_sold_per_change,
                        MAX(sh.timestamp) as last_activity
                    FROM stock_history sh
                    WHERE sh.change_type = 'decrease'
                        AND sh.timestamp >= %s
                    GROUP BY sh.product_uid, sh.product_name
                    ORDER BY total_stock_sold DESC, total_decreases DESC
                    LIMIT %s
                """

                cursor.execute(query, [cutoff_date, limit])
                results = cursor.fetchall()

                popular_products = []
                for row in results:
                    popular_products.append({
                        'product_uid': row[0],
                        'product_name': row[1],
                        'total_decreases': row[2],
                        'total_stock_sold': row[3],
                        'avg_stock_sold_per_change': float(row[4]) if row[4] else 0,
                        'last_activity': row[5]
                    })

                return popular_products

        except Exception as e:
            logger.error(f"Błąd podczas pobierania popularnych produktów: {e}")
            return []

    def _get_stock_statistics(self, days=30):
        """Pobierz statystyki stanów magazynowych"""
        from django.db import connections
        from django.utils import timezone
        from datetime import timedelta

        try:
            with connections['matterhorn1'].cursor() as cursor:
                cutoff_date = timezone.now() - timedelta(days=days)

                query = """
                    SELECT 
                        COUNT(*) as total_changes,
                        COUNT(CASE WHEN change_type = 'increase' THEN 1 END) as increases,
                        COUNT(CASE WHEN change_type = 'decrease' THEN 1 END) as decreases,
                        COUNT(CASE WHEN change_type = 'no_change' THEN 1 END) as no_changes,
                        SUM(CASE WHEN change_type = 'decrease' THEN ABS(stock_change) ELSE 0 END) as total_sold,
                        SUM(CASE WHEN change_type = 'increase' THEN stock_change ELSE 0 END) as total_added,
                        AVG(CASE WHEN change_type = 'decrease' THEN ABS(stock_change) ELSE NULL END) as avg_sold_per_decrease,
                        COUNT(DISTINCT product_uid) as unique_products,
                        COUNT(DISTINCT variant_uid) as unique_variants
                    FROM stock_history
                    WHERE timestamp >= %s
                """

                cursor.execute(query, [cutoff_date])
                result = cursor.fetchone()

                if result:
                    stats = {
                        'total_changes': result[0],
                        'increases': result[1],
                        'decreases': result[2],
                        'no_changes': result[3],
                        'total_sold': result[4] or 0,
                        'total_added': result[5] or 0,
                        'avg_sold_per_decrease': float(result[6]) if result[6] else 0,
                        'unique_products': result[7],
                        'unique_variants': result[8]
                    }
                else:
                    stats = {}

                return stats

        except Exception as e:
            logger.error(
                f"Błąd podczas pobierania statystyk stanów magazynowych: {e}")
            return {}

    def _clean_old_stock_history(self, days_to_keep=90):
        """Usuń stare rekordy z historii stanów magazynowych"""
        from django.db import connections
        from django.utils import timezone
        from datetime import timedelta

        try:
            with connections['matterhorn1'].cursor() as cursor:
                cutoff_date = timezone.now() - timedelta(days=days_to_keep)

                delete_query = """
                    DELETE FROM stock_history
                    WHERE timestamp < %s
                """

                cursor.execute(delete_query, [cutoff_date])
                deleted_count = cursor.rowcount

                logger.info(
                    f"Usunięto {deleted_count} starych rekordów z historii stanów magazynowych")
                return f"Usunięto {deleted_count} starych rekordów z historii stanów magazynowych"

        except Exception as e:
            logger.error(
                f"Błąd podczas czyszczenia historii stanów magazynowych: {e}")
            return f"Błąd podczas czyszczenia historii: {e}"
