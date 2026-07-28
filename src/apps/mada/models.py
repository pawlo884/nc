from django.db import models

from core.saga_models import AbstractSaga, AbstractSagaStep


class Brand(models.Model):
    """Model dla marek produktów z feedu Mada (PRODUCERS/PRODUCER)."""
    producer_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mada_brand'
        verbose_name = 'Marka'
        verbose_name_plural = 'Marki'
        indexes = [
            models.Index(fields=['producer_id'], name='mada_brand_producer_id_idx'),
            models.Index(fields=['name'], name='mada_brand_name_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.producer_id})"


class Category(models.Model):
    """Model dla kategorii produktów z feedu Mada (CATEGORIES/CATEGORY, atrybuty c1/c2)."""
    category_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=300)
    path = models.CharField(max_length=500, blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mada_category'
        verbose_name = 'Kategoria'
        verbose_name_plural = 'Kategorie'
        indexes = [
            models.Index(fields=['category_id'], name='mada_category_category_id_idx'),
            models.Index(fields=['name'], name='mada_category_name_idx'),
            models.Index(fields=['parent'], name='mada_category_parent_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.category_id})"


class ApiSyncLog(models.Model):
    """Log synchronizacji z API Mada (import pełny/partial)."""
    STATUS_CHOICES = [
        ('pending', 'Oczekuje'),
        ('running', 'W trakcie'),
        ('completed', 'Zakończone'),
        ('failed', 'Błąd'),
    ]
    SYNC_TYPE_CHOICES = [
        ('full_import', 'Import pełny'),
        ('partial_import', 'Import przyrostowy'),
    ]

    sync_type = models.CharField(max_length=50, choices=SYNC_TYPE_CHOICES, db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    file_name = models.CharField(
        max_length=100, blank=True,
        help_text="Nazwa pliku z manifestu Mada (np. 2026-07-28-full lub 2026-07-28_114003)")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    products_processed = models.IntegerField(default=0)
    products_created = models.IntegerField(default=0)
    products_updated = models.IntegerField(default=0)
    products_failed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'mada_apisynclog'
        verbose_name = 'Log synchronizacji API'
        verbose_name_plural = 'Logi synchronizacji API'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['sync_type'], name='mada_asl_sync_type_idx'),
            models.Index(fields=['status'], name='mada_asl_status_idx'),
            models.Index(fields=['started_at'], name='mada_asl_started_idx'),
            models.Index(fields=['file_name'], name='mada_asl_file_name_idx'),
        ]

    def __str__(self):
        return f"{self.sync_type} - {self.status} ({self.started_at})"


class MadaProduct(models.Model):
    """
    Produkt z feedu Mada (products.xml / PRODUCT).
    """
    api_id = models.IntegerField(unique=True, db_index=True, help_text="Pole 'ID' produktu z feedu Mada")

    name = models.CharField(max_length=500)
    desc = models.TextField(blank=True, null=True)

    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='mada_products', db_column='mada_brand_fk_id',
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='mada_products', db_column='mada_category_fk_id',
    )

    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vat = models.DecimalField(max_digits=5, decimal_places=2, default=23)

    # Reszta danych z API (FLAGS, SIMILAR_PRODUCTS, PRODUCER_ADDRESS,
    # PRODUCER_SECURITY_INFO, ATTRIBUTES) - nie warto rozbijać na osobne
    # modele przy pierwszej wersji, feed i tak trzeba re-parsować co import.
    raw_data = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(
        default=True, db_index=True,
        help_text="False gdy produkt zniknął z ostatniego pełnego importu (wygaszony)")

    # Mapowanie do MPD
    mapped_product_uid = models.IntegerField(
        null=True, blank=True, db_index=True,
        help_text='ID produktu w bazie MPD',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_api_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'mada_product'
        verbose_name = 'Produkt'
        verbose_name_plural = 'Produkty'
        ordering = ['-api_id']
        indexes = [
            models.Index(fields=['api_id']),
            models.Index(fields=['brand']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['mapped_product_uid']),
        ]

    def __str__(self) -> str:
        return f"{self.name} [Mada #{self.api_id}]"


class MadaProductImage(models.Model):
    """Zdjęcia produktu (IMAGES/IMG)."""
    product = models.ForeignKey(
        MadaProduct, on_delete=models.CASCADE, related_name='images')
    api_image_id = models.CharField(max_length=50, db_index=True, help_text="atrybut id z IMG")
    image_url = models.URLField(max_length=1000)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'mada_product_image'
        verbose_name = 'Obraz produktu'
        verbose_name_plural = 'Obrazy produktów'
        ordering = ['order', 'api_image_id']
        unique_together = [['product', 'api_image_id']]
        indexes = [
            models.Index(fields=['product']),
        ]

    def __str__(self) -> str:
        return f"#{self.api_image_id} - {self.product.name}"


class MadaProductVariant(models.Model):
    """
    Wariant produktu (MODELS/MODEL/SIZE) - kolor + rozmiar, EAN, stan.

    Feed Mada nie nadaje wariantom osobnego numerycznego id, dlatego
    variant_key jest kluczem stabilnym w obrębie produktu: EAN gdy dostępny,
    w przeciwnym razie "color|size".
    """
    product = models.ForeignKey(
        MadaProduct, on_delete=models.CASCADE, related_name='variants')

    variant_key = models.CharField(max_length=255, db_index=True)
    color = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=50, blank=True)
    ean = models.CharField(max_length=50, blank=True, db_index=True)
    stock = models.IntegerField(default=0)

    # Mapowanie do MPD (wzorzec jak Matterhorn/Tabu)
    mapped_variant_uid = models.IntegerField(
        null=True, blank=True, db_index=True,
        help_text='ID wariantu w bazie MPD (variant_id)',
    )
    is_mapped = models.BooleanField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mada_product_variant'
        verbose_name = 'Wariant produktu'
        verbose_name_plural = 'Warianty produktów'
        unique_together = [['product', 'variant_key']]
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['ean']),
            models.Index(fields=['variant_key']),
            models.Index(fields=['mapped_variant_uid']),
        ]

    def __str__(self) -> str:
        return f"{self.color}/{self.size} [Mada product #{self.product_id}]"


# Saga Pattern Models — pola współdzielone z matterhorn1/tabu przez core.saga_models
# (AbstractSaga/AbstractSagaStep); logika wykonania/persystencji w core.saga.
class Saga(AbstractSaga):
    """Model do logowania Saga operations (np. tworzenie/mapowanie produktu w MPD)."""

    class Meta:
        db_table = 'mada_saga_logs'
        ordering = ['-created_at']
        verbose_name = 'Saga Log'
        verbose_name_plural = 'Saga Logs'
        app_label = 'mada'


class SagaStep(AbstractSagaStep):
    """Model do logowania poszczególnych kroków Saga"""

    saga = models.ForeignKey(Saga, on_delete=models.CASCADE, related_name='steps')

    class Meta:
        db_table = 'mada_saga_steps'
        ordering = ['saga', 'step_order']
        unique_together = ['saga', 'step_order']
        verbose_name = 'Saga Step'
        verbose_name_plural = 'Saga Steps'
        app_label = 'mada'


class StockHistory(models.Model):
    """Historia zmian stanów magazynowych (wzorzec jak Matterhorn/Tabu)."""
    product_api_id = models.IntegerField(db_index=True, help_text="ID produktu z feedu Mada")
    variant_key = models.CharField(max_length=255, blank=True, null=True)
    product_name = models.CharField(max_length=500, blank=True, null=True)
    variant_label = models.CharField(max_length=150, blank=True, null=True, help_text="kolor/rozmiar")
    old_stock = models.IntegerField(blank=True, null=True)
    new_stock = models.IntegerField(blank=True, null=True)
    stock_change = models.IntegerField(blank=True, null=True)
    change_type = models.CharField(max_length=20, blank=True, null=True)  # 'increase'/'decrease'/'no_change'
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mada_stock_history'
        verbose_name = 'Historia stanów magazynowych'
        verbose_name_plural = 'Historia stanów magazynowych'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['product_api_id'], name='mada_sh_product_idx'),
            models.Index(fields=['variant_key'], name='mada_sh_variant_idx'),
            models.Index(fields=['timestamp'], name='mada_sh_timestamp_idx'),
            models.Index(fields=['change_type'], name='mada_sh_change_idx'),
            models.Index(fields=['product_api_id', 'timestamp'], name='mada_sh_prod_time_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.product_name} - {self.variant_label}: {self.old_stock} → {self.new_stock} ({self.timestamp})"
