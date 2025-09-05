from django.db import models
from decimal import Decimal
from django.contrib import admin


# Create your models here.

class Attributes(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'attributes'
        app_label = 'MPD'
        verbose_name = 'Attribute'
        verbose_name_plural = 'Attributes'


class Brands(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    logo_url = models.TextField(blank=True, null=True)
    opis = models.TextField(blank=True, null=True)
    url = models.URLField(max_length=255, blank=True, null=True)
    iai_brand_id = models.IntegerField(blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'brands'
        app_label = 'MPD'
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'

    def save(self, *args, **kwargs):
        print(f"Zapisywanie marki: {self.name}")
        print(f"Używana baza danych: {self._state.db}")
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name) if self.name else 'Brak nazwy'


class Colors(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    hex_code = models.CharField(max_length=7, blank=True, null=True)
    parent_id = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, db_column='parent_id')
    iai_colors_id = models.IntegerField(blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'colors'
        app_label = 'MPD'
        verbose_name = 'Color'
        verbose_name_plural = 'Colors'

    def __str__(self):
        return str(self.name) if self.name else 'Brak nazwy'


class Products(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=500, blank=True, null=True)
    brand = models.ForeignKey(
        Brands, on_delete=models.CASCADE, db_column='brand_id', to_field='id', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    series = models.ForeignKey('ProductSeries', db_column='series_id',
                               on_delete=models.DO_NOTHING, blank=True, null=True)
    unit = models.ForeignKey(
        'Units', on_delete=models.CASCADE, db_column='unit', to_field='unit_id', null=True, blank=True)
    visibility = models.BooleanField(
        default=True, verbose_name='Widoczność w sklepie')
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'products'
        app_label = 'MPD'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return str(self.name) if self.name else 'Brak nazwy'

    def get_brand_name(self):
        return self.brand.name if self.brand else 'Brak marki'


class Sizes(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    unit = models.CharField(max_length=255, blank=True, null=True)
    name_lower = models.CharField(max_length=255, blank=True, null=True)
    iai_size_id = models.CharField(max_length=255, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'sizes'
        app_label = 'MPD'
        verbose_name = 'Size'
        verbose_name_plural = 'Sizes'

    def __str__(self):
        return str(self.name) if self.name else 'Brak nazwy'


class Sources(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    long_name = models.CharField(max_length=255, blank=True, null=True)
    short_name = models.CharField(max_length=100, blank=True, null=True)
    showcase_image = models.URLField(max_length=500, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    tel = models.CharField(max_length=50, blank=True, null=True)
    fax = models.CharField(max_length=50, blank=True, null=True)
    www = models.URLField(max_length=255, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    zipcode = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'sources'
        app_label = 'MPD'
        verbose_name = 'Source'
        verbose_name_plural = 'Sources'


class ProductVariants(models.Model):
    variant_id = models.IntegerField(db_column='variant_id', primary_key=True)
    product = models.ForeignKey(
        Products, on_delete=models.CASCADE, db_column='product_id')
    color = models.ForeignKey(
        Colors, on_delete=models.CASCADE, db_column='color_id', null=True, blank=True)
    producer_color = models.ForeignKey(
        Colors, on_delete=models.CASCADE, db_column='producer_color_id', null=True, blank=True, related_name='producer_variants')
    size = models.ForeignKey(
        Sizes, on_delete=models.CASCADE, db_column='size_id', null=True, blank=True)
    producer_code = models.CharField(max_length=255, blank=True, null=True)
    iai_product_id = models.IntegerField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'product_variants'
        app_label = 'MPD'
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'

    def __str__(self):
        return f"{self.product.name} - {self.color.name if self.color else 'Brak koloru'} - {self.size.name if self.size else 'Brak rozmiaru'}"


class ProductvariantsSources(models.Model):
    id = models.BigAutoField(primary_key=True)
    variant = models.ForeignKey(
        ProductVariants, on_delete=models.CASCADE, db_column='variant_id', to_field='variant_id')
    source = models.ForeignKey(
        Sources, on_delete=models.RESTRICT, db_column='source_id', null=True, blank=True)
    ean = models.CharField(max_length=50, blank=True, null=True)
    variant_uid = models.IntegerField(blank=True, null=True)
    gtin14 = models.CharField(max_length=50, blank=True, null=True)
    gtin13 = models.CharField(max_length=50, blank=True, null=True)
    gtin12 = models.CharField(max_length=50, blank=True, null=True)
    isbn10 = models.CharField(max_length=50, blank=True, null=True)
    gtin8 = models.CharField(max_length=50, blank=True, null=True)
    upce = models.CharField(max_length=50, blank=True, null=True)
    mpn = models.CharField(max_length=50, blank=True, null=True)
    other = models.CharField(max_length=50, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'product_variants_sources'
        app_label = 'MPD'
        verbose_name = 'Product Variant Source'
        verbose_name_plural = 'Product Variant Sources'


class ProductVariantsRetailPrice(models.Model):
    variant = models.OneToOneField(ProductVariants, on_delete=models.CASCADE,
                                   db_column='variant_id', primary_key=True, to_field='variant_id')
    retail_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    vat = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)
    net_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'product_variants_retail_price'


class ProductImage(models.Model):
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Products, on_delete=models.CASCADE, db_column='product_id', related_name='images')
    iai_product_id = models.IntegerField(blank=True, null=True)
    file_path = models.CharField(max_length=500)
    updated_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'product_images'
        app_label = 'MPD'
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'

    def __str__(self):
        return str(self.file_path)


class ProductSet(models.Model):
    id = models.BigAutoField(primary_key=True)
    mapped_product = models.ForeignKey(
        'Products', on_delete=models.CASCADE, related_name='product_sets')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'product_set'
        verbose_name = 'Product Set'
        verbose_name_plural = 'Product Sets'

    def __str__(self):
        return f"{self.name} ({self.mapped_product.name if self.mapped_product else ''})"


class ProductSetItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    product_set_id = models.IntegerField()
    product_id = models.IntegerField()
    quantity = models.IntegerField(default=1)
    position = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'product_set_items'
        verbose_name = 'Product Set Item'
        verbose_name_plural = 'Product Set Items'

    def __str__(self):
        return f"ProductSetItem {self.id} (product_id={self.product_id}, product_set_id={self.product_set_id})"


class ProductSeries(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'product_series'
        app_label = 'MPD'
        verbose_name = 'Seria'
        verbose_name_plural = 'Serie'
        ordering = ['name']

    def __str__(self):
        return str(self.name) if self.name else f'Seria {self.id}'


class StockAndPrices(models.Model):
    id = models.BigIntegerField(primary_key=True)
    variant = models.ForeignKey(
        ProductVariants, on_delete=models.CASCADE, db_column='variant_id', to_field='variant_id')
    source = models.ForeignKey(
        Sources, on_delete=models.CASCADE, db_column='source_id')
    stock = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    last_updated = models.DateTimeField()
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'stock_and_prices'
        verbose_name = 'Stan magazynowy'
        verbose_name_plural = 'Stany magazynowe'


class StockHistory(models.Model):
    id = models.BigIntegerField(primary_key=True)
    stock_id = models.BigIntegerField()
    source_id = models.BigIntegerField(null=True, blank=True)
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    previous_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'))
    new_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'))
    change_date = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'stock_history'
        verbose_name = 'Historia stanu magazynowego'
        verbose_name_plural = 'Historia stanów magazynowych'


class Categories(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    path = models.CharField(max_length=255, blank=True, null=True)
    parent_id = models.BigIntegerField(blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'categories'
        verbose_name = 'Kategoria'
        verbose_name_plural = 'Kategorie'


class StockAndPricesInline(admin.TabularInline):
    model = StockAndPrices
    product = models.ForeignKey(
        Products, on_delete=models.CASCADE, related_name='stock_and_prices')
    fields = ['variant_id', 'stock', 'price', 'currency']
    readonly_fields = ['variant_id', 'stock', 'price', 'currency']
    extra = 0
    can_delete = False
    max_num = 0

    def has_add_permission(self, request, obj=None):
        return False


class Vat(models.Model):
    id = models.BigAutoField(primary_key=True)
    vat_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'vat'


class Paths(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    path = models.CharField(max_length=255, blank=True, null=True)
    parent_id = models.BigIntegerField(blank=True, null=True)
    iai_category_id = models.IntegerField(blank=True, null=True)
    iai_menu_id = models.IntegerField(blank=True, null=True)
    iai_menu_parent_id = models.IntegerField(blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'path'
        verbose_name = 'Ścieżka'
        verbose_name_plural = 'Ścieżki'


class ProductPaths(models.Model):
    id = models.BigAutoField(primary_key=True)
    product_id = models.IntegerField()
    path_id = models.IntegerField()
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'product_path'
        verbose_name = 'Ścieżka produktu'
        verbose_name_plural = 'Ścieżki produktów'
        unique_together = ('product_id', 'path_id')


class Units(models.Model):
    id = models.BigAutoField(primary_key=True)
    unit_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'units'
        verbose_name = 'Jednostka'
        verbose_name_plural = 'Jednostki'


class FabricComponent(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'fabric_component'

    def __str__(self):
        return str(self.name) if self.name else "Brak nazwy"


class ProductFabric(models.Model):
    product = models.ForeignKey(
        Products, on_delete=models.CASCADE, related_name='fabrics')
    component = models.ForeignKey(FabricComponent, on_delete=models.CASCADE)
    percentage = models.PositiveSmallIntegerField()

    class Meta:
        db_table = 'product_fabric'
        unique_together = ('product', 'component')

    def __str__(self):
        component_name = self.component.name if self.component and self.component.name else "Nieznany komponent"
        return f"{component_name} {self.percentage}%"


class IaiProductCounter(models.Model):
    id = models.IntegerField(primary_key=True)
    counter_value = models.BigIntegerField()
    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'iai_product_counter'
        verbose_name = 'Licznik IAI Product ID'
        verbose_name_plural = 'Liczniki IAI Product ID'

    def __str__(self):
        return f"Licznik IAI: {str(self.counter_value)}"


class FullChangeFile(models.Model):
    id = models.BigAutoField(primary_key=True)
    filename = models.CharField(max_length=255)
    timestamp = models.CharField(max_length=50)  # YYYY-MM-DDTHH-MM-SS
    created_at = models.DateTimeField(auto_now_add=True)
    bucket_url = models.URLField(blank=True, null=True)
    local_path = models.CharField(max_length=500, blank=True, null=True)
    file_size = models.BigIntegerField(default=0)

    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'full_change_files'
        verbose_name = 'Plik XML'
        verbose_name_plural = 'Pliki XML'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.timestamp}) - {self.file_size} bytes"
