"""
Widoki dashboard_pydash – RBAC (tylko zalogowani, staff ma pełny dostęp).
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_GET, require_POST
from django.urls import reverse

from .models import DashAuditLog
from .tasks import run_simulation


def _is_staff(user):
    return user.is_authenticated and user.is_staff


@require_GET
@login_required
def dashboard_view(request):
    """Główny widok dashboardu z osadzonym Dash (RBAC: login_required)."""
    DashAuditLog.objects.create(
        user=request.user,
        action='view_dashboard',
        details={'path': request.path},
    )
    return render(request, 'dashboard_pydash/dashboard.html', {
        'user': request.user,
        'is_staff': request.user.is_staff,
    })


@require_GET
@login_required
@user_passes_test(_is_staff)
def audit_log_view(request):
    """Lista audit log – tylko dla staff (RBAC)."""
    DashAuditLog.objects.create(
        user=request.user,
        action='view_audit_log',
        details={},
    )
    entries = DashAuditLog.objects.select_related('user').order_by('-created_at')[:100]
    return render(request, 'dashboard_pydash/audit_log.html', {'entries': entries})


@require_POST
@login_required
def trigger_simulation_view(request):
    """Uruchamia task Celery (symulacja) – zapis w audit log."""
    task = run_simulation.delay(user_id=request.user.id, params={'source': 'dashboard'})
    DashAuditLog.objects.create(
        user=request.user,
        action='trigger_task',
        details={'task_id': str(task.id), 'task_name': 'run_simulation'},
    )
    return redirect(reverse('dashboard_pydash:dashboard'))
