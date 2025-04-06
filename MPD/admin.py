from django.contrib import admin  # type: ignore
from .models import Brands, Products, Sizes
# Register your models here.


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    fields = ['name', 'description', 'brand' ]
    list_display = ['id', 'name', 'description', 'get_brand_name', ]


@admin.register(Brands)
class BrandsAdmin(admin.ModelAdmin):
    fields = ['name', 'logo_url', 'brand_lower', 'opis', ]
    list_display = ['id', 'name', ]


@admin.register(Sizes)
class SizesAdmin(admin.ModelAdmin):
    fields = ['name', 'category', 'unit', 'name_lower', ]
    list_display = ['id', 'name', 'category', 'unit', 'name_lower', ]
    list_filter = ['name', 'category', 'unit', 'name_lower',]