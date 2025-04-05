from django.contrib import admin  # type: ignore
from .models import Products, UpdateLog, VariantsInLine, OtherColorsInline, ProductInSetInline, ProductsProxy, ProductsProxyAdminForm
from .defs_import import export_to_products
from django.utils.html import format_html

# Register your models here.
# admin.site.register(Products)


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_per_page = 30
    fields = ['active', 'name', 'description', 'creation_date', 'color', 'category_name', 'category_path', 'brand', 'url','url_link', 'new_collection', 'size_table', 'size_table_txt', 'size_table_html', 'price', ]
    list_display = ['id', 'active', 'name', 'color', 'category_name', 'brand', 'new_collection', 'price', 'timestamp', 'url_link', ]
    list_filter = ['active', 'category_name', 'brand',]
    readonly_fields = ["active", "name", "description", "creation_date", 'url','url_link',  "color", "category_name", "category_path", "brand", "new_collection", "size_table", "size_table_txt", "size_table_html", "price", "mapped_product_id", "is_mapped", ]
    search_fields = ['id', 'name', 'brand', 'category_name',]
    inlines = [VariantsInLine, OtherColorsInline, ProductInSetInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('variants', 'other_colors', 'product_in_set')
        return queryset

    def url_link(self, obj):
        if obj.url:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">🌐 Otwórz link</a>',
                obj.url
            )
        return "-"
    url_link.short_description = "URL"


@admin.register(ProductsProxy)
class MapperAdmin(admin.ModelAdmin):
    form = ProductsProxyAdminForm
    list_per_page = 30
    fields = ['active', 'name', 'description', 'creation_date', 'color', 'category_name', 'category_path', 'brand', 'url', 'new_collection', 'size_table', 'size_table_txt', 'size_table_html', 'price', 
              'mapped_product_id', 'is_mapped', 'get_product_color_id', 'get_variant_names', 'get_product_in_set']
    list_display = ('id', 'name', 'color', 'category_name', 'brand', 'timestamp', 'mapped_product_id', 'is_mapped', 'get_product_color_id', 'get_variant_names', 'get_product_in_set', 'last_updated', )
    list_filter = ('category_name', 'brand', 'is_mapped', )
    readonly_fields = ["active", "name", "description", "creation_date", "color", "category_name", "category_path", "brand", "new_collection", "size_table", "size_table_txt", "size_table_html", "price",
                       "mapped_product_id", "is_mapped", 'get_product_color_id', 'get_variant_names','get_product_in_set'] 
    search_fields = ('id', 'name', 'brand')
    actions = [export_to_products]
 
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


    '''inlines = [VariantsInLine, OtherColorsInline, ProductInSetInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('variants', 'other_colors', 'product_in_set')
        return queryset'''


@admin.register(UpdateLog)
class UpdateLogAdmin(admin.ModelAdmin):
    fields = ['last_update', 'description', 'data_items', 'data_inventory',]
    list_display = ['id', 'last_update', 'description',]
    readonly_fields = ['last_update', 'description', 'data_items', 'data_inventory',]
    list_per_page = 20


'''@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'level', 'message')
    list_filter = ('level', 'timestamp')
    search_fields = ('message',)'''
