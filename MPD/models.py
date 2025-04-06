from django.db import models


# Create your models here.


class Brands(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    logo_url = models.TextField(blank=True, null=True)
    brand_lower = models.CharField(max_length=255, blank=True, null=True)
    opis = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'brands'
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'

    def __str__(self) -> str:
        return self.name if self.name else 'Brak nazwy'


class Products(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    # brand_id = models.IntegerField(blank=True, null=True)
    brand = models.ForeignKey(Brands, on_delete=models.CASCADE)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.id} {self.name}"

    def get_brand_name(self):
        return self.brand.name

    get_brand_name.short_description = 'Brand Name'


class Sizes(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    unit = models.CharField(max_length=255, blank=True, null=True)
    name_lower = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sizes'
        verbose_name = 'Size'
        verbose_name_plural = 'Sizes'