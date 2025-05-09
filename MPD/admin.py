from django.contrib import admin  # type: ignore
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from .models import Brands, Products, Sizes, Sources, ProductVariants, ProductSet, ProductSetItem
# Register your models here.


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_per_page = 30
    fields = ['name', 'description', 'brand', 'show_variants', 'show_images']
    list_display = ['id', 'name', 'description', 'brand', 'updated_at']
    list_filter = ['brand']
    search_fields = ['id', 'name', 'description', 'brand__name']
    readonly_fields = ['show_variants', 'show_images']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')

    def show_variants(self, obj):
        variants = obj.productvariants_set.all()
        if not variants:
            return "Brak wariantów"
        html = "<table style='border-collapse:collapse;'>"
        html += "<tr><th style='border:1px solid #ccc;padding:2px 6px;'>Kolor</th><th style='border:1px solid #ccc;padding:2px 6px;'>Rozmiar</th><th style='border:1px solid #ccc;padding:2px 6px;'>Stan</th><th style='border:1px solid #ccc;padding:2px 6px;'>EAN</th></tr>"
        for v in variants:
            size_name = v.size.name if v.size else ""
            html += f"<tr><td style='border:1px solid #ccc;padding:2px 6px;'>{v.color}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{size_name}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{v.total_stock}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{v.ean}</td></tr>"
        html += "</table>"
        return mark_safe(html)

    def show_images(self, obj):
        images = obj.images.all()
        if not images:
            return "Brak zdjęć"
        html = ""
        for img in images:
            url = img.file_path
            html += f'<a href="{url}" target="_blank"><img src="{url}" style="max-height:60px; margin:2px; border:1px solid #ccc;" /></a>'
        return format_html(html)
    show_images.short_description = "Zdjęcia produktu"


@admin.register(Brands)
class BrandsAdmin(admin.ModelAdmin):
    fields = ['name', 'logo_url', 'brand_lower', 'opis']
    list_display = ['id', 'name']
    search_fields = ['name']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


@admin.register(Sizes)
class SizesAdmin(admin.ModelAdmin):
    fields = ['name', 'category', 'unit', 'name_lower']
    list_display = ['id', 'name', 'category', 'unit', 'name_lower']
    list_filter = ['name', 'category', 'unit', 'name_lower']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')

@admin.register(Sources)
class SourceAdmin(admin.ModelAdmin):
    fields = ['name', 'location','type']
    list_display = ['id', 'name', 'location','type']
    search_fields = ['name']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')

@admin.register(ProductSet)
class ProductSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'mapped_product', 'created_at', 'updated_at')
    search_fields = ('name', 'mapped_product__name')
    list_filter = ('created_at', 'updated_at')
    raw_id_fields = ('mapped_product',)

@admin.register(ProductSetItem)
class ProductSetItemAdmin(admin.ModelAdmin):
    list_display = (  'quantity', 'created_at')
    # search_fields = ('')
    list_filter = ('created_at',)
    #raw_id_fields = ('set', 'mapped_product',)