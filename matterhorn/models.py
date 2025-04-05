from django.db import models
from django.contrib import admin
from django import forms

# Create your models here.
class Products(models.Model):
    id = models.AutoField(primary_key=True)
    active = models.CharField(max_length=10, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    name_without_number = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    creation_date = models.CharField(max_length=40, blank=True, null=True)  # Możesz rozważyć DateField lub DateTimeField
    color = models.CharField(max_length=50, blank=True, null=True)
    category_name = models.CharField(max_length=255, blank=True, null=True)
    category_id = models.IntegerField(blank=True, null=True)
    category_path = models.CharField(max_length=255, blank=True, null=True)
    brand_id = models.IntegerField(blank=True, null=True)
    brand = models.CharField(max_length=255, blank=True, null=True)
    stock_total = models.IntegerField(blank=True, null=True)
    url = models.URLField(max_length=255, blank=True, null=True)
    new_collection = models.CharField(max_length=5, blank=True, null=True)
    size_table = models.TextField(blank=True, null=True)
    weight = models.IntegerField(blank=True, null=True)
    size_table_txt = models.TextField(blank=True, null=True)
    size_table_html = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    timestamp = models.DateTimeField()
    mapped_product_id = models.IntegerField(null=True, blank=True)
    is_mapped = models.BooleanField(default=False)
    last_updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'products'
        verbose_name = "Product"
        verbose_name_plural = "Products"
    
    def __str__(self):
        return self.name or "Unnamed Product"


class Images(models.Model):
    image_id = models.BigAutoField(primary_key=True)
    image_path = models.TextField(blank=True, null=True)
    product = models.ForeignKey('Products', models.CASCADE, blank=True, null=True)
    timestamp = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'images'

class ProductsProxy(Products):
    class Meta:
        proxy = True
        verbose_name = "Mapper"
        verbose_name_plural = "Mapper"

    @admin.display(description="Product Color ID's")
    def get_product_color_id(self):
        other_colors = self.other_colors.all()  # Pobiera wszystkie powiązane rekordy z OtherColors
        return ', '.join(str(color.color_product.id) for color in other_colors) if other_colors else ""

    @admin.display(description="Variant Names")
    def get_variant_names(self):
        variants = self.variants.all()
        return ', '.join(variant.name for variant in variants if variant.name) if variants else ""

    @admin.display(description="Product in set")
    def get_product_in_set(self):
        product_in_set = self.product_in_set.all()
        return ', '.join(str(product.set_product.id) for product in product_in_set) if product_in_set else ""


    def __str__(self):
        return f"{self.id} {self.name} {self.color}"


class OtherColors(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Products, 
        on_delete=models.CASCADE,
        db_column='product_id',
        related_name='other_colors',
        db_index=True)
    color_product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='othercolors_color_product_id',
        db_column='color_product_id',
        db_index=True)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        verbose_name_plural = "Other Colors"
        db_table = 'other_colors'
        unique_together = (('product', 'color_product'),)
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['color_product']),
        ]

class ProductInSet(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        db_column='product_id',
        related_name='product_in_set',
        db_index=True)
    set_product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='productinset_set_product_id',
        db_index=True)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'product_in_set'
        verbose_name_plural = "Product In Set"
        unique_together = (('product', 'set_product'),)
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['set_product']),
        ]

class UpdateLog(models.Model):
    last_update = models.DateTimeField()
    description = models.CharField(max_length=255, blank=True, null=True)    
    data_items = models.TextField(blank=True, null=True)
    data_inventory = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'update_log'

class Variants(models.Model):
    variant_uid = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    stock = models.IntegerField(blank=True, null=True)
    max_processing_time = models.IntegerField(blank=True, null=True)
    ean = models.CharField(max_length=50, blank=True, null=True)
    product = models.ForeignKey(Products, on_delete=models.CASCADE , related_name='variants', blank=True, null=True)
    timestamp = models.DateTimeField()
    mapped_variant_id = models.IntegerField(null=True, blank=True)
    is_mapped = models.BooleanField(default=False)
    last_updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        verbose_name_plural = "Variants"
        db_table = 'variants'
        indexes = [
            models.Index(fields=['product']),
        ]

class VariantsInLine(admin.TabularInline):
    model = Variants
    extra = 0
    can_delete = False


class OtherColorsInline(admin.TabularInline):
    model = OtherColors
    fk_name = 'product'
    extra = 0
    can_delete = False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "color_product":
            obj_id = request.resolver_match.kwargs.get("object_id")  # get ID of the current object

            if obj_id:
                # get related products by `OtherColors`
                related_products = OtherColors.objects.filter(product_id=obj_id).values_list("color_product_id", flat=True)

                # get only related products by 'OtherColors`
                kwargs["queryset"] = ProductsProxy.objects.filter(id__in=related_products)
            else:
                kwargs["queryset"] = ProductsProxy.objects.none()  

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProductInSetInline(admin.TabularInline):
    model = ProductInSet
    fk_name = 'product'
    extra = 0
    can_delete = False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'set_product':
            obj_id = request.resolver_match.kwargs.get("object_id")

            if obj_id:
                related_products = ProductInSet.objects.filter(product_id=obj_id).values_list('set_product_id', flat=True)
                kwargs['queryset'] = Products.objects.filter(id__in=related_products)
            else:
                kwargs['queryset'] = Products.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class ProductsProxyAdminForm(forms.ModelForm):
    get_other_colors = forms.CharField(required=False, label="Other Colors", widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    class Meta:
        model = ProductsProxy
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'get_other_colors' not in self.fields:
            self.fields['get_other_colors'] = forms.CharField(
                required=False,
                label="Other Colors",
                widget=forms.TextInput(attrs={'readonly': 'readonly'})
            )

        if self.instance:
            self.fields['get_other_colors'].initial = ', '.join(str(color) for color in self.instance.other_colors.all())

