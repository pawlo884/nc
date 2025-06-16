from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


# Create your models here.


class Brands(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    logo_url = models.TextField(blank=True, null=True)
    opis = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
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
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    brand = models.ForeignKey(
        Brands, on_delete=models.CASCADE, db_column='brand_id', to_field='id')
    updated_at = models.DateTimeField(blank=True, null=True)
    series = models.ForeignKey('ProductSeries', db_column='series_id',
                               on_delete=models.DO_NOTHING, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = False
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

    class Meta:
        managed = False
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

    class Meta:
        managed = True
        db_table = 'sources'
        app_label = 'MPD'
        verbose_name = 'Source'
        verbose_name_plural = 'Sources'


class ProductVariants(models.Model):
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Products, on_delete=models.CASCADE, db_column='product_id')
    variant_id = models.IntegerField()
    source = models.ForeignKey(
        Sources, on_delete=models.RESTRICT, db_column='source_id', null=True, blank=True)
    color = models.ForeignKey(
        Colors, on_delete=models.CASCADE, db_column='color_id', null=True, blank=True)
    producer_color = models.ForeignKey(
        Colors, on_delete=models.CASCADE, db_column='producer_color_id', null=True, blank=True, related_name='producer_variants')
    size = models.ForeignKey(
        Sizes, on_delete=models.CASCADE, db_column='size_id', null=True, blank=True)
    ean = models.CharField(max_length=50, blank=True, null=True)
    variant_uid = models.IntegerField(blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'product_variants'
        app_label = 'MPD'
        unique_together = ('variant_id', 'source')
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'

    def __str__(self):
        return f"{self.product.name} - {self.color.name if self.color else 'Brak koloru'} - {self.size.name if self.size else 'Brak rozmiaru'}"


class ProductImage(models.Model):
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Products, on_delete=models.CASCADE, db_column='product_id', related_name='images')
    variant_id = models.IntegerField(blank=True, null=True)
    file_path = models.CharField(max_length=500)

    class Meta:
        managed = False
        db_table = 'product_images'
        app_label = 'MPD'
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'

    def __str__(self):
        return self.file_path


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
        managed = False
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
        managed = False
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
        managed = False
        db_table = 'product_series'
        app_label = 'MPD'
        verbose_name = 'Seria'
        verbose_name_plural = 'Serie'

    def __str__(self):
        return str(self.name) if self.name else f'Seria {self.id}'


class StockAndPrices(models.Model):
    id = models.BigIntegerField(primary_key=True)
    variant_id = models.BigIntegerField()
    source_id = models.BigIntegerField()
    stock = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    last_updated = models.DateTimeField()

    class Meta:
        managed = False
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
        managed = False
        db_table = 'stock_history'
        verbose_name = 'Historia stanu magazynowego'
        verbose_name_plural = 'Historia stanów magazynowych'


class Categories(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    path = models.CharField(max_length=255, blank=True, null=True)
    parent_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'categories'
        verbose_name = 'Kategoria'
        verbose_name_plural = 'Kategorie'
