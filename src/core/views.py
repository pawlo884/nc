"""
Views for nc project.
"""
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse


def index(request):
    """Strona główna projektu."""
    try:
        import dashboard_pydash  # noqa: F401
        has_pydash = True
    except ImportError:
        has_pydash = False
    return render(request, 'index.html', {'has_pydash': has_pydash})


def health_check(request):
    """Health check endpoint dla Docker health checks."""
    return HttpResponse("OK", content_type="text/plain")
