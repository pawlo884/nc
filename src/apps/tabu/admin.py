import logging
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.http import JsonResponse
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connections
from django.utils import timezone
from django.utils.html import format_html

from .models import Brand, Category, ApiSyncLog, TabuProduct, TabuProductImage, TabuProductVariant, StockHistory


logger = logging.getLogger(__name__)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand_id', 'last_api_sync', 'created_at']
    list_filter = ['created_at', 'updated_at', 'last_api_sync']
    search_fields = ['name', 'brand_id']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_id', 'parent', 'created_at']
    list_filter = ['created_at', 'updated_at', 'parent']
    search_fields = ['name', 'category_id', 'path']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync']


class TabuBrandFilter(SimpleListFilter):
    title = 'Marka'
    parameter_name = 'brand'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        if request.GET.get('category'):
            try:
                qs = qs.filter(category_id=int(request.GET['category']))
            except (ValueError, TypeError):
                pass
        brands = Brand.objects.filter(
            id__in=qs.exclude(brand__isnull=True).values_list('brand_id', flat=True).distinct()
        ).order_by('name')
        return [(str(b.id), b.name) for b in brands]

    def queryset(self, request, queryset):
        if self.value():
            try:
                return queryset.filter(brand_id=int(self.value()))
            except (ValueError, TypeError):
                return queryset
        return queryset


class TabuCategoryFilter(SimpleListFilter):
    title = 'Kategoria'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        if request.GET.get('brand'):
            try:
                qs = qs.filter(brand_id=int(request.GET['brand']))
            except (ValueError, TypeError):
                pass
        categories = Category.objects.filter(
            id__in=qs.exclude(category__isnull=True).values_list('category_id', flat=True).distinct()
        ).order_by('name')
        return [(str(c.id), c.name) for c in categories]

    def queryset(self, request, queryset):
        if self.value():
            try:
                return queryset.filter(category_id=int(self.value()))
            except (ValueError, TypeError):
                return queryset
        return queryset


class TabuProductImageInline(admin.TabularInline):
    model = TabuProductImage
    extra = 0
    fields = ['api_image_id', 'image_preview', 'image_url', 'is_main', 'order']
    readonly_fields = ['api_image_id', 'image_preview']

    def image_preview(self, obj):
        if obj and obj.image_url:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 80px; max-height: 80px;" /></a>',
                obj.image_url, obj.image_url
            )
        return '-'
    image_preview.short_description = 'Podgląd'


class TabuProductVariantInline(admin.TabularInline):
    model = TabuProductVariant
    extra = 0
    fields = ['api_id', 'symbol', 'color', 'size', 'store', 'price_gross', 'ean']
    readonly_fields = ['api_id']


@admin.register(TabuProduct)
class TabuProductAdmin(admin.ModelAdmin):
    list_display = [
        'api_id', 'name', 'brand', 'category', 'symbol', 'price_gross',
        'store_total', 'is_mapped_mpd', 'last_update'
    ]
    list_display_links = ['api_id', 'name']
    list_filter = [TabuBrandFilter, TabuCategoryFilter, 'last_update']
    search_fields = ['name', 'symbol', 'ean', 'producer_name', 'brand__name', 'category__name']
    readonly_fields = ['api_id', 'last_update', 'image_preview', 'mapped_product_uid']
    ordering = ['-api_id']
    inlines = [TabuProductImageInline, TabuProductVariantInline]
    change_form_template = 'admin/tabu/tabuproduct/change_form.html'

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('api_id', 'name', 'desc_short', 'desc_long', 'desc_safety', 'brand', 'category', 'symbol', 'ean')
        }),
        ('Obraz główny', {
            'fields': ('image_url', 'image_preview'),
            'classes': ('collapse',)
        }),
        ('Ceny i VAT', {
            'fields': ('price_net', 'price_gross', 'price_old', 'vat_label', 'vat_value')
        }),
        ('Stan i dostępność', {
            'fields': ('store_total', 'unit_label', 'status_label', 'status_auto', 'hidden_search')
        }),
        ('Linki i metadane', {
            'fields': ('url', 'version_signature', 'last_update'),
            'classes': ('collapse',)
        }),
        ('Grupy i słowniki', {
            'fields': ('groups', 'dictionaries'),
            'classes': ('collapse',)
        }),
        ('Dane API (backup)', {
            'fields': ('category_path', 'api_category_id', 'producer_name', 'api_producer_id', 'producer_code'),
            'classes': ('collapse',)
        }),
        ('Mapowanie MPD', {
            'fields': ('mapped_product_uid',),
            'classes': ('collapse',)
        }),
    )

    def is_mapped_mpd(self, obj):
        return bool(obj.mapped_product_uid) if obj else False
    is_mapped_mpd.boolean = True
    is_mapped_mpd.short_description = 'MPD'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('mpd-create/<int:product_id>/', self.admin_site.admin_view(self.mpd_create), name='tabu-mpd-create'),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        try:
            product = TabuProduct.objects.select_related('brand').get(pk=object_id)
            is_mapped = bool(product.mapped_product_uid)

            # Pobierz dane MPD (kolory, ścieżki, atrybuty, marki, jednostki, rozmiary, fabric)
            with connections['MPD'].cursor() as cursor:
                cursor.execute("SELECT id, name FROM colors WHERE parent_id IS NULL ORDER BY name")
                main_colors = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

                cursor.execute("SELECT id, name, parent_id FROM colors WHERE parent_id IS NOT NULL ORDER BY name")
                producer_colors = [{'id': row[0], 'name': row[1], 'parent_id': row[2]} for row in cursor.fetchall()]

                cursor.execute("SELECT id, name, path FROM path ORDER BY name")
                mpd_paths = [{'id': row[0], 'name': row[1], 'path': row[2] or ''} for row in cursor.fetchall()]

                cursor.execute("SELECT id, name FROM attributes ORDER BY name")
                mpd_attributes = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

                cursor.execute("SELECT id, name FROM brands ORDER BY name")
                mpd_brands = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

                cursor.execute("SELECT unit_id, name FROM units ORDER BY name")
                units = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT category FROM sizes WHERE category IS NOT NULL ORDER BY category")
                size_categories = [row[0] for row in cursor.fetchall()]

                cursor.execute("SELECT id, name FROM fabric_component ORDER BY name")
                fabric_components = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

            selected_paths = []
            selected_attributes = []
            mpd_data = {}
            producer_color_name = ''
            producer_code = ''
            series_name = ''
            selected_unit_id = None

            if is_mapped:
                with connections['MPD'].cursor() as cursor:
                    cursor.execute(
                        "SELECT p.name, p.description, p.short_description, b.name FROM products p "
                        "LEFT JOIN brands b ON p.brand_id = b.id WHERE p.id = %s",
                        [product.mapped_product_uid]
                    )
                    r = cursor.fetchone()
                    if r:
                        mpd_data = {'name': r[0] or '', 'description': r[1] or '', 'short_description': r[2] or '', 'brand': r[3] or ''}

                    cursor.execute(
                        """SELECT c.name,
                            (SELECT pvs.producer_code FROM product_variants_sources pvs
                             WHERE pvs.variant_id = pv.variant_id AND pvs.producer_code IS NOT NULL AND pvs.producer_code != ''
                             LIMIT 1)
                            FROM product_variants pv
                            LEFT JOIN colors c ON pv.producer_color_id = c.id
                            WHERE pv.product_id = %s LIMIT 1""",
                        [product.mapped_product_uid]
                    )
                    r = cursor.fetchone()
                    if r:
                        producer_color_name = r[0] or ''
                        producer_code = r[1] or ''

                    cursor.execute(
                        "SELECT ps.name FROM products p LEFT JOIN product_series ps ON p.series_id = ps.id WHERE p.id = %s",
                        [product.mapped_product_uid]
                    )
                    r = cursor.fetchone()
                    if r:
                        series_name = r[0] or ''

                    cursor.execute("SELECT path_id FROM product_path WHERE product_id = %s", [product.mapped_product_uid])
                    selected_paths = [row[0] for row in cursor.fetchall()]

                    cursor.execute("SELECT attribute_id FROM product_attributes WHERE product_id = %s", [product.mapped_product_uid])
                    selected_attributes = [row[0] for row in cursor.fetchall()]

                    cursor.execute("SELECT unit FROM products WHERE id = %s", [product.mapped_product_uid])
                    r = cursor.fetchone()
                    if r and r[0] is not None:
                        selected_unit_id = r[0]

            extra_context.update({
                'is_mapped': is_mapped,
                'mpd_data': mpd_data,
                'main_colors': main_colors,
                'producer_colors': producer_colors,
                'mpd_paths': mpd_paths,
                'mpd_attributes': mpd_attributes,
                'mpd_brands': mpd_brands,
                'units': units,
                'size_categories': size_categories,
                'fabric_components': fabric_components,
                'selected_paths': selected_paths,
                'selected_attributes': selected_attributes,
                'producer_color_name': producer_color_name,
                'producer_code': producer_code,
                'series_name': series_name,
                'selected_unit_id': selected_unit_id,
            })
        except TabuProduct.DoesNotExist:
            extra_context['is_mapped'] = False
            extra_context['mpd_data'] = {}
            extra_context['main_colors'] = []
            extra_context['producer_colors'] = []
            extra_context['mpd_paths'] = []
            extra_context['mpd_attributes'] = []
            extra_context['mpd_brands'] = []
            extra_context['units'] = []
            extra_context['size_categories'] = []
            extra_context['fabric_components'] = []
            extra_context['selected_paths'] = []
            extra_context['selected_attributes'] = []
        except Exception as e:
            logger.exception("Błąd change_view Tabu: %s", e)
            extra_context['is_mapped'] = False
            extra_context['mpd_data'] = {}
            extra_context['main_colors'] = []
            extra_context['producer_colors'] = []
            extra_context['mpd_paths'] = []
            extra_context['mpd_attributes'] = []
            extra_context['mpd_brands'] = []
            extra_context['units'] = []
            extra_context['size_categories'] = []
            extra_context['fabric_components'] = []
            extra_context['selected_paths'] = []
            extra_context['selected_attributes'] = []

        return super().change_view(request, object_id, form_url, extra_context)

    @method_decorator(csrf_exempt)
    @method_decorator(require_http_methods(["POST"]))
    def mpd_create(self, request, product_id):
        """Tworzy nowy produkt w MPD na podstawie danych Tabu i formularza."""
        form_data = {
            'mpd_name': request.POST.get('mpd_name'),
            'mpd_short_description': request.POST.get('mpd_short_description'),
            'mpd_description': request.POST.get('mpd_description'),
            'mpd_brand': request.POST.get('mpd_brand'),
            'series_name': request.POST.get('series_name'),
            'unit_id': request.POST.get('unit_id'),
            'main_color_id': request.POST.get('main_color_id'),
            'producer_color_name': request.POST.get('producer_color_name'),
            'producer_code': request.POST.get('producer_code'),
            'mpd_paths': request.POST.getlist('mpd_paths'),
            'mpd_attributes': request.POST.getlist('mpd_attributes'),
            'fabric_component': request.POST.getlist('fabric_component[]'),
            'fabric_percentage': request.POST.getlist('fabric_percentage[]'),
            'upload_images': True,
        }
        from .services import create_mpd_product_from_tabu
        result = create_mpd_product_from_tabu(int(product_id), form_data)
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f'Utworzono produkt w MPD (ID: {result["mpd_product_id"]})',
                'mpd_product_id': result['mpd_product_id'],
            })
        status_code = 404 if (result.get('error_message') or '').find('nie istnieje') >= 0 else 400
        return JsonResponse({'success': False, 'error': result['error_message']}, status=status_code)
    def image_preview(self, obj):
        if obj and obj.image_url:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 200px; max-height: 200px;" /></a>',
                obj.image_url, obj.image_url
            )
        return '-'
    image_preview.short_description = 'Podgląd'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('brand', 'category')


@admin.register(TabuProductVariant)
class TabuProductVariantAdmin(admin.ModelAdmin):
    list_display = ['api_id', 'product', 'symbol', 'color', 'size', 'store', 'price_gross']
    list_filter = ['product__brand', 'product__category']
    search_fields = ['symbol', 'ean', 'product__name']
    readonly_fields = ['api_id']
    raw_id_fields = ['product']


@admin.register(ApiSyncLog)
class ApiSyncLogAdmin(admin.ModelAdmin):
    list_display = [
        'sync_type', 'status', 'started_at', 'completed_at',
        'products_processed', 'products_success', 'products_failed',
        'stock_changes_display', 'error_message',
    ]
    list_filter = ['status', 'sync_type', 'started_at']
    search_fields = ['sync_type', 'error_message']
    readonly_fields = ['started_at', 'completed_at', 'raw_response']
    ordering = ['-started_at']

    def stock_changes_display(self, obj):
        """Liczba zmian stanów zapisanych w historii (z raw_response)."""
        if obj.raw_response and isinstance(obj.raw_response, dict):
            n = obj.raw_response.get('stock_changes_logged')
            if n is not None:
                return n
        return '-'
    stock_changes_display.short_description = 'Zmiany historii'


@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'variant_symbol', 'old_stock', 'new_stock', 'stock_change', 'change_type', 'timestamp']
    list_filter = ['change_type', 'timestamp']
    search_fields = ['product_name', 'variant_symbol']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    list_per_page = 50
