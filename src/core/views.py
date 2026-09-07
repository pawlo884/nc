"""
Views for nc project.
"""
import socket

from django.shortcuts import render
from django.http import HttpResponse


def index(request):
    """Strona główna projektu."""
    return render(request, 'index.html')


def health_check(request):
    """Health check dla Docker — w odpowiedzi hostname kontenera."""
    return HttpResponse(
        f"OK pod={socket.gethostname()}",
        content_type="text/plain",
    )
