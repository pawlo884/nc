from django.db import models


class WebSession(models.Model):
    """Model reprezentujący sesję web scraping"""
    name = models.CharField(max_length=255, verbose_name="Nazwa sesji")
    url = models.URLField(verbose_name="URL docelowy")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Data utworzenia")
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Data aktualizacji")
    is_active = models.BooleanField(default=True, verbose_name="Aktywna")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    headers = models.JSONField(
        default=dict, blank=True, verbose_name="Nagłówki HTTP")
    cookies = models.JSONField(
        default=dict, blank=True, verbose_name="Cookies")
    proxy = models.CharField(max_length=255, blank=True, verbose_name="Proxy")
    timeout = models.IntegerField(default=30, verbose_name="Timeout (sekundy)")

    class Meta:
        verbose_name = "Sesja Web"
        verbose_name_plural = "Sesje Web"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.url}"


class ScrapingTask(models.Model):
    """Model reprezentujący zadanie scraping"""
    STATUS_CHOICES = [
        ('pending', 'Oczekujące'),
        ('running', 'W trakcie'),
        ('completed', 'Zakończone'),
        ('failed', 'Błąd'),
        ('cancelled', 'Anulowane'),
    ]

    session = models.ForeignKey(
        WebSession, on_delete=models.CASCADE, verbose_name="Sesja")
    name = models.CharField(max_length=255, verbose_name="Nazwa zadania")
    url = models.URLField(verbose_name="URL do scrapowania")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Data utworzenia")
    started_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Data rozpoczęcia")
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Data zakończenia")
    error_message = models.TextField(
        blank=True, verbose_name="Komunikat błędu")
    retry_count = models.IntegerField(default=0, verbose_name="Liczba prób")
    max_retries = models.IntegerField(
        default=3, verbose_name="Maksymalna liczba prób")

    # Konfiguracja scraping
    selectors = models.JSONField(
        default=dict, blank=True, verbose_name="Selektory CSS")
    wait_time = models.IntegerField(
        default=5, verbose_name="Czas oczekiwania (sekundy)")
    use_selenium = models.BooleanField(
        default=False, verbose_name="Użyj Selenium")
    headless = models.BooleanField(default=True, verbose_name="Tryb headless")

    class Meta:
        verbose_name = "Zadanie Scraping"
        verbose_name_plural = "Zadania Scraping"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.status}"


class ScrapingResult(models.Model):
    """Model reprezentujący wynik scraping"""
    task = models.ForeignKey(
        ScrapingTask, on_delete=models.CASCADE, verbose_name="Zadanie")
    data = models.JSONField(default=dict, verbose_name="Dane")
    raw_html = models.TextField(blank=True, verbose_name="Surowy HTML")
    screenshot_path = models.CharField(
        max_length=500, blank=True, verbose_name="Ścieżka do screenshot")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Data utworzenia")

    class Meta:
        verbose_name = "Wynik Scraping"
        verbose_name_plural = "Wyniki Scraping"
        ordering = ['-created_at']

    def __str__(self):
        return f"Wynik dla {self.task.name} - {self.created_at}"

    def get_data_summary(self):
        """Zwraca podsumowanie danych"""
        if isinstance(self.data, dict):
            return f"Klucze: {list(self.data.keys())}"
        elif isinstance(self.data, list):
            return f"Liczba elementów: {len(self.data)}"
        else:
            return str(self.data)[:100] + "..." if len(str(self.data)) > 100 else str(self.data)


class WebAgentLog(models.Model):
    """Model reprezentujący logi web agenta"""
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]

    session = models.ForeignKey(
        WebSession, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Sesja")
    task = models.ForeignKey(ScrapingTask, on_delete=models.CASCADE,
                             null=True, blank=True, verbose_name="Zadanie")
    level = models.CharField(
        max_length=10, choices=LEVEL_CHOICES, verbose_name="Poziom")
    message = models.TextField(verbose_name="Wiadomość")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Data utworzenia")

    class Meta:
        verbose_name = "Log Web Agent"
        verbose_name_plural = "Logi Web Agent"
        ordering = ['-created_at']

    def __str__(self):
        message_preview = str(self.message)[:50] if self.message else ''
        return f"{self.level} - {message_preview}"
