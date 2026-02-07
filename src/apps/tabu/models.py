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
        db_table = 'tabu_brand'
        verbose_name = 'Marka'
        verbose_name_plural = 'Marki'
        indexes = [
            models.Index(fields=['brand_id'], name='tabu_brand_brand_id_idx'),
            models.Index(fields=['name'], name='tabu_brand_name_idx'),
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
        db_table = 'tabu_category'
        verbose_name = 'Kategoria'
        verbose_name_plural = 'Kategorie'
        indexes = [
            models.Index(fields=['category_id'],
                         name='tabu_category_category_id_idx'),
            models.Index(fields=['name'], name='tabu_category_name_idx'),
            models.Index(fields=['parent'], name='tabu_category_parent_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.category_id})"


class Product(models.Model):
    """Główny model produktu z API Tabu"""
    # Identyfikatory
    product_id = models.CharField(max_length=50, unique=True, db_index=True)
    external_id = models.CharField(
        max_length=100, blank=True, null=True, db_index=True)

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
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    price_net = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    price_gross = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default='PLN')
    vat_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)

    # URL i linki
    url = models.URLField(max_length=1000, blank=True, null=True)
    slug = models.SlugField(max_length=500, blank=True,
                            null=True, db_index=True)

    # Statusy i flagi
    new_collection = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    on_sale = models.BooleanField(default=False)

    # Pola JSON dla złożonych danych z API
    raw_data = models.JSONField(
        default=dict, blank=True, help_text="Pełne dane z API")
    attributes = models.JSONField(
        default=dict, blank=True, help_text="Atrybuty produktu")
    prices = models.JSONField(default=dict, blank=True,
                              help_text="Ceny w różnych walutach")
    other_colors = models.JSONField(
        default=list, blank=True, help_text="Inne kolory produktu")
    products_in_set = models.JSONField(
        default=list, blank=True, help_text="Produkty w zestawie")

    class Meta:
        db_table = 'tabu_product'
        verbose_name = 'Produkt'
        verbose_name_plural = 'Produkty'
        indexes = [
            models.Index(fields=['product_id'], name='tabu_prod_pid_idx'),
            models.Index(fields=['active'], name='tabu_prod_active_idx'),
            models.Index(fields=['brand'], name='tabu_prod_brand_idx'),
            models.Index(fields=['category'], name='tabu_prod_category_idx'),
            models.Index(fields=['slug'], name='tabu_prod_slug_idx'),
            models.Index(fields=['external_id'], name='tabu_prod_ext_id_idx'),
            models.Index(fields=['created_at'], name='tabu_prod_created_idx'),
            models.Index(fields=['last_api_sync'],
                         name='tabu_prod_last_sync_idx'),
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
        db_table = 'tabu_productimage'
        verbose_name = 'Obraz produktu'
        verbose_name_plural = 'Obrazy produktów'
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['product', 'order'],
                         name='tabu_pimg_prod_ord_idx'),
            models.Index(fields=['is_main'], name='tabu_pimg_is_main_idx'),
        ]
        unique_together = [['product', 'image_url']]

    def __str__(self):
        return f"Obraz {self.order} - {self.product.name}"


class ProductVariant(models.Model):
    """Model dla wariantów produktów (rozmiary, kolory)"""
    variant_id = models.CharField(max_length=50, unique=True, db_index=True)
    external_id = models.CharField(
        max_length=100, blank=True, null=True, db_index=True)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='variants')

    # Informacje o wariancie
    name = models.CharField(max_length=200, blank=True, null=True)
    sku = models.CharField(max_length=100, blank=True,
                           null=True, db_index=True)
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
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    price_net = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    price_gross = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)

    # Czas realizacji
    max_processing_time = models.PositiveIntegerField(
        default=0, help_text="Czas realizacji w dniach")

    # Pola JSON
    raw_data = models.JSONField(
        default=dict, blank=True, help_text="Pełne dane z API")
    attributes = models.JSONField(
        default=dict, blank=True, help_text="Atrybuty wariantu")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_api_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tabu_productvariant'
        verbose_name = 'Wariant produktu'
        verbose_name_plural = 'Warianty produktów'
        indexes = [
            models.Index(fields=['variant_id'],
                         name='tabu_pvar_variant_id_idx'),
            models.Index(fields=['product'], name='tabu_pvar_product_idx'),
            models.Index(fields=['sku'], name='tabu_pvar_sku_idx'),
            models.Index(fields=['ean'], name='tabu_pvar_ean_idx'),
            models.Index(fields=['available'], name='tabu_pvar_available_idx'),
            models.Index(fields=['stock'], name='tabu_pvar_stock_idx'),
            models.Index(fields=['external_id'], name='tabu_pvar_ext_id_idx'),
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
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    products_processed = models.IntegerField(default=0)
    products_success = models.IntegerField(default=0)
    products_failed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    raw_response = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        db_table = 'tabu_apisynclog'
        verbose_name = 'Log synchronizacji API'
        verbose_name_plural = 'Logi synchronizacji API'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['sync_type'], name='tabu_asl_sync_type_idx'),
            models.Index(fields=['status'], name='tabu_asl_status_idx'),
            models.Index(fields=['started_at'], name='tabu_asl_started_idx'),
        ]

    def __str__(self):
        return f"{self.sync_type} - {self.status} ({self.started_at})"


class TabuProduct(models.Model):
    """
    Produkt z API Tabu (bez mieszania z istniejącym modelem Product).
    Oparty bezpośrednio o strukturę odpowiedzi /products.
    """

    # Identyfikatory
    api_id = models.IntegerField(
        unique=True, db_index=True, help_text="Pole 'id' z API Tabu")
    symbol = models.CharField(max_length=100, db_index=True)
    ean = models.CharField(max_length=50, blank=True, db_index=True)

    # Podstawowe informacje
    name = models.CharField(max_length=500)
    desc_short = models.TextField(blank=True, null=True)

    # Kategoria (z JSON: category, category_id)
    category_path = models.CharField(
        max_length=500,
        help_text="Ścieżka kategorii z API, np. 'Dla niej > Skarpetki > Stopki'",
    )
    category_id = models.IntegerField(db_index=True)

    # Producent
    producer_name = models.CharField(max_length=200)
    producer_id = models.IntegerField(db_index=True)
    producer_code = models.CharField(max_length=100, blank=True)

    # Obraz
    image_url = models.URLField(max_length=1000, blank=True)

    # Ceny / VAT
    price_net = models.DecimalField(max_digits=10, decimal_places=2)
    price_gross = models.DecimalField(max_digits=10, decimal_places=2)
    price_old = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_kind = models.PositiveSmallIntegerField(
        default=1,
        help_text="1 - cena netto, 2 - cena brutto (zgodnie z dokumentacją API)",
    )

    vat_label = models.CharField(
        max_length=20, help_text="Etykieta VAT, np. '23%'")
    vat_id = models.IntegerField()
    vat_value = models.DecimalField(max_digits=5, decimal_places=2)

    # Stan / jednostka
    store_total = models.IntegerField(
        help_text="Łączny stan magazynowy 'store'")
    unit_label = models.CharField(
        max_length=50, help_text="Nazwa jednostki, np. 'par', 'szt'")
    unit_id = models.IntegerField()
    weight = models.DecimalField(max_digits=8, decimal_places=3, default=0)

    # Status / dostępność
    status_label = models.CharField(max_length=50)
    status_id = models.IntegerField()
    status_auto = models.BooleanField(default=True)

    # Dane www / inne
    url = models.URLField(max_length=1000)
    version_signature = models.CharField(max_length=100, blank=True)
    preorder = models.CharField(max_length=50, blank=True)
    hidden_search = models.BooleanField(default=False)
    last_update = models.DateTimeField()

    # Promocja (opcjonalnie)
    promo = models.CharField(max_length=100, blank=True)
    promo_uid = models.CharField(max_length=100, blank=True)
    promo_from = models.DateTimeField(null=True, blank=True)
    promo_to = models.DateTimeField(null=True, blank=True)

    # Surowy JSON do przyszłego mapowania
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'tabu_api_product'
        verbose_name = 'Tabu produkt (API)'
        verbose_name_plural = 'Tabu produkty (API)'
        indexes = [
            models.Index(fields=['api_id']),
            models.Index(fields=['symbol']),
            models.Index(fields=['category_id']),
            models.Index(fields=['producer_id']),
        ]

    def __str__(self) -> str:
        return f"{self.name} [Tabu #{self.api_id}]"


class TabuProductVariant(models.Model):
    """
    Wariant produktu z API Tabu (pole 'variants' w odpowiedzi).
    Powiązany z TabuProduct, bez mieszania z istniejącym ProductVariant.
    """

    api_id = models.IntegerField(
        unique=True, db_index=True, help_text="Pole 'id' wariantu z API")
    product = models.ForeignKey(
        TabuProduct,
        on_delete=models.CASCADE,
        related_name='api_variants',
    )

    symbol = models.CharField(max_length=120, db_index=True)
    ean = models.CharField(max_length=50, blank=True, db_index=True)

    price_net = models.DecimalField(max_digits=10, decimal_places=2)
    price_gross = models.DecimalField(max_digits=10, decimal_places=2)
    price_kind = models.PositiveSmallIntegerField(default=1)

    vat_label = models.CharField(max_length=20)
    vat_id = models.IntegerField()
    vat_value = models.DecimalField(max_digits=5, decimal_places=2)

    store = models.IntegerField(db_index=True)
    weight = models.DecimalField(max_digits=8, decimal_places=3, default=0)

    # Wyciągnięte z items (dla wygodnego filtrowania)
    color = models.CharField(max_length=100, blank=True,
                             help_text="Wartość parametru 'Kolor'")
    size = models.CharField(max_length=50, blank=True,
                            help_text="Wartość parametru 'Rozmiar'")

    # Pełna struktura items z API (lista parametrów wariantu)
    items = models.JSONField(default=list, blank=True)

    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'tabu_api_variant'
        verbose_name = 'Tabu wariant (API)'
        verbose_name_plural = 'Tabu warianty (API)'
        indexes = [
            models.Index(fields=['api_id']),
            models.Index(fields=['product']),
            models.Index(fields=['ean']),
            models.Index(fields=['store']),
        ]

    def __str__(self) -> str:
        return f"{self.symbol} [Tabu variant #{self.api_id}]"
