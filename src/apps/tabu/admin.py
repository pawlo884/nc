from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from .models import Brand, Category, ApiSyncLog, TabuProduct, TabuProductImage, TabuProductVariant, StockHistory


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
        'store_total', 'last_update'
    ]
    list_display_links = ['api_id', 'name']
    list_filter = [TabuBrandFilter, TabuCategoryFilter, 'last_update']
    search_fields = ['name', 'symbol', 'ean', 'producer_name', 'brand__name', 'category__name']
    readonly_fields = ['api_id', 'last_update', 'image_preview']
    ordering = ['-api_id']
    inlines = [TabuProductImageInline, TabuProductVariantInline]

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
    )

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
