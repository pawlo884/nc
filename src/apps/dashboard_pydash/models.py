"""
Modele dla dashboard_pydash.

Audit log – ślad dostępu do Dash (RBAC / enterprise).
"""
from django.conf import settings
from django.db import models


class DashAuditLog(models.Model):
    """Log dostępu do dashboardu (audit trail)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dash_audit_logs',
    )
    action = models.CharField(max_length=64)  # np. 'view_dashboard', 'trigger_task'
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dashboard_pydash_audit_log'
        ordering = ['-created_at']
        verbose_name = 'wpis audytu Dash'
        verbose_name_plural = 'audyt Dash'

    def __str__(self):
        return f"{self.action} @ {self.created_at}"
