"""
Konfiguracja admin dla aplikacji web_agent.
"""
from django.contrib import admin
from .models import AutomationRun, ProductProcessingLog, BrandConfig, ProducerColor


@admin.register(AutomationRun)
class AutomationRunAdmin(admin.ModelAdmin):
    """Admin dla AutomationRun"""
    list_display = [
        'id', 'started_at', 'completed_at', 'status',
        'products_processed', 'products_success', 'products_failed',
        'brand_id', 'category_id'
    ]
    list_filter = ['status', 'started_at', 'brand_id', 'category_id']
    search_fields = ['id', 'error_message']
    readonly_fields = ['started_at', 'completed_at']
    date_hierarchy = 'started_at'

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('status', 'started_at', 'completed_at')
        }),
        ('Statystyki', {
            'fields': ('products_processed', 'products_success', 'products_failed')
        }),
        ('Filtry', {
            'fields': ('brand_id', 'category_id', 'filters')
        }),
        ('Błędy', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductProcessingLog)
class ProductProcessingLogAdmin(admin.ModelAdmin):
    """Admin dla ProductProcessingLog"""
    list_display = [
        'id', 'automation_run', 'product_id', 'product_name',
        'status', 'mpd_product_id', 'processed_at'
    ]
    list_filter = ['status', 'automation_run', 'processed_at']
    search_fields = ['product_id', 'product_name', 'error_message']
    readonly_fields = ['processed_at']
    date_hierarchy = 'processed_at'

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('automation_run', 'product_id', 'product_name', 'status')
        }),
        ('Wynik', {
            'fields': ('mpd_product_id', 'error_message', 'processed_at')
        }),
        ('Dane przetwarzania', {
            'fields': ('processing_data',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProducerColor)
class ProducerColorAdmin(admin.ModelAdmin):
    list_display = ['brand_name', 'color_name',
                    'usage_count', 'created_at', 'updated_at']
    list_filter = ['brand_name', 'created_at']
    search_fields = ['brand_name', 'color_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['brand_name', 'color_name']

    fieldsets = (
        ('Informacje podstawowe', {
            'fields': ('brand_id', 'brand_name', 'color_name', 'normalized_color')
        }),
        ('Statystyki', {
            'fields': ('usage_count',)
        }),
        ('Daty', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(BrandConfig)
class BrandConfigAdmin(admin.ModelAdmin):
    """Admin dla BrandConfig"""
    list_display = [
        'brand_name', 'brand_id', 'default_active_filter',
        'default_is_mapped_filter', 'similarity_threshold', 'updated_at'
    ]
    list_filter = ['default_active_filter',
                   'default_is_mapped_filter', 'created_at', 'updated_at']
    search_fields = ['brand_name', 'brand_id']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'updated_at'

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('brand_id', 'brand_name')
        }),
        ('Domyślne filtry', {
            'fields': ('default_active_filter', 'default_is_mapped_filter')
        }),
        ('Mapowanie kolorów', {
            'fields': ('color_mapping',),
            'description': 'Mapowanie kolorów producenta w formacie JSON: {"Dark Brown": "Ciemny Brąz", "Beige": "Beż"}'
        }),
        ('Atrybuty i wyszukiwanie', {
            'fields': ('attributes', 'similarity_threshold'),
            'description': 'Lista atrybutów do wyszukiwania w opisie produktu oraz próg podobieństwa dla cosine similarity'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
