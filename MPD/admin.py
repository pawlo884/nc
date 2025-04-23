from django.contrib import admin  # type: ignore
from .models import Brands, Products, Sizes, Sources
# Register your models here.


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    fields = ['name', 'description', 'brand']
    list_display = ['id', 'name', 'description', 'get_brand_name', 'updated_at']
    list_filter = ['brand', 'updated_at']
    search_fields = ['name', 'description', 'brand__name']
    list_per_page = 20
    ordering = ['-id']
    raw_id_fields = ['brand']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


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