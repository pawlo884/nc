"""
WSGI config for nc project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import logging
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings')

logger = logging.getLogger(__name__)

try:
    application = get_wsgi_application()
except Exception as e:
    # Użyj prostego logowania bez exc_info, aby uniknąć problemów z textwrap.dedent
    logger.error(f"Błąd podczas inicjalizacji WSGI: {type(e).__name__}: {str(e)}")
    raise

# Wyłączony wrapper z obsługą błędów - może powodować problemy z parsowaniem requestów
# Django ma własną obsługę błędów, która jest bardziej stabilna
# application = application_with_error_handling
