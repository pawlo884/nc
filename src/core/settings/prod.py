import os
from .base import *

# Produkcja używa baz bez przedrostka zzz_ (zdefiniowanych w base.py)
# Development (dev.py) nadpisuje je na wersje z zzz_

# Usuń bazy z przedrostkiem zzz_ z DATABASES (tylko dla produkcji)
zzz_databases = [key for key in DATABASES.keys() if key.startswith('zzz_')]
for zzz_db in zzz_databases:
    del DATABASES[zzz_db]

# Usuń debug_toolbar z INSTALLED_APPS w produkcji
if 'debug_toolbar' in INSTALLED_APPS:
    INSTALLED_APPS.remove('debug_toolbar')

# Limity uploadów dla produkcji
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000  # Maksymalna liczba pól w formularzu

# Limity dla gunicorn - zwiększone dla stabilności
GUNICORN_TIMEOUT = 300  # 5 minut
GUNICORN_KEEPALIVE = 5  # 5 sekund
GUNICORN_MAX_REQUESTS = 500  # Restart workera po 500 requestach

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY', 'django-insecure-zlntqh&x6vv%$+87ycj-)=#isuos^f_h4w%e#9+&w%xd5mph)!')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Bezpieczniejsza konfiguracja ALLOWED_HOSTS
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '212.127.93.27',  # VPS IP
    '192.168.50.31',  # IP serwera w sieci lokalnej
    'app-web-1',  # Nazwa kontenera Docker
    'web',  # Alias kontenera w sieci Docker
    'nc.sowa.ch',  # Główna domena aplikacji
    'sowa.ch',  # Domena główna (bez poddomeny)
    # Dodaj konkretne domeny zamiast '*'
    # 'twoja-domena.com',
    # 'www.twoja-domena.com',
]

# Dodatkowe ustawienia bezpieczeństwa dla produkcji
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Logowanie - tylko console (bez plików) - nadpisuje base.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process} {thread} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security.DisallowedHost': {
            'handlers': ['console'],
            'level': 'CRITICAL',  # Zmienione z WARNING na CRITICAL aby nie logować każdego ataku
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',  # Zmienione na ERROR aby widzieć błędy 500
            'propagate': False,
        },
        'gunicorn.error': {
            'handlers': ['console'],
            'level': 'WARNING',  # Loguj błędy gunicorn
            'propagate': False,
        },
        'gunicorn.access': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'gunicorn.error': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'gunicorn.access': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
# Używamy Path object zamiast os.path.join dla spójności z base.py
STATIC_ROOT = str(BASE_DIR / 'staticfiles')
# Sprawdź czy katalog static istnieje przed dodaniem do STATICFILES_DIRS
static_dir = str(BASE_DIR / 'static')
STATICFILES_DIRS = [
    static_dir,
] if os.path.exists(static_dir) else []

# Konfiguracja dla plików statycznych w produkcji
# Używamy WhiteNoise jako fallback gdy nginx nie działa lub aplikacja działa bezpośrednio
# Używamy zwykłego WhiteNoiseStorage (bez manifestu) dla prostoty
STATICFILES_STORAGE = 'whitenoise.storage.WhiteNoiseStaticFilesStorage'

# WhiteNoise configuration
WHITENOISE_USE_FINDERS = True  # Pozwól WhiteNoise używać finders do znajdowania plików
WHITENOISE_AUTOREFRESH = True  # Automatycznie odświeżaj pliki (dla development)
WHITENOISE_MANIFEST_STRICT = False  # Nie wymagaj manifestu

# STATICFILES_FINDERS - używamy domyślnych z base.py
# Dodajemy obsługę duplikatów - pierwszy znaleziony plik jest używany
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Dodaj WhiteNoise do middleware dla serwowania plików statycznych
# WhiteNoise działa jako fallback gdy nginx nie jest dostępny
# BotBlockerMiddleware blokuje znane boty i crawlery
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Dodane dla serwowania plików statycznych
    # Blokowanie botów i crawlerów
    'core.middleware.BotBlockerMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Security settings for production
SECURE_SSL_REDIRECT = False  # Tymczasowo wyłączone, ponieważ nie mamy jeszcze HTTPS
SESSION_COOKIE_SECURE = False  # Wyłączone dla dostępu po HTTP (bez HTTPS)
SECURE_HSTS_SECONDS = None  # Tymczasowo wyłączone
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_FRAME_DENY = False

# Cross-Origin-Opener-Policy settings for production
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# Dodatkowe ustawienia dla proxy
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = None

# CSRF Configuration
CSRF_TRUSTED_ORIGINS = [
    'http://212.127.93.27',
    'http://212.127.93.27:8000',
    'http://212.127.93.27:8001',
    'https://212.127.93.27',
    'http://192.168.50.31',
    'http://192.168.50.31:8000',
    'http://192.168.50.31:8001',
    'http://172.24.0.1:8001',  # Adres bramy sieci Docker dla NPM
    'https://nc.sowa.ch',
    'https://sowa.ch',
]
CSRF_COOKIE_SECURE = False  # Wyłączone dla logowania po HTTP (bez HTTPS)
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://212.127.93.27:8001",
    "http://192.168.50.31:8001",
]

# Redis Configuration - wspólne dla Celery i Cache
# W Dockerze nazwa serwisu Redis to 'redis' (w trybie blue-green: docker-compose.blue-green.yml)
# Użyj zmiennych środowiskowych CELERY_BROKER_URL jeśli są ustawione (z docker-compose)
# W przeciwnym razie użyj REDIS_HOST i REDIS_PASSWORD
if os.getenv('CELERY_BROKER_URL'):
    # Workerzy mają ustawione CELERY_BROKER_URL w docker-compose
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', os.getenv('CELERY_BROKER_URL'))
    # Wyciągnij REDIS_HOST i REDIS_PASSWORD z URL dla cache
    # Użyj prostego parsowania stringa zamiast regex
    try:
        # Format: redis://:password@host:port/db
        broker_url = CELERY_BROKER_URL
        if '://:' in broker_url:
            # Ma hasło
            parts = broker_url.replace('redis://:', '').split('@', 1)
            if len(parts) == 2:
                REDIS_PASSWORD = parts[0]
                host_part = parts[1].split('/')[0]  # Usuń /db
                REDIS_HOST = host_part.split(':')[0]  # Usuń :port
            else:
                REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
                REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'CHANGE_ME_IN_ENV')
        else:
            # Bez hasła
            REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
            REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'CHANGE_ME_IN_ENV')
    except Exception:
        # Fallback jeśli parsowanie się nie powiedzie
        REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
        REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'CHANGE_ME_IN_ENV')
else:
    # Aplikacja web używa REDIS_HOST i REDIS_PASSWORD
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'CHANGE_ME_IN_ENV')
    CELERY_BROKER_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/0'
    CELERY_RESULT_BACKEND = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/0'

# Debug: sprawdź czy zmienne są załadowane (tylko jeśli DEBUG=True)
if DEBUG:
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Celery Configuration: BROKER_URL={CELERY_BROKER_URL[:30]}..., RESULT_BACKEND={CELERY_RESULT_BACKEND[:30]}...")
    logger.info(f"Redis Configuration: HOST={REDIS_HOST}, PASSWORD={'***' if REDIS_PASSWORD else 'NOT SET'}")
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Warsaw'
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_TRACK_STARTED = True

# Celery Redis connection settings - fix dla connection timeouts
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
CELERY_BROKER_POOL_LIMIT = 10
CELERY_REDIS_MAX_CONNECTIONS = 50

# Celery Redis transport options - uproszczona konfiguracja keepalive
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,
    'max_connections': 50,
    'socket_keepalive': True,
    'socket_timeout': 120,  # Socket timeout (2 minuty)
    'socket_connect_timeout': 30,  # Connection timeout (30 sekund)
    'retry_on_timeout': True,
    # Health check co 25 sekund
    'health_check_interval': 25,
}

# Result backend transport options - takie same jak broker
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    'socket_keepalive': True,
    'socket_timeout': 120,
    'socket_connect_timeout': 30,
    'retry_on_timeout': True,
    'health_check_interval': 25,
}

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
# Użyj django-redis z obsługą błędów
try:
    import django_redis
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            # Używamy bazy 1 dla cache
            'LOCATION': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/1',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'CONNECTION_POOL_KWARGS': {
                    'retry_on_timeout': True,
                    'socket_connect_timeout': 5,
                },
                # Ignoruj błędy połączenia - aplikacja będzie działać bez cache
                'IGNORE_EXCEPTIONS': True,
            }
        }
    }
except ImportError:
    # Fallback do dummy cache jeśli django-redis nie jest dostępne
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

# Django REST Framework Configuration
REST_FRAMEWORK = {
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
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/day',
        'anon': '100/day',
        'bulk': '60/min',
    },
}

# Dodaj drf_spectacular tylko jeśli jest dostępny
try:
    import drf_spectacular
    REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'
except ImportError:
    pass

# drf-spectacular Configuration (tylko jeśli dostępny)
try:
    import drf_spectacular
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
except ImportError:
    SPECTACULAR_SETTINGS = {}
