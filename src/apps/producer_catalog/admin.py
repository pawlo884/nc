from django.contrib import admin
from .models import ProducerSource, ProducerProduct, ProducerProductVariant, ProducerPriceHistory


@admin.register(ProducerSource)
class ProducerSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'base_url', 'is_active', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']


@admin.register(ProducerProduct)
class ProducerProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'source', 'external_id', 'scraped_at', 'updated_at']
    list_filter = ['source']
    search_fields = ['name', 'url', 'external_id']
    raw_id_fields = ['source']
    readonly_fields = ['scraped_at', 'created_at', 'updated_at']


@admin.register(ProducerProductVariant)
class ProducerProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'size_name', 'price_brutto', 'currency', 'scraped_at']
    list_filter = ['currency', 'product__source']
    search_fields = ['product__name', 'size_name']
    raw_id_fields = ['product']
    readonly_fields = ['scraped_at', 'created_at', 'updated_at']


@admin.register(ProducerPriceHistory)
class ProducerPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['variant', 'price_brutto', 'currency', 'recorded_at']
    list_filter = ['recorded_at', 'currency']
    search_fields = ['variant__product__name', 'variant__size_name']
    raw_id_fields = ['variant']
    readonly_fields = ['recorded_at']
    ordering = ['-recorded_at']
