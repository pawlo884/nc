from django.db import models


class Brand(models.Model):
    """Model dla marek produktów z API Tabu"""
    brand_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    logo_url = models.URLField(max_length=1000, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_api_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'brand'
        verbose_name = 'Marka'
        verbose_name_plural = 'Marki'
        indexes = [
            models.Index(fields=['brand_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.brand_id})"


class Category(models.Model):
    """Model dla kategorii produktów z API Tabu"""
    category_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    path = models.CharField(max_length=500, blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_api_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'category'
        verbose_name = 'Kategoria'
        verbose_name_plural = 'Kategorie'
        indexes = [
            models.Index(fields=['category_id']),
            models.Index(fields=['name']),
            models.Index(fields=['parent']),
        ]

    def __str__(self):
        return f"{self.name} ({self.category_id})"


class Product(models.Model):
    """Główny model produktu z API Tabu"""
    # Identyfikatory
    product_id = models.CharField(max_length=50, unique=True, db_index=True)
    external_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    
    # Podstawowe informacje
    active = models.BooleanField(default=True, db_index=True)
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=500, blank=True, null=True)
    
    # Daty
    creation_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_api_sync = models.DateTimeField(null=True, blank=True)
    
    # Relacje
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    # Ceny i dostępność
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_net = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_gross = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default='PLN')
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # URL i linki
    url = models.URLField(max_length=1000, blank=True, null=True)
    slug = models.SlugField(max_length=500, blank=True, null=True, db_index=True)
    
    # Statusy i flagi
    new_collection = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    on_sale = models.BooleanField(default=False)
    
    # Pola JSON dla złożonych danych z API
    raw_data = models.JSONField(default=dict, blank=True, help_text="Pełne dane z API")
    attributes = models.JSONField(default=dict, blank=True, help_text="Atrybuty produktu")
    prices = models.JSONField(default=dict, blank=True, help_text="Ceny w różnych walutach")
    other_colors = models.JSONField(default=list, blank=True, help_text="Inne kolory produktu")
    products_in_set = models.JSONField(default=list, blank=True, help_text="Produkty w zestawie")
    
    class Meta:
        db_table = 'product'
        verbose_name = 'Produkt'
        verbose_name_plural = 'Produkty'
        indexes = [
            models.Index(fields=['product_id']),
            models.Index(fields=['active']),
            models.Index(fields=['brand']),
            models.Index(fields=['category']),
            models.Index(fields=['slug']),
            models.Index(fields=['external_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['last_api_sync']),
        ]

    def __str__(self):
        return f"{self.name} ({self.product_id})"

    @property
    def stock_total(self):
        """Oblicza całkowity stan magazynowy z wariantów"""
        return sum(variant.stock for variant in self.variants.all())


class ProductImage(models.Model):
    """Model dla obrazów produktów"""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField(max_length=1000)
    thumbnail_url = models.URLField(max_length=1000, blank=True, null=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    alt_text = models.CharField(max_length=500, blank=True, null=True)
    is_main = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'productimage'
        verbose_name = 'Obraz produktu'
        verbose_name_plural = 'Obrazy produktów'
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['product', 'order']),
            models.Index(fields=['is_main']),
        ]
        unique_together = [['product', 'image_url']]

    def __str__(self):
        return f"Obraz {self.order} - {self.product.name}"


class ProductVariant(models.Model):
    """Model dla wariantów produktów (rozmiary, kolory)"""
    variant_id = models.CharField(max_length=50, unique=True, db_index=True)
    external_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='variants')
    
    # Informacje o wariancie
    name = models.CharField(max_length=200, blank=True, null=True)
    sku = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    ean = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    
    # Rozmiar i kolor
    size = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=100, blank=True, null=True)
    color_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Stan magazynowy
    stock = models.PositiveIntegerField(default=0, db_index=True)
    stock_reserved = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True, db_index=True)
    
    # Ceny wariantu
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_net = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_gross = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Czas realizacji
    max_processing_time = models.PositiveIntegerField(default=0, help_text="Czas realizacji w dniach")
    
    # Pola JSON
    raw_data = models.JSONField(default=dict, blank=True, help_text="Pełne dane z API")
    attributes = models.JSONField(default=dict, blank=True, help_text="Atrybuty wariantu")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_api_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'productvariant'
        verbose_name = 'Wariant produktu'
        verbose_name_plural = 'Warianty produktów'
        indexes = [
            models.Index(fields=['variant_id']),
            models.Index(fields=['product']),
            models.Index(fields=['sku']),
            models.Index(fields=['ean']),
            models.Index(fields=['available']),
            models.Index(fields=['stock']),
            models.Index(fields=['external_id']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name or self.size} ({self.variant_id})"


class ApiSyncLog(models.Model):
    """Model do logowania synchronizacji z API Tabu"""
    STATUS_CHOICES = [
        ('pending', 'Oczekuje'),
        ('running', 'W trakcie'),
        ('completed', 'Zakończone'),
        ('failed', 'Błąd'),
    ]
    
    sync_type = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    products_processed = models.IntegerField(default=0)
    products_success = models.IntegerField(default=0)
    products_failed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    raw_response = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        db_table = 'apisynclog'
        verbose_name = 'Log synchronizacji API'
        verbose_name_plural = 'Logi synchronizacji API'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['sync_type']),
            models.Index(fields=['status']),
            models.Index(fields=['started_at']),
        ]

    def __str__(self):
        return f"{self.sync_type} - {self.status} ({self.started_at})"
