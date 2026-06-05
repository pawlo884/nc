"""
Views for nc project.
"""
import os

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
from django.db import connections
from django.core.cache import cache


def index(request):
    """Strona główna projektu."""
    return render(request, 'index.html')


def health_check(request):
    """
    Health check dla Docker i Sentry Uptime Monitoring.

    ?simple=1 – tylko liveness (proces odpowiada).
    Domyślnie – readiness: baza danych + Redis.
    """
    if request.GET.get('simple') == '1':
        return HttpResponse('OK', content_type='text/plain')

    checks = {}
    healthy = True

    for db_alias in ('default',):
        try:
            with connections[db_alias].cursor() as cursor:
                cursor.execute('SELECT 1')
            checks[f'db_{db_alias}'] = 'ok'
        except Exception as exc:
            checks[f'db_{db_alias}'] = str(exc)
            healthy = False

    try:
        cache.set('health_check_probe', '1', 5)
        if cache.get('health_check_probe') == '1':
            checks['redis'] = 'ok'
        else:
            checks['redis'] = 'cache miss'
            healthy = False
    except Exception as exc:
        checks['redis'] = str(exc)
        healthy = False

    if healthy:
        return JsonResponse({'status': 'ok', 'checks': checks})

    return JsonResponse(
        {'status': 'unhealthy', 'checks': checks},
        status=503,
    )


def sentry_debug(request):
    """Testowy endpoint Sentry – celowo wywołuje błąd."""
    debug_endpoint_enabled = os.getenv('SENTRY_DEBUG_ENDPOINT', '').lower() in (
        '1', 'true', 'yes', 'on',
    )
    if not settings.DEBUG and not debug_endpoint_enabled:
        raise Http404

    _ = 1 / 0
