"""
Ustawienia środowiska test (staging) na k3s.

Architektura jak prod (bez baz zzz_); różnice: domena testowa, bazy z .env.test,
opcjonalny DEBUG przez DJANGO_DEBUG.
"""
from .prod import *  # noqa: F403, F401

DJANGO_ENV = 'test'

_debug_env = os.getenv('DJANGO_DEBUG', '')
if _debug_env:
    DEBUG = _debug_env.lower() in ('1', 'true', 'yes', 'on')

allowed_hosts_env = os.getenv('DJANGO_ALLOWED_HOSTS', '')
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]
else:
    ALLOWED_HOSTS = [
        'localhost',
        '127.0.0.1',
        'nc-web',
        'nc-test.sowa.ch',
    ]

API_BASE_URL = os.getenv('API_BASE_URL', 'https://nc-test.sowa.ch')
MPD_API_URL = os.getenv('MPD_API_URL', 'https://nc-test.sowa.ch/mpd')

_csrf_extra = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if _csrf_extra:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _csrf_extra.split(',') if origin.strip()]
else:
    CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS) + [
        'https://nc-test.sowa.ch',
        'http://nc-test.sowa.ch',
    ]

if SPECTACULAR_SETTINGS:
    SPECTACULAR_SETTINGS = {**SPECTACULAR_SETTINGS, 'TITLE': 'NC Project API (TEST)'}
