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
    Produkt z API Tabu – pełne dane z GET products/{id}.
    Zawiera: desc_long, desc_safety, gallery, groups, dictionaries, variants.
    """

    # Identyfikatory
    api_id = models.IntegerField(
        unique=True, db_index=True, help_text="Pole 'id' z API Tabu")
    symbol = models.CharField(max_length=100, db_index=True)
    ean = models.CharField(max_length=50, blank=True, db_index=True)

    # Podstawowe informacje
    name = models.CharField(max_length=500)
    desc_short = models.TextField(blank=True, null=True)
    desc_long = models.TextField(blank=True, null=True, help_text="Opis długi HTML")
    desc_safety = models.TextField(blank=True, null=True, help_text="Informacje bezpieczeństwa")

    # Relacje
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tabu_products',
        db_column='tabu_category_fk_id',
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tabu_products',
        db_column='tabu_brand_fk_id',
    )

    # Backup z API (bez relacji)
    category_path = models.CharField(max_length=500, blank=True)
    api_category_id = models.IntegerField(db_index=True, default=0)
    producer_name = models.CharField(max_length=200, blank=True)
    api_producer_id = models.IntegerField(db_index=True, default=0)
    producer_code = models.CharField(max_length=100, blank=True)

    # Obrazy – główny + gallery (TabuProductImage)
    image_url = models.URLField(max_length=1000, blank=True, help_text="Obraz główny")

    # Ceny / VAT
    price_net = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_gross = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_old = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_kind = models.PositiveSmallIntegerField(default=1)
    vat_label = models.CharField(max_length=20, default='23%')
    vat_id = models.IntegerField(default=1)
    vat_value = models.DecimalField(max_digits=5, decimal_places=2, default=23)

    # Stan / jednostka
    store_total = models.IntegerField(default=0)
    unit_label = models.CharField(max_length=50, default='szt')
    unit_id = models.IntegerField(default=1)
    weight = models.DecimalField(max_digits=8, decimal_places=3, default=0)

    # Dostawy
    shipment = models.CharField(max_length=200, blank=True)
    shipment_id = models.CharField(max_length=50, blank=True)
    shipment_days = models.CharField(max_length=50, blank=True)

    # Status
    status_label = models.CharField(max_length=50, default='')
    status_id = models.IntegerField(default=1)
    status_auto = models.BooleanField(default=True)

    # Dane www
    url = models.URLField(max_length=1000, default='https://tabu.com.pl/')
    version_signature = models.CharField(max_length=100, blank=True)
    preorder = models.CharField(max_length=50, blank=True)
    hidden_search = models.BooleanField(default=False)
    last_update = models.DateTimeField()

    # Promocja
    promo = models.CharField(max_length=100, blank=True)
    promo_uid = models.CharField(max_length=100, blank=True)
    promo_from = models.DateTimeField(null=True, blank=True)
    promo_to = models.DateTimeField(null=True, blank=True)

    # Z API: groups (np. skarpety, wielka-promocja), dictionaries (Kolor, Rozmiar, Materiał...)
    groups = models.JSONField(default=list, blank=True)
    dictionaries = models.JSONField(default=list, blank=True, help_text="Atrybuty: Kolor, Rozmiar, Materiał...")
    stores = models.JSONField(default=list, blank=True, help_text="[{id, store}]")

    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'tabu_product_detail'
        verbose_name = 'Tabu produkt (szczegóły)'
        verbose_name_plural = 'Tabu produkty (szczegóły)'
        ordering = ['-api_id']
        indexes = [
            models.Index(fields=['api_id']),
            models.Index(fields=['symbol']),
            models.Index(fields=['api_category_id']),
            models.Index(fields=['api_producer_id']),
            models.Index(fields=['brand']),
            models.Index(fields=['category']),
        ]

    def __str__(self) -> str:
        return f"{self.name} [Tabu #{self.api_id}]"


class TabuProductImage(models.Model):
    """Obrazy z gallery – zdjęcia produktu w tym zdjęcia kolorów."""
    product = models.ForeignKey(
        TabuProduct,
        on_delete=models.CASCADE,
        related_name='gallery_images',
    )
    api_image_id = models.IntegerField(db_index=True, help_text="id z gallery[]")
    image_url = models.URLField(max_length=1000)
    is_main = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'tabu_product_gallery'
        verbose_name = 'Zdjęcie produktu Tabu'
        verbose_name_plural = 'Zdjęcia produktów Tabu'
        ordering = ['order', 'api_image_id']
        unique_together = [['product', 'api_image_id']]
        indexes = [
            models.Index(fields=['product']),
        ]

    def __str__(self) -> str:
        return f"#{self.api_image_id} - {self.product.name}"


class TabuProductVariant(models.Model):
    """Wariant produktu – rozmiar/kolor, stany magazynowe, ceny."""

    api_id = models.IntegerField(
        unique=True, db_index=True, help_text="Pole 'id' wariantu z API")
    product = models.ForeignKey(
        TabuProduct,
        on_delete=models.CASCADE,
        related_name='api_variants',
    )

    symbol = models.CharField(max_length=120, db_index=True)
    ean = models.CharField(max_length=50, blank=True, db_index=True)

    price_net = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_gross = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_kind = models.PositiveSmallIntegerField(default=1)
    vat_label = models.CharField(max_length=20, default='23%')
    vat_id = models.IntegerField(default=1)
    vat_value = models.DecimalField(max_digits=5, decimal_places=2, default=23)

    store = models.IntegerField(db_index=True, default=0)
    weight = models.DecimalField(max_digits=8, decimal_places=3, default=0)

    color = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=50, blank=True)
    items = models.JSONField(default=list, blank=True, help_text="Parametry: Kolor, Rozmiar...")
    stores = models.JSONField(default=list, blank=True, help_text="[{id, store}]")

    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'tabu_product_variant'
        verbose_name = 'Tabu wariant (API)'
        verbose_name_plural = 'Tabu warianty (API)'
        indexes = [
            models.Index(fields=['api_id']),
            models.Index(fields=['product']),
            models.Index(fields=['ean']),
            models.Index(fields=['store']),
        ]

    def __str__(self) -> str:
        return f"{self.symbol} [Tabu #{self.api_id}]"


class StockHistory(models.Model):
    """Model do śledzenia historii zmian stanów magazynowych (jak w Matterhorn)."""
    variant_api_id = models.IntegerField(db_index=True, help_text="ID wariantu z API Tabu")
    product_api_id = models.IntegerField(db_index=True, help_text="ID produktu z API Tabu")
    product_name = models.CharField(max_length=500, blank=True, null=True)
    variant_symbol = models.CharField(max_length=120, blank=True, null=True)
    old_stock = models.PositiveIntegerField(blank=True, null=True)
    new_stock = models.PositiveIntegerField(blank=True, null=True)
    stock_change = models.IntegerField(blank=True, null=True)  # new_stock - old_stock
    change_type = models.CharField(
        max_length=20, blank=True, null=True
    )  # 'increase', 'decrease', 'no_change'
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tabu_stock_history'
        verbose_name = 'Historia stanów magazynowych'
        verbose_name_plural = 'Historia stanów magazynowych'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['variant_api_id'], name='tabu_sh_variant_idx'),
            models.Index(fields=['product_api_id'], name='tabu_sh_product_idx'),
            models.Index(fields=['timestamp'], name='tabu_sh_timestamp_idx'),
            models.Index(fields=['change_type'], name='tabu_sh_change_idx'),
            models.Index(fields=['product_api_id', 'timestamp'], name='tabu_sh_prod_time_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.product_name} - {self.variant_symbol}: {self.old_stock} → {self.new_stock} ({self.timestamp})"
