from django.contrib import admin
from .models import DashAuditLog


@admin.register(DashAuditLog)
class DashAuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'details_short')
    list_filter = ('action', 'created_at')
    search_fields = ('action', 'user__username')
    readonly_fields = ('user', 'action', 'details', 'created_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    def details_short(self, obj):
        if not obj.details:
            return '—'
        s = str(obj.details)[:80]
        return s + '…' if len(str(obj.details)) > 80 else s

    details_short.short_description = 'Szczegóły'
