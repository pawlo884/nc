from django.contrib import admin

from .models import (
    Brand, Category, ApiSyncLog, MadaProduct, MadaProductImage, MadaProductVariant,
    StockHistory, Saga, SagaStep,
)
from core.db_routers import _get_mada_db
from core.wholesaler_admin import (
    make_scoped_filter, render_product_thumbnail, ReadOnlyLogAdminMixin,
    RouterScopedQuerysetMixin,
)


@admin.register(Brand)
class BrandAdmin(RouterScopedQuerysetMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = ['producer_id', 'name', 'created_at', 'updated_at']
    search_fields = ['producer_id', 'name']
    ordering = ['name']


@admin.register(Category)
class CategoryAdmin(RouterScopedQuerysetMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = ['category_id', 'name', 'parent', 'path', 'created_at']
    list_filter = ['parent']
    search_fields = ['category_id', 'name', 'path']
    ordering = ['name']


MadaBrandFilter = make_scoped_filter(
    title='Marka', parameter_name='brand', counterpart_parameter_name='category',
    related_model=Brand,
)
MadaCategoryFilter = make_scoped_filter(
    title='Kategoria', parameter_name='category', counterpart_parameter_name='brand',
    related_model=Category,
)


class MadaProductImageInline(admin.TabularInline):
    model = MadaProductImage
    extra = 0
    fields = ['api_image_id', 'image_preview', 'image_url', 'order']
    readonly_fields = ['api_image_id', 'image_preview']

    def image_preview(self, obj):
        if obj and obj.image_url:
            return render_product_thumbnail(obj.image_url, fallback_host='mada.pl')
        return '-'
    image_preview.short_description = 'Podgląd'


class MadaProductVariantInline(admin.TabularInline):
    model = MadaProductVariant
    extra = 0
    fields = ['variant_key', 'color', 'size', 'ean', 'stock', 'is_mapped', 'mapped_variant_uid']
    readonly_fields = ['variant_key']


@admin.register(MadaProduct)
class MadaProductAdmin(RouterScopedQuerysetMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = [
        'api_id', 'thumbnail', 'name', 'brand', 'category', 'price', 'old_price',
        'is_active', 'mapped_product_uid', 'updated_at',
    ]
    list_filter = ['is_active', MadaBrandFilter, MadaCategoryFilter]
    search_fields = ['api_id', 'name']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync', 'raw_data']
    inlines = [MadaProductVariantInline, MadaProductImageInline]
    ordering = ['-api_id']

    def thumbnail(self, obj):
        first_image = obj.images.order_by('order').first()
        if first_image:
            return render_product_thumbnail(first_image.image_url, fallback_host='mada.pl')
        return '-'
    thumbnail.short_description = 'Zdjęcie'


@admin.register(MadaProductVariant)
class MadaProductVariantAdmin(RouterScopedQuerysetMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = [
        'product', 'color', 'size', 'ean', 'stock', 'is_mapped', 'mapped_variant_uid', 'updated_at',
    ]
    list_filter = ['is_mapped']
    search_fields = ['ean', 'variant_key', 'product__name', 'product__api_id']


@admin.register(ApiSyncLog)
class ApiSyncLogAdmin(RouterScopedQuerysetMixin, ReadOnlyLogAdminMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = [
        'sync_type', 'status', 'file_name', 'started_at', 'completed_at',
        'products_processed', 'products_created', 'products_updated', 'products_failed',
    ]
    list_filter = ['sync_type', 'status']
    ordering = ['-started_at']


@admin.register(StockHistory)
class StockHistoryAdmin(RouterScopedQuerysetMixin, ReadOnlyLogAdminMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = [
        'product_name', 'variant_label', 'old_stock', 'new_stock', 'stock_change',
        'change_type', 'timestamp',
    ]
    list_filter = ['change_type']
    search_fields = ['product_name', 'product_api_id', 'variant_key']
    ordering = ['-timestamp']


@admin.register(Saga)
class SagaAdmin(RouterScopedQuerysetMixin, ReadOnlyLogAdminMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = ['saga_id', 'saga_type', 'status', 'completed_steps', 'total_steps', 'created_at']
    list_filter = ['saga_type', 'status']
    search_fields = ['saga_id']
    ordering = ['-created_at']


@admin.register(SagaStep)
class SagaStepAdmin(RouterScopedQuerysetMixin, ReadOnlyLogAdminMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = ['saga', 'step_order', 'step_name', 'status', 'started_at', 'completed_at']
    list_filter = ['status']
    ordering = ['saga', 'step_order']
