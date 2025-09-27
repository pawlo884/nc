import os
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY', 'django-insecure-zlntqh&x6vv%$+87ycj-)=#isuos^f_h4w%e#9+&w%xd5mph)!')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', '209.38.208.114']


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# WhiteNoise Configuration
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_ALLOW_ALL_ORIGINS = True

# Security settings for production
SECURE_SSL_REDIRECT = False  # Tymczasowo wyłączone, ponieważ nie mamy jeszcze HTTPS
SESSION_COOKIE_SECURE = False  # Tymczasowo wyłączone
CSRF_COOKIE_SECURE = False  # Tymczasowo wyłączone
SECURE_HSTS_SECONDS = None  # Tymczasowo wyłączone
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_FRAME_DENY = False

# Dodatkowe ustawienia dla proxy
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = None

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Celery Configuration
CELERY_BROKER_URL = f'redis://:{os.getenv("REDIS_PASSWORD", "Relisys17!!")}@redis:6379/0'
CELERY_RESULT_BACKEND = f'redis://:{os.getenv("REDIS_PASSWORD", "Relisys17!!")}@redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Warsaw'
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_TRACK_STARTED = True

# Celery Beat Configuration
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery Task Routes - routing do odpowiednich kolejek
CELERY_TASK_ROUTES = {
    # Task importu trafia do kolejki 'import'
    'matterhorn1.tasks.full_import_and_update': {'queue': 'import'},
    # Pozostałe taski używają domyślnej kolejki
    'matterhorn1.tasks.*': {'queue': 'default'},
}

# Cache Configuration - Redis dla blokad między workerami
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        # Używamy bazy 1 dla cache
        'LOCATION': f'redis://:{os.getenv("REDIS_PASSWORD", "Relisys17!!")}@redis:6379/1',
    }
}

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

# drf-spectacular Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'NC Project API',
    'DESCRIPTION': 'API dla zarządzania produktami, wariantami i eksportu XML',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'TAGS': [
        {'name': 'Products', 'description': 'Operacje na produktach'},
        {'name': 'Variants', 'description': 'Operacje na wariantach produktów'},
        {'name': 'Brands', 'description': 'Operacje na markach'},
        {'name': 'Categories', 'description': 'Operacje na kategoriach'},
        {'name': 'Images', 'description': 'Operacje na obrazach produktów'},
        {'name': 'Product Sets', 'description': 'Zarządzanie zestawami produktów'},
        {'name': 'XML Export', 'description': 'Eksport i generowanie plików XML'},
        {'name': 'Database', 'description': 'Operacje na bazie danych'},
        {'name': 'Sync', 'description': 'Synchronizacja z zewnętrznymi API'},
    ],
}
