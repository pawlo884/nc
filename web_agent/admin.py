"""
Konfiguracja admin dla aplikacji web_agent.
"""
from django.contrib import admin
from .models import AutomationRun, ProductProcessingLog


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
