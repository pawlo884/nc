from django.contrib import admin
from django.http import JsonResponse
from django.db import connections
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging
from .models import (
    Brand, Category, Product, ProductDetails, ProductImage,
    ProductVariant, ApiSyncLog
)

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
    fields = ['variant_uid', 'name', 'stock', 'ean', 'max_processing_time']
    readonly_fields = ['variant_uid']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'product_id', 'name', 'brand', 'category', 'active',
        'stock_total', 'created_at', 'updated_at'
    ]
    list_filter = [
        'brand', 'category', 'active', 'created_at', 'updated_at'
    ]
    search_fields = [
        'product_id', 'name', 'description', 'brand__name', 'category__name'
    ]
    readonly_fields = [
        'product_id', 'mapped_product_id', 'created_at', 'updated_at', 'stock_total'
    ]
    ordering = ['-created_at']
    inlines = [ProductDetailsInline, ProductImageInline, ProductVariantInline]

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': (
                'product_id', 'name', 'description', 'brand', 'category'
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
            'fields': ('mapped_product_id',),
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
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Dodaj dane MPD do kontekstu"""
        extra_context = extra_context or {}

        try:
            product = Product.objects.get(id=object_id)
            is_mapped = bool(product.mapped_product_id)

            # Pobierz dane MPD jeśli produkt jest zmapowany
            mpd_data = {}
            suggested_products = []
            main_colors = []
            producer_colors = []
            mpd_paths = []
            selected_paths = []
            units = []

            if is_mapped:
                # Pobierz dane produktu z MPD
                with connections['MPD'].cursor() as cursor:
                    cursor.execute("""
                        SELECT p.name, p.description, p.short_description, b.name as brand_name
                        FROM products p 
                        LEFT JOIN brands b ON p.brand = b.id 
                        WHERE p.id = %s
                    """, [product.mapped_product_id])
                    result = cursor.fetchone()
                    if result:
                        mpd_data = {
                            'name': result[0] or '',
                            'description': result[1] or '',
                            'short_description': result[2] or '',
                            'brand': result[3] or ''
                        }

                    # Pobierz kolory
                    cursor.execute("SELECT id, name FROM colors ORDER BY name")
                    main_colors = [{'id': row[0], 'name': row[1]}
                                   for row in cursor.fetchall()]

                    # Pobierz ścieżki
                    cursor.execute(
                        "SELECT id, name, path FROM path ORDER BY name")
                    mpd_paths = [{'id': row[0], 'name': row[1],
                                  'path': row[2]} for row in cursor.fetchall()]

                    # Pobierz przypisane ścieżki
                    cursor.execute("SELECT path_id FROM product_path WHERE product_id = %s", [
                                   product.mapped_product_id])
                    selected_paths = [row[0] for row in cursor.fetchall()]

                    # Pobierz jednostki
                    cursor.execute("SELECT id, name FROM units ORDER BY name")
                    units = [{'id': row[0], 'name': row[1]}
                             for row in cursor.fetchall()]
            else:
                # Pobierz sugerowane produkty
                with connections['MPD'].cursor() as cursor:
                    cursor.execute("""
                        SELECT p.id, p.name, b.name as brand_name
                        FROM products p 
                        LEFT JOIN brands b ON p.brand = b.id 
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
                'producer_color_name': '',
                'producer_code': '',
                'series_name': '',
                'selected_unit_id': None
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
                'producer_color_name': '',
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
                brand = request.POST.get('mpd_brand')
                main_color_id = request.POST.get('main_color_id')
                producer_code = request.POST.get('producer_code')
                producer_color_name = request.POST.get('producer_color_name')
                unit_id = request.POST.get('unit_id')

                if not name:
                    return JsonResponse({'success': False, 'error': 'Nazwa jest wymagana'})

                # Przygotuj dane do wysłania do API MPD
                mpd_data = {
                    'name': name,
                    'description': description or '',
                    'short_description': short_description or '',
                    'brand_id': brand,
                    'unit_id': unit_id,
                    'visibility': True
                }

                # Dodaj warianty jeśli podano kolor
                if main_color_id or producer_color_name or producer_code:
                    variants = [{
                        'color_id': main_color_id,
                        'producer_color_name': producer_color_name,
                        'producer_code': producer_code
                    }]
                    mpd_data['variants'] = variants

                # Wyślij żądanie do API MPD
                mpd_api_url = f"{settings.MPD_API_URL}/products/create/"
                response = requests.post(
                    mpd_api_url, json=mpd_data, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'success':
                        mpd_product_id = result.get('product_id')

                        # Zaktualizuj mapped_product_id w matterhorn1
                        product = Product.objects.get(id=product_id)
                        product.mapped_product_id = mpd_product_id
                        product.save()

                        return JsonResponse({
                            'success': True,
                            'message': f'Utworzono produkt w MPD (ID: {mpd_product_id})'
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
                if not product.mapped_product_id:
                    return JsonResponse({'success': False, 'error': 'Produkt nie jest zmapowany'})

                # Dodawanie ścieżek
                mpd_paths = request.POST.getlist('mpd_paths')
                if mpd_paths:
                    with connections['MPD'].cursor() as cursor:
                        for path_id in mpd_paths:
                            cursor.execute(
                                "INSERT INTO product_path (product_id, path_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                [product.mapped_product_id, path_id]
                            )
                    return JsonResponse({'success': True, 'message': 'Dodano ścieżki.'})

                # Usuwanie ścieżki
                remove_path_id = request.POST.get('remove_path_id')
                if remove_path_id:
                    with connections['MPD'].cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM product_path WHERE product_id = %s AND path_id = %s",
                            [product.mapped_product_id, remove_path_id]
                        )
                    return JsonResponse({'success': True, 'message': 'Usunięto ścieżkę.'})

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
                        "UPDATE product SET mapped_product_id = %s WHERE id = %s",
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
                if not product.mapped_product_id:
                    return JsonResponse({'success': False, 'error': 'Produkt nie jest zmapowany'})

                # Przygotuj dane do aktualizacji
                update_data = {field_name: value}

                # Wyślij żądanie do API MPD
                mpd_api_url = f"{settings.MPD_API_URL}/products/{product.mapped_product_id}/update/"
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


@admin.register(ProductDetails)
class ProductDetailsAdmin(admin.ModelAdmin):
    list_display = ['product', 'weight', 'has_size_table', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['product__name', 'product__product_id']
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
    search_fields = ['product__name', 'product__product_id', 'image_url']
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
        'max_processing_time', 'created_at'
    ]
    list_filter = ['created_at', 'updated_at', 'max_processing_time']
    search_fields = [
        'variant_uid', 'name', 'ean', 'product__name', 'product__product_id'
    ]
    readonly_fields = ['variant_uid', 'created_at', 'updated_at']
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


ProductAdmin.actions = [make_active, make_inactive]
