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
    product_uid = models.IntegerField(unique=True, db_index=True)
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
    mapped_product_uid = models.IntegerField(
        null=True, blank=True, help_text="UID produktu w bazie MPD")
    is_mapped = models.BooleanField(
        default=False, help_text="Czy produkt jest zmapowany do MPD")
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_api_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'product'
        verbose_name = 'Produkt'
        verbose_name_plural = 'Produkty'
        indexes = [
            models.Index(fields=['product_uid']),
            models.Index(fields=['active']),
            models.Index(fields=['brand']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} ({self.product_uid})"

    @property
    def stock_total(self):
        """Oblicza całkowity stan magazynowy z wariantów"""
        return sum(variant.stock for variant in self.variants.all())

    def get_absolute_url(self):
        """Zwraca URL do szczegółów produktu w admin"""
        from django.urls import reverse
        return reverse('admin:matterhorn1_product_change', args=[self.pk])


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
    image_url = models.CharField(max_length=1000)
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

    # Mapowanie do MPD
    mapped_variant_uid = models.IntegerField(
        null=True, blank=True, help_text="UID wariantu w bazie MPD")
    is_mapped = models.BooleanField(
        null=True, blank=True, help_text="Czy wariant jest zmapowany do MPD")

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
            models.Index(fields=['is_mapped']),
            models.Index(fields=['mapped_variant_uid']),
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


# Saga Pattern Models
class SagaStatus(models.TextChoices):
    """Statusy Saga"""
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    COMPENSATING = "compensating", "Compensating"
    COMPENSATED = "compensated", "Compensated"


class Saga(models.Model):
    """Model do logowania Saga operations"""

    saga_id = models.CharField(max_length=100, unique=True, db_index=True)
    # np. 'product_creation', 'variant_creation'
    saga_type = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=SagaStatus.choices, default=SagaStatus.PENDING)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)

    # Stats
    total_steps = models.IntegerField(default=0)
    completed_steps = models.IntegerField(default=0)
    failed_step = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'saga_logs'
        ordering = ['-created_at']
        verbose_name = 'Saga Log'
        verbose_name_plural = 'Saga Logs'
        app_label = 'matterhorn1'

    def __str__(self):
        return f"Saga {self.saga_id} ({self.saga_type}) - {self.status}"


class SagaStep(models.Model):
    """Model do logowania poszczególnych kroków Saga"""

    saga = models.ForeignKey(
        Saga, on_delete=models.CASCADE, related_name='steps')
    step_name = models.CharField(max_length=100)
    step_order = models.IntegerField()

    # Status i timestamps
    status = models.CharField(
        max_length=20, choices=SagaStatus.choices, default=SagaStatus.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    compensated_at = models.DateTimeField(null=True, blank=True)

    # Data
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)

    # Compensation
    compensation_attempted = models.BooleanField(default=False)
    compensation_successful = models.BooleanField(default=False)

    class Meta:
        db_table = 'saga_steps'
        ordering = ['saga', 'step_order']
        unique_together = ['saga', 'step_order']
        verbose_name = 'Saga Step'
        verbose_name_plural = 'Saga Steps'
        app_label = 'matterhorn1'

    def __str__(self):
        return f"{self.saga.saga_id} - Step {self.step_order}: {self.step_name} ({self.status})"


class StockHistory(models.Model):
    """Model do śledzenia historii zmian stanów magazynowych"""
    id = models.AutoField(primary_key=True)
    variant_uid = models.CharField(max_length=50, db_index=True)
    product_uid = models.IntegerField(
        db_index=True, help_text="ID produktu z API Matterhorn")
    product_name = models.CharField(max_length=500, blank=True, null=True)
    variant_name = models.CharField(max_length=50, blank=True, null=True)
    old_stock = models.PositiveIntegerField(blank=True, null=True)
    new_stock = models.PositiveIntegerField(blank=True, null=True)
    stock_change = models.IntegerField(
        blank=True, null=True)  # new_stock - old_stock
    # 'increase', 'decrease', 'no_change'
    change_type = models.CharField(max_length=20, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matterhorn1_stock_history'  # Unikalna nazwa tabeli dla matterhorn1
        app_label = 'matterhorn1'
        verbose_name = 'Historia stanów magazynowych'
        verbose_name_plural = 'Historia stanów magazynowych'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['variant_uid'], name='mh1_sh_variant_idx'),
            models.Index(fields=['product_uid'], name='mh1_sh_product_idx'),
            models.Index(fields=['timestamp'], name='mh1_sh_timestamp_idx'),
            models.Index(fields=['change_type'], name='mh1_sh_change_idx'),
            models.Index(fields=['product_uid', 'timestamp'],
                         name='mh1_sh_prod_time_idx'),
        ]

    def __str__(self):
        return f"{self.product_name} - {self.variant_name}: {self.old_stock} → {self.new_stock} ({self.timestamp})"

    def get_product_url(self):
        """Zwraca URL do produktu w admin na podstawie product_uid"""
        from django.urls import reverse
        try:
            # Znajdź produkt po product_uid
            from .models import Product
            product = Product.objects.using('matterhorn1').get(
                product_uid=self.product_uid)
            return reverse('admin:matterhorn1_product_change', args=[product.pk])
        except Product.DoesNotExist:
            return None
