from django.contrib import admin
from .models import Brand, Category, Product, ProductImage, ProductVariant, ApiSyncLog


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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_id', 'brand', 'category', 'active', 'price', 'stock_total', 'last_api_sync']
    list_filter = ['active', 'brand', 'category', 'new_collection', 'featured', 'on_sale', 'created_at', 'last_api_sync']
    search_fields = ['name', 'product_id', 'external_id', 'slug', 'description']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync', 'stock_total']
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('product_id', 'external_id', 'name', 'description', 'short_description', 'active')
        }),
        ('Relacje', {
            'fields': ('brand', 'category')
        }),
        ('Ceny', {
            'fields': ('price', 'price_net', 'price_gross', 'currency', 'vat_rate')
        }),
        ('Statusy', {
            'fields': ('new_collection', 'featured', 'on_sale')
        }),
        ('Linki', {
            'fields': ('url', 'slug')
        }),
        ('Dane JSON', {
            'fields': ('raw_data', 'attributes', 'prices', 'other_colors', 'products_in_set'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('creation_date', 'created_at', 'updated_at', 'last_api_sync')
        }),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'order', 'is_main', 'image_url']
    list_filter = ['is_main', 'created_at']
    search_fields = ['product__name', 'image_url', 'alt_text']
    readonly_fields = ['created_at']
    ordering = ['product', 'order']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'variant_id', 'size', 'color', 'stock', 'available', 'price', 'sku']
    list_filter = ['available', 'product__brand', 'product__category', 'created_at', 'last_api_sync']
    search_fields = ['variant_id', 'external_id', 'sku', 'ean', 'product__name', 'size', 'color']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync']
    fieldsets = (
        ('Identyfikatory', {
            'fields': ('variant_id', 'external_id', 'sku', 'ean')
        }),
        ('Produkt', {
            'fields': ('product',)
        }),
        ('Informacje o wariancie', {
            'fields': ('name', 'size', 'color', 'color_code')
        }),
        ('Stan magazynowy', {
            'fields': ('stock', 'stock_reserved', 'available')
        }),
        ('Ceny', {
            'fields': ('price', 'price_net', 'price_gross')
        }),
        ('Inne', {
            'fields': ('max_processing_time', 'raw_data', 'attributes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_api_sync')
        }),
    )


@admin.register(ApiSyncLog)
class ApiSyncLogAdmin(admin.ModelAdmin):
    list_display = ['sync_type', 'status', 'started_at', 'completed_at', 'products_processed', 'products_success', 'products_failed']
    list_filter = ['status', 'sync_type', 'started_at']
    search_fields = ['sync_type', 'error_message']
    readonly_fields = ['started_at', 'completed_at']
    ordering = ['-started_at']
