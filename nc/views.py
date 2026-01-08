"""
Views for nc project.
"""
from django.shortcuts import render


def index(request):
    """Strona główna projektu."""
    return render(request, 'index.html')
