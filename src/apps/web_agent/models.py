from django.db import models


class AutomationRun(models.Model):
    """Log operacji automatyzacji wypełniania formularzy MPD"""

    STATUS_CHOICES = [
        ('pending', 'Oczekuje'),
        ('running', 'W trakcie'),
        ('completed', 'Zakończone'),
        ('failed', 'Błąd'),
    ]

    id = models.BigAutoField(primary_key=True)
    started_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Rozpoczęto')
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name='Zakończono')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    products_processed = models.IntegerField(
        default=0, verbose_name='Przetworzono produktów')
    products_success = models.IntegerField(default=0, verbose_name='Sukces')
    products_failed = models.IntegerField(default=0, verbose_name='Błędy')
    error_message = models.TextField(
        blank=True, null=True, verbose_name='Komunikat błędu')
    brand_id = models.IntegerField(
        null=True, blank=True, verbose_name='ID marki')
    category_id = models.IntegerField(
        null=True, blank=True, verbose_name='ID kategorii')
    filters = models.JSONField(default=dict, blank=True, verbose_name='Filtry')
    SOURCE_CHOICES = [
        ('matterhorn1', 'Matterhorn1'),
        ('tabu', 'Tabu'),
    ]
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='matterhorn1',
        verbose_name='Źródło',
        help_text='Źródło produktów: Matterhorn1 (przeglądarka) lub Tabu (backend).'
    )
    logs = models.TextField(
        blank=True, null=True, verbose_name='Logi',
        help_text='Logi automatyzacji w czasie rzeczywistym'
    )

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
    product_name = models.CharField(
        max_length=500, blank=True, verbose_name='Nazwa produktu')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    mpd_product_id = models.IntegerField(
        null=True, blank=True, verbose_name='ID produktu w MPD')
    error_message = models.TextField(
        blank=True, null=True, verbose_name='Komunikat błędu')
    processed_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Przetworzono')
    processing_data = models.JSONField(
        default=dict, blank=True, verbose_name='Dane przetwarzania')

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


class BrandConfig(models.Model):
    """Konfiguracja marki - mapowanie kolorów, domyślne filtry, atrybuty"""

    id = models.BigAutoField(primary_key=True)
    brand_id = models.IntegerField(
        unique=True, db_index=True, verbose_name='ID marki')
    brand_name = models.CharField(max_length=200, verbose_name='Nazwa marki')
    default_active_filter = models.BooleanField(
        null=True, blank=True, verbose_name='Domyślny filtr active')
    default_is_mapped_filter = models.BooleanField(
        null=True, blank=True, verbose_name='Domyślny filtr is_mapped')
    color_mapping = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Mapowanie kolorów producenta',
        help_text='JSON: {"Dark Brown": "Ciemny Brąz", "Beige": "Beż", ...}'
    )
    attributes = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Lista atrybutów do wyszukiwania',
        help_text='Lista atrybutów do wyszukiwania w opisie produktu: ["Bawełna", "Elastan", "Bambus", ...]'
    )
    similarity_threshold = models.FloatField(
        default=0.7,
        verbose_name='Próg podobieństwa',
        help_text='Próg podobieństwa dla wyszukiwania atrybutów (0.0-1.0, domyślnie 0.7)'
    )
    category_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Konfiguracja kategorii',
        help_text='JSON z konfiguracją dla każdej kategorii. Przykład: {"Kostiumy dwuczęściowe": {"path_value": "5", "base_type": "Kostium kąpielowy", "has_top": true}, "Jednoczęściowe": {"path_value": "7", "base_type": "Jednoczęściowy kostium kąpielowy", "has_top": true}, "Figi kąpielowe": {"path_value": "6", "base_type": "Figi kąpielowe", "has_top": false}}'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Utworzono')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='Zaktualizowano')

    class Meta:
        db_table = 'brand_config'
        verbose_name = 'Konfiguracja marki'
        verbose_name_plural = 'Konfiguracje marek'
        ordering = ['brand_name']
        indexes = [
            models.Index(fields=['brand_id']),
            models.Index(fields=['brand_name']),
        ]

    def __str__(self):
        return f"{self.brand_name} (ID: {self.brand_id})"


class ProducerColor(models.Model):
    """Baza kolorów producenta dla marki - przechowuje fantazyjne nazwy kolorów"""

    id = models.BigAutoField(primary_key=True)
    brand_id = models.IntegerField(
        db_index=True, verbose_name='ID marki')
    brand_name = models.CharField(
        max_length=200, verbose_name='Nazwa marki')
    color_name = models.CharField(
        max_length=200, verbose_name='Nazwa koloru producenta')
    normalized_color = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Znormalizowana nazwa koloru',
        help_text='Znormalizowana wersja nazwy koloru do porównań'
    )
    usage_count = models.IntegerField(
        default=0, verbose_name='Liczba użyć')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Utworzono')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='Zaktualizowano')

    class Meta:
        db_table = 'producer_color'
        verbose_name = 'Kolor producenta'
        verbose_name_plural = 'Kolory producenta'
        ordering = ['brand_name', 'color_name']
        unique_together = [['brand_id', 'color_name']]
        indexes = [
            models.Index(fields=['brand_id', 'color_name']),
            models.Index(fields=['brand_name']),
        ]

    def __str__(self):
        return f"{self.brand_name} - {self.color_name}"

    def save(self, *args, **kwargs):
        """Automatycznie normalizuje nazwę koloru przy zapisie"""
        if not self.normalized_color and self.color_name:
            self.normalized_color = self._normalize_color_name(self.color_name)
        super().save(*args, **kwargs)

    @staticmethod
    def _normalize_color_name(color_name: str) -> str:
        """Normalizuje nazwę koloru do porównań (lowercase, bez spacji)"""
        if not color_name:
            return ""
        return color_name.lower().strip().replace(' ', '').replace('-', '')


class AIPrompt(models.Model):
    """Prompty AI do zarządzania w Django Admin"""

    PROMPT_TYPE_CHOICES = [
        ('system', 'System'),
        ('user', 'User'),
    ]

    CATEGORY_CHOICES = [
        ('description', 'Opis produktu'),
        ('name', 'Nazwa produktu'),
        ('attributes', 'Ekstrakcja atrybutów'),
        ('legacy', 'Legacy enhancement'),
    ]

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=200,
        unique=True,
        db_index=True,
        verbose_name='Nazwa promptu',
        help_text='Unikalna nazwa promptu (np. "product_description_system", "product_name_user_figi")'
    )
    prompt_type = models.CharField(
        max_length=20,
        choices=PROMPT_TYPE_CHOICES,
        verbose_name='Typ promptu',
        help_text='System prompt (instrukcje) lub User prompt (zadanie)'
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        verbose_name='Kategoria',
        help_text='Kategoria promptu (description, name, attributes, legacy)'
    )
    content = models.TextField(
        verbose_name='Treść promptu',
        help_text='Treść promptu. Możesz użyć zmiennych w formacie {variable_name} (np. {base_type}, {has_top}, {description_sections})'
    )
    variables = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Zmienne',
        help_text='Lista zmiennych używanych w prompcie (np. ["base_type", "has_top", "description_sections"])'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Aktywny',
        help_text='Czy prompt jest aktywny (używany w automatyzacji)'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Opis',
        help_text='Opis promptu i jego przeznaczenia'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Utworzono')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='Zaktualizowano')

    class Meta:
        db_table = 'ai_prompt'
        verbose_name = 'Prompt AI'
        verbose_name_plural = 'Prompty AI'
        ordering = ['category', 'prompt_type', 'name']
        indexes = [
            models.Index(fields=['category', 'prompt_type', 'is_active']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_prompt_type_display()}, {self.get_category_display()})"

    def render(self, **kwargs) -> str:
        """Renderuje prompt z wypełnionymi zmiennymi"""
        try:
            content_str = str(self.content) if self.content else ""
            return content_str.format(**kwargs)
        except KeyError:
            # Jeśli brakuje zmiennej, zwróć oryginalny prompt
            return str(self.content) if self.content else ""
