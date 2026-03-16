"""
Views for nc project.
"""
from django.shortcuts import render
from django.http import HttpResponse


def index(request):
    """Strona główna projektu."""
    return render(request, 'index.html')


def health_check(request):
    """Health check endpoint dla Docker health checks."""
    return HttpResponse("OK", content_type="text/plain")
