from django.db import models
from decimal import Decimal


class Manufacturer(models.Model):
    """Model dla dostawców/marek WEGA"""
    manufacturer_id = models.CharField(
        max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    gprs = models.TextField(blank=True, null=True,
                            help_text="Dane GPRS (wymóg unijny)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wega_manufacturer'
        verbose_name = 'Dostawca'
        verbose_name_plural = 'Dostawcy'
        ordering = ['name']
        indexes = [
            models.Index(fields=['manufacturer_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.manufacturer_id})"


class Category(models.Model):
    """Model dla kategorii WEGA z drzewem hierarchicznym"""
    category_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    is_filter = models.BooleanField(
        default=False,
        help_text="Czy kategoria jest filtrem (nie kategorią w menu)"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Kategoria nadrzędna"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wega_category'
        verbose_name = 'Kategoria'
        verbose_name_plural = 'Kategorie'
        ordering = ['name']
        indexes = [
            models.Index(fields=['category_id']),
            models.Index(fields=['parent']),
            models.Index(fields=['is_filter']),
        ]

    def __str__(self):
        return f"{self.name} ({self.category_id})"


class Product(models.Model):
    """Główny model produktu WEGA"""
    product_id = models.IntegerField(unique=True, db_index=True)
    url = models.URLField(max_length=1000, blank=True, null=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Cena netto produktu"
    )
    gross_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Cena brutto produktu"
    )
    symbol = models.IntegerField(blank=True, null=True)
    is_new = models.BooleanField(
        default=False, help_text="Czy produkt jest nowością")
    is_promotion = models.BooleanField(
        default=False,
        help_text="Czy produkt jest w promocji"
    )
    pcs_in_a_box = models.IntegerField(
        blank=True,
        null=True,
        help_text="Ile sztuk jest w jednym opakowaniu"
    )

    # Podstawowe informacje o produkcie
    name = models.CharField(max_length=255)
    description = models.TextField(
        max_length=1500,
        blank=True,
        null=True,
        help_text="Opis produktu"
    )
    material = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Skład produktu"
    )
    size_chart = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="Link do obrazu z tabelą rozmiarów"
    )

    # Relacje
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text="Kategoria produktu"
    )
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text="Producent/dostawca"
    )

    # Mapowanie do MPD
    mapped_product_uid = models.IntegerField(
        null=True, blank=True, help_text="UID produktu w bazie MPD")
    is_mapped = models.BooleanField(
        default=False, help_text="Czy produkt jest zmapowany do MPD")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_api_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'wega_product'
        verbose_name = 'Produkt'
        verbose_name_plural = 'Produkty'
        indexes = [
            models.Index(fields=['product_id']),
            models.Index(fields=['symbol']),
            models.Index(fields=['category']),
            models.Index(fields=['manufacturer']),
            models.Index(fields=['is_new']),
            models.Index(fields=['is_promotion']),
            models.Index(fields=['is_mapped']),
            models.Index(fields=['mapped_product_uid']),
        ]

    def __str__(self):
        return f"{self.name} ({self.product_id})"


class ProductImage(models.Model):
    """Model dla obrazów produktów WEGA"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    url = models.URLField(max_length=255)
    is_main = models.BooleanField(
        default=False,
        help_text="Czy to główny obraz produktu"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Kolejność wyświetlania"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wega_productimage'
        verbose_name = 'Obraz produktu'
        verbose_name_plural = 'Obrazy produktów'
        ordering = ['-is_main', 'order', 'id']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['is_main']),
        ]

    def __str__(self):
        image_type = "Główny" if self.is_main else "Dodatkowy"
        return f"{image_type} obraz - {self.product.name}"


class ProductAttribute(models.Model):
    """Model dla atrybutów produktu (warianty: rozmiar, kolor, stan magazynowy, EAN)"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='attributes'
    )
    size = models.CharField(max_length=255, blank=True, null=True)
    color = models.CharField(max_length=255, blank=True, null=True)
    available = models.IntegerField(
        default=0,
        help_text="Liczba reprezentująca stan magazynowy"
    )
    ean = models.CharField(
        max_length=25,
        blank=True,
        null=True,
        db_index=True,
        help_text="Kod EAN produktu"
    )
    color_image_url = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Adres obrazu reprezentujący kolor atrybutu"
    )

    # Mapowanie do MPD
    mapped_variant_uid = models.IntegerField(
        null=True, blank=True, help_text="UID wariantu w bazie MPD")
    is_mapped = models.BooleanField(
        null=True, blank=True, help_text="Czy wariant jest zmapowany do MPD")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wega_productattribute'
        verbose_name = 'Atrybut produktu'
        verbose_name_plural = 'Atrybuty produktów'
        ordering = ['product', 'size', 'color']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['ean']),
            models.Index(fields=['size']),
            models.Index(fields=['color']),
            models.Index(fields=['is_mapped']),
            models.Index(fields=['mapped_variant_uid']),
        ]

    def __str__(self):
        attrs = []
        if self.size:
            attrs.append(f"Rozmiar: {self.size}")
        if self.color:
            attrs.append(f"Kolor: {self.color}")
        if self.ean:
            attrs.append(f"EAN: {self.ean}")
        attrs_str = ", ".join(attrs) if attrs else "Bez atrybutów"
        return f"{self.product.name} - {attrs_str}"


class Promotion(models.Model):
    """Model dla promocji produktu WEGA (opcjonalne)"""
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='promotion',
        null=True,
        blank=True
    )
    start_date = models.DateTimeField(help_text="Data rozpoczęcia promocji")
    end_date = models.DateTimeField(help_text="Data zakończenia promocji")
    value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Wartość procentowa promocji"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wega_promotion'
        verbose_name = 'Promocja'
        verbose_name_plural = 'Promocje'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"Promocja {self.value}% - {self.product.name if self.product else 'Brak produktu'}"


class New(models.Model):
    """Model dla nowości produktu WEGA (opcjonalne)"""
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='new_product',
        null=True,
        blank=True
    )
    start_date = models.DateTimeField(help_text="Data rozpoczęcia nowości")
    end_date = models.DateTimeField(help_text="Data zakończenia nowości")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wega_new'
        verbose_name = 'Nowość'
        verbose_name_plural = 'Nowości'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"Nowość - {self.product.name if self.product else 'Brak produktu'}"


class RelatedProduct(models.Model):
    """Model dla powiązanych produktów WEGA"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='related_products'
    )
    related_product_id = models.IntegerField(
        help_text="ID produktu powiązanego"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wega_relatedproduct'
        verbose_name = 'Powiązany produkt'
        verbose_name_plural = 'Powiązane produkty'
        ordering = ['product', 'related_product_id']
        unique_together = [['product', 'related_product_id']]
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['related_product_id']),
        ]

    def __str__(self):
        return f"{self.product.name} -> Produkt {self.related_product_id}"
