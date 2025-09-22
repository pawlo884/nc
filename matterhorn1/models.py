from django.db import models


class Brand(models.Model):
    """Model dla marek produktów"""
    brand_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'brand'
        verbose_name = 'Marka'
        verbose_name_plural = 'Marki'

    def __str__(self):
        return f"{self.name} ({self.brand_id})"


class Category(models.Model):
    """Model dla kategorii produktów"""
    category_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'category'
        verbose_name = 'Kategoria'
        verbose_name_plural = 'Kategorie'

    def __str__(self):
        return f"{self.name} ({self.category_id})"


class Product(models.Model):
    """Główny model produktu - tylko najważniejsze pola"""
    product_id = models.IntegerField(unique=True, db_index=True)
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    creation_date = models.DateTimeField(null=True, blank=True)
    color = models.CharField(max_length=100, blank=True)
    url = models.URLField(max_length=1000, blank=True)
    new_collection = models.BooleanField(default=False)

    # Relacje
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, null=True, blank=True)
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, null=True, blank=True)

    # Pola JSON dla złożonych danych
    products_in_set = models.JSONField(default=list, blank=True)
    other_colors = models.JSONField(default=list, blank=True)
    prices = models.JSONField(default=dict, blank=True)

    # Mapowanie do MPD
    mapped_product_id = models.IntegerField(
        null=True, blank=True, help_text="ID produktu w bazie MPD")
    is_mapped = models.BooleanField(default=False, help_text="Czy produkt jest zmapowany do MPD")
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_api_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'product'
        verbose_name = 'Produkt'
        verbose_name_plural = 'Produkty'
        indexes = [
            models.Index(fields=['product_id']),
            models.Index(fields=['active']),
            models.Index(fields=['brand']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} ({self.product_id})"

    @property
    def stock_total(self):
        """Oblicza całkowity stan magazynowy z wariantów"""
        return sum(variant.stock for variant in self.variants.all())


class ProductDetails(models.Model):
    """Szczegóły techniczne produktu - rzadko używane pola"""
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='details')
    weight = models.CharField(max_length=20, blank=True, null=True)
    size_table = models.TextField(blank=True, null=True)
    size_table_txt = models.TextField(blank=True, null=True)
    size_table_html = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'productdetails'
        verbose_name = 'Szczegóły produktu'
        verbose_name_plural = 'Szczegóły produktów'

    def __str__(self):
        return f"Szczegóły - {self.product.name}"


class ProductImage(models.Model):
    """Model dla obrazów produktów"""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField(max_length=1000)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'productimage'
        verbose_name = 'Obraz produktu'
        verbose_name_plural = 'Obrazy produktów'
        ordering = ['order']
        unique_together = [['product', 'image_url']]

    def __str__(self):
        return f"Obraz {self.order} - {self.product.name}"


class ProductVariant(models.Model):
    """Model dla wariantów produktów (rozmiary)"""
    variant_uid = models.CharField(max_length=50, unique=True, db_index=True)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=50)  # rozmiar
    stock = models.PositiveIntegerField(default=0)
    max_processing_time = models.PositiveIntegerField(default=0)
    ean = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'productvariant'
        verbose_name = 'Wariant produktu'
        verbose_name_plural = 'Warianty produktów'
        indexes = [
            models.Index(fields=['variant_uid']),
            models.Index(fields=['product']),
            models.Index(fields=['ean']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name} ({self.variant_uid})"


class ApiSyncLog(models.Model):
    """Model do logowania synchronizacji z API"""
    sync_type = models.CharField(
        max_length=50)  # 'products', 'variants', 'bulk_update'
    status = models.CharField(max_length=20)  # 'success', 'error', 'partial'
    records_processed = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    records_errors = models.PositiveIntegerField(default=0)
    error_details = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    current_page = models.PositiveIntegerField(
        default=1, help_text="Aktualna strona podczas importu")

    class Meta:
        db_table = 'apisynclog'
        verbose_name = 'Log synchronizacji API'
        verbose_name_plural = 'Logi synchronizacji API'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.sync_type} - {self.status} ({self.started_at})"
