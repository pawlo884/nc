from django.contrib import admin  # type: ignore
from .models import Products, UpdateLog, ProductsProxy, ProductsProxyAdminForm, Images
from .defs_import import export_to_products
from django.utils.html import format_html

# Register your models here.
# admin.site.register(Products)


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_per_page = 30
    fields = ['active', 'name', 'description', 'creation_date', 'color', 'category_name', 'category_path', 'brand', 'url', 'url_link', 'new_collection', 'size_table', 'size_table_txt', 'size_table_html', 'price', 'get_product_images', 'get_variants', 'get_other_colors', 'get_product_in_set']
    list_display = ['id', 'active', 'name', 'color', 'category_name', 'brand', 'new_collection', 'price', 'timestamp', 'url_link']
    list_filter = ['active', 'category_name', 'brand']
    readonly_fields = ["active", "name", "description", "creation_date", 'url', 'url_link', "color", "category_name", "category_path", "brand", "new_collection", "size_table", "size_table_txt", "size_table_html", "price", "mapped_product_id", "is_mapped", "get_product_images", "get_variants", "get_other_colors", "get_product_in_set"]
    search_fields = ['id', 'name', 'brand', 'category_name']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('variants', 'other_colors', 'product_in_set')
        return queryset

    def get_product_images(self, obj):
        images = Images.objects.filter(product=obj)
        if images:
            html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
            for image in images:
                if image.image_path:
                    html += f'<a href="{image.image_path}" target="_blank" rel="noopener noreferrer"><img src="{image.image_path}" style="max-height: 100px; max-width: 100px; margin: 5px; cursor: pointer;" /></a>'
            html += '</div>'
            return format_html(html)
        return "-"
    get_product_images.short_description = 'Images'

    def get_variants(self, obj):
        variants = obj.variants.all()
        if variants:
            html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
            for variant in variants:
                html += f'''
                    <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; min-width: 200px;">
                        <div><strong>Nazwa:</strong> {variant.name or '-'}</div>
                        <div><strong>Stan:</strong> {variant.stock or '-'}</div>
                        <div><strong>EAN:</strong> {variant.ean or '-'}</div>
                        <div><strong>Czas przetwarzania:</strong> {variant.max_processing_time or '-'}</div>
                    </div>
                '''
            html += '</div>'
            return format_html(html)
        return "-"
    get_variants.short_description = 'Variants'

    def get_other_colors(self, obj):
        other_colors = obj.other_colors.all()
        if other_colors:
            html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
            for color in other_colors:
                if color.color_product:
                    # Pobierz pierwsze zdjęcie produktu
                    first_image = Images.objects.filter(product=color.color_product).first()
                    image_html = ''
                    if first_image and first_image.image_path:
                        image_html = f'<a href="{first_image.image_path}" target="_blank" rel="noopener noreferrer"><img src="{first_image.image_path}" style="max-height: 100px; max-width: 100px; margin: 5px; cursor: pointer;" /></a>'
                    
                    html += f'''
                        <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; min-width: 200px;">
                            <div style="text-align: center; margin-bottom: 10px;">{image_html}</div>
                            <div><strong>ID:</strong> {color.color_product.id}</div>
                            <div><strong>Nazwa:</strong> {color.color_product.name or '-'}</div>
                            <div><strong>Kolor:</strong> {color.color_product.color or '-'}</div>
                            <div style="margin-top: 10px;">
                                <a href="/admin/matterhorn/products/{color.color_product.id}/change/" class="button" style="background-color: #417690; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">Edytuj produkt</a>
                            </div>
                        </div>
                    '''
            html += '</div>'
            return format_html(html)
        return "-"
    get_other_colors.short_description = 'Other Colors'

    def get_product_in_set(self, obj):
        products_in_set = obj.product_in_set.all()
        if products_in_set:
            html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
            for product in products_in_set:
                if product.set_product:
                    # Pobierz pierwsze zdjęcie produktu
                    first_image = Images.objects.filter(product=product.set_product).first()
                    image_html = ''
                    if first_image and first_image.image_path:
                        image_html = f'<a href="{first_image.image_path}" target="_blank" rel="noopener noreferrer"><img src="{first_image.image_path}" style="max-height: 100px; max-width: 100px; margin: 5px; cursor: pointer;" /></a>'
                    
                    html += f'''
                        <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; min-width: 200px;">
                            <div style="text-align: center; margin-bottom: 10px;">{image_html}</div>
                            <div><strong>ID:</strong> {product.set_product.id}</div>
                            <div><strong>Nazwa:</strong> {product.set_product.name or '-'}</div>
                            <div><strong>Kolor:</strong> {product.set_product.color or '-'}</div>
                            <div style="margin-top: 10px;">
                                <a href="/admin/matterhorn/products/{product.set_product.id}/change/" class="button" style="background-color: #417690; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">Edytuj produkt</a>
                            </div>
                        </div>
                    '''
            html += '</div>'
            return format_html(html)
        return "-"
    get_product_in_set.short_description = 'Products in Set'

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
                       "mapped_product_id", "is_mapped", 'get_product_color_id', 'get_variant_names', 'get_product_in_set'] 
    search_fields = ('id', 'name', 'brand')
    actions = [export_to_products]

    def get_product_color_id(self, obj):
        if obj.mapped_product_id:
            return format_html(
                '<a href="/admin/matterhorn/products/{}/change/" class="button" style="background-color: #417690; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">Przejdź do produktu</a>',
                obj.mapped_product_id
            )
        return "-"
    get_product_color_id.short_description = "Produkt"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


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
