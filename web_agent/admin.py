from django.contrib import admin
from .models import WebAgentTask, WebAgentLog, WebAgentConfig


@admin.register(WebAgentTask)
class WebAgentTaskAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'brand_name', 'task_type', 'status', 'priority', 'url', 
        'created_at', 'started_at', 'completed_at'
    ]
    list_filter = [
        'status', 'task_type', 'brand_name', 'priority', 'created_at', 
        'started_at', 'completed_at'
    ]
    search_fields = ['name', 'brand_name', 'url', 'error_message']
    readonly_fields = [
        'created_at', 'updated_at', 'started_at', 
        'completed_at', 'celery_task_id'
    ]
    list_per_page = 25
    ordering = ['-priority', '-created_at']
    
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('name', 'task_type', 'status', 'url')
        }),
        ('Organizacja per marka', {
            'fields': ('brand_id', 'brand_name', 'priority')
        }),
        ('Dane techniczne', {
            'fields': ('config', 'result', 'celery_task_id')
        }),
        ('Daty', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at')
        }),
        ('Błędy', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )


@admin.register(WebAgentLog)
class WebAgentLogAdmin(admin.ModelAdmin):
    list_display = [
        'task', 'level', 'message_short', 'timestamp'
    ]
    list_filter = ['level', 'timestamp', 'task__status']
    search_fields = ['message', 'task__name']
    readonly_fields = ['timestamp']
    list_per_page = 50
    ordering = ['-timestamp']
    
    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Wiadomość'
    
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('task', 'level', 'message')
        }),
        ('Dodatkowe dane', {
            'fields': ('timestamp', 'extra_data'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WebAgentConfig)
class WebAgentConfigAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'description_short', 'is_active', 
        'created_at', 'updated_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    ordering = ['name']
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Opis'
    
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Konfiguracja', {
            'fields': ('config_data',)
        }),
        ('Daty', {
            'fields': ('created_at', 'updated_at')
        }),
    )
