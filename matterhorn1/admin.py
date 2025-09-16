from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Brand, Category, Product, ProductDetails, ProductImage, 
    ProductVariant, ApiSyncLog
)


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
        'product_id', 'created_at', 'updated_at', 'stock_total'
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
    modeladmin.message_user(request, f"Oznaczono {queryset.count()} produktów jako aktywne.")

@admin.action(description='Oznacz jako nieaktywne')
def make_inactive(modeladmin, request, queryset):
    queryset.update(active=False)
    modeladmin.message_user(request, f"Oznaczono {queryset.count()} produktów jako nieaktywne.")

ProductAdmin.actions = [make_active, make_inactive]