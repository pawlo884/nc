from django.db import models
from django.utils import timezone


class AutomationRun(models.Model):
    """Log operacji automatyzacji wypełniania formularzy MPD"""
    
    STATUS_CHOICES = [
        ('pending', 'Oczekuje'),
        ('running', 'W trakcie'),
        ('completed', 'Zakończone'),
        ('failed', 'Błąd'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Rozpoczęto')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Zakończono')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    products_processed = models.IntegerField(default=0, verbose_name='Przetworzono produktów')
    products_success = models.IntegerField(default=0, verbose_name='Sukces')
    products_failed = models.IntegerField(default=0, verbose_name='Błędy')
    error_message = models.TextField(blank=True, null=True, verbose_name='Komunikat błędu')
    brand_id = models.IntegerField(null=True, blank=True, verbose_name='ID marki')
    category_id = models.IntegerField(null=True, blank=True, verbose_name='ID kategorii')
    filters = models.JSONField(default=dict, blank=True, verbose_name='Filtry')
    
    class Meta:
        db_table = 'automation_run'
        verbose_name = 'Uruchomienie automatyzacji'
        verbose_name_plural = 'Uruchomienia automatyzacji'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"AutomationRun #{self.id} - {self.status} ({self.started_at})"
    
    @property
    def duration(self):
        """Oblicza czas trwania operacji"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None


class ProductProcessingLog(models.Model):
    """Log przetwarzania pojedynczego produktu"""
    
    STATUS_CHOICES = [
        ('pending', 'Oczekuje'),
        ('processing', 'Przetwarzanie'),
        ('success', 'Sukces'),
        ('failed', 'Błąd'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    automation_run = models.ForeignKey(
        AutomationRun,
        on_delete=models.CASCADE,
        related_name='product_logs',
        verbose_name='Uruchomienie automatyzacji'
    )
    product_id = models.IntegerField(verbose_name='ID produktu')
    product_name = models.CharField(max_length=500, blank=True, verbose_name='Nazwa produktu')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    mpd_product_id = models.IntegerField(null=True, blank=True, verbose_name='ID produktu w MPD')
    error_message = models.TextField(blank=True, null=True, verbose_name='Komunikat błędu')
    processed_at = models.DateTimeField(auto_now_add=True, verbose_name='Przetworzono')
    processing_data = models.JSONField(default=dict, blank=True, verbose_name='Dane przetwarzania')
    
    class Meta:
        db_table = 'product_processing_log'
        verbose_name = 'Log przetwarzania produktu'
        verbose_name_plural = 'Logi przetwarzania produktów'
        ordering = ['-processed_at']
        indexes = [
            models.Index(fields=['automation_run', 'status']),
            models.Index(fields=['product_id']),
        ]
    
    def __str__(self):
        return f"ProductLog #{self.id} - Product {self.product_id} - {self.status}"
