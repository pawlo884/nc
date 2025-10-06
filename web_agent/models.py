from django.db import models


class WebAgentTask(models.Model):
    """Model dla zadań agenta web"""
    
    STATUS_CHOICES = [
        ('pending', 'Oczekujące'),
        ('running', 'W trakcie'),
        ('completed', 'Zakończone'),
        ('failed', 'Niepowodzenie'),
        ('cancelled', 'Anulowane'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('scrape', 'Scraping'),
        ('monitor', 'Monitorowanie'),
        ('data_collection', 'Zbieranie danych'),
        ('automation', 'Automatyzacja'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Nazwa zadania')
    task_type = models.CharField(
        max_length=50, 
        choices=TASK_TYPE_CHOICES,
        verbose_name='Typ zadania'
    )
    url = models.URLField(blank=True, null=True, verbose_name='URL')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='Status'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Data utworzenia'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Data aktualizacji'
    )
    started_at = models.DateTimeField(
        blank=True, null=True, 
        verbose_name='Data rozpoczęcia'
    )
    completed_at = models.DateTimeField(
        blank=True, null=True, 
        verbose_name='Data zakończenia'
    )
    config = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='Konfiguracja'
    )
    result = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='Wynik'
    )
    error_message = models.TextField(
        blank=True, 
        verbose_name='Komunikat błędu'
    )
    celery_task_id = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name='ID zadania Celery'
    )
    
    class Meta:
        db_table = 'web_agent_tasks'
        verbose_name = 'Zadanie agenta web'
        verbose_name_plural = 'Zadania agenta web'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class WebAgentLog(models.Model):
    """Model dla logów agenta web"""
    
    LOG_LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Informacja'),
        ('WARNING', 'Ostrzeżenie'),
        ('ERROR', 'Błąd'),
        ('CRITICAL', 'Krytyczny'),
    ]
    
    task = models.ForeignKey(
        WebAgentTask, 
        on_delete=models.CASCADE, 
        related_name='logs',
        verbose_name='Zadanie'
    )
    level = models.CharField(
        max_length=10, 
        choices=LOG_LEVEL_CHOICES,
        verbose_name='Poziom logu'
    )
    message = models.TextField(verbose_name='Wiadomość')
    timestamp = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Znacznik czasu'
    )
    extra_data = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='Dodatkowe dane'
    )
    
    class Meta:
        db_table = 'web_agent_logs'
        verbose_name = 'Log agenta web'
        verbose_name_plural = 'Logi agenta web'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.task.name} - {self.get_level_display()} - {self.timestamp}"


class WebAgentConfig(models.Model):
    """Model dla konfiguracji agenta web"""
    
    name = models.CharField(max_length=100, unique=True, verbose_name='Nazwa')
    description = models.TextField(blank=True, verbose_name='Opis')
    config_data = models.JSONField(verbose_name='Dane konfiguracji')
    is_active = models.BooleanField(default=True, verbose_name='Aktywny')
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Data utworzenia'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Data aktualizacji'
    )
    
    class Meta:
        db_table = 'web_agent_configs'
        verbose_name = 'Konfiguracja agenta web'
        verbose_name_plural = 'Konfiguracje agenta web'
        ordering = ['name']
    
    def __str__(self):
        return self.name
