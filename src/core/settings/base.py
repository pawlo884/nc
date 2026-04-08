"""
Base Django settings for nc project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
import tempfile
import logging

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR wskazuje na root projektu (tam gdzie jest manage.py, .env.dev, etc.)
# W kontenerze Docker: /app/core/settings/base.py -> parent.parent.parent = /app
# Lokalnie: src/core/settings/base.py -> parent.parent.parent.parent = root projektu
# Sprawdzamy czy jesteśmy w kontenerze (struktura /app/core/) czy lokalnie (src/core/)
_file_path = Path(__file__).resolve()
if len(_file_path.parts) >= 3 and _file_path.parts[1] == 'app' and _file_path.parts[2] == 'core':
    # W kontenerze Docker: /app/core/settings/base.py
    BASE_DIR = _file_path.parent.parent.parent  # /app
else:
    # Lokalnie: src/core/settings/base.py lub c:/.../src/core/settings/base.py
    BASE_DIR = _file_path.parent.parent.parent.parent  # root projektu

# Load environment variables
# .env.dev może być w BASE_DIR (Docker) lub BASE_DIR.parent (lokalnie, repo root)
def _find_dotenv(name: str) -> Path:
    p = BASE_DIR / name
    if p.exists():
        return p
    return BASE_DIR.parent / name

if os.getenv('DJANGO_SETTINGS_MODULE', '').endswith('.dev'):
    load_dotenv(_find_dotenv('.env.dev'))
elif os.getenv('DJANGO_SETTINGS_MODULE', '').endswith('.prod'):
    # W produkcji Docker ładuje .env.prod przez env_file, ale na wszelki wypadek
    load_dotenv(_find_dotenv('.env.prod'))
    load_dotenv()  # Fallback do .env jeśli .env.prod nie istnieje
else:
    load_dotenv()

# API URL configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')

# Matterhorn API configuration
MATTERHORN_API_URL = os.getenv(
    'MATTERHORN_API_URL', 'https://matterhorn.pl')
MATTERHORN_API_USERNAME = os.getenv('MATTERHORN_API_USERNAME', '')
MATTERHORN_API_PASSWORD = os.getenv('MATTERHORN_API_PASSWORD', '')
MATTERHORN_API_KEY = os.getenv('MATTERHORN_API_KEY', '')

# Tabu API configuration (dokumentacja: https://b2b.tabu.com.pl/api/v1)
TABU_API_BASE_URL = (os.getenv('TABU_API_BASE_URL') or 'https://b2b.tabu.com.pl/api/v1').strip().rstrip('/')
TABU_API_KEY = os.getenv('TABU_API_KEY', '')
# Domyślne ustawienia sync dla Tabu (możliwe do nadpisania przez env)
TABU_SYNC_STOP_AFTER_404_DEFAULT = int(os.getenv('TABU_SYNC_STOP_AFTER_404_DEFAULT', '10'))

# Konfiguracja logowania - tylko console logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} - {levelname} - {name} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {message}',
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
        'matterhorn': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Application definition
INSTALLED_APPS = [
    'admin_interface',  # Włączone - do customizacji kolorów admin
    'colorfield',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'django_celery_results',
    'debug_toolbar',
    'rest_framework',
    'rest_framework.authtoken',
    # 'matterhorn',  # usunięta stara aplikacja
    'MPD',
    'matterhorn1',
    'web_agent',
    'tabu',
]

# Dodaj drf_spectacular tylko jeśli jest dostępny
try:
    import drf_spectacular
    INSTALLED_APPS.append('drf_spectacular')
except ImportError:
    pass

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# Database
# Base zawiera konfigurację produkcyjną (bez przedrostka zzz_)
# Development (dev.py) nadpisuje na wersje z przedrostkiem zzz_
DATABASES = {
    'default': {
        'ENGINE': 'core.db_backend',
        'NAME': os.getenv('DEFAULT_DB_NAME'),
        'USER': os.getenv('DEFAULT_DB_USER'),
        'PASSWORD': os.getenv('DEFAULT_DB_PASSWORD'),
        'HOST': os.getenv('DEFAULT_DB_HOST'),
        'PORT': os.getenv('DEFAULT_DB_PORT'),
        # Musi być 0 z powodu database routing - routery wymagają zamykania połączeń po każdym użyciu
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 30,  # Zwiększone do 30s dla zewnętrznych serwerów
            'keepalives': 1,       # Włącz TCP keepalive
            'keepalives_idle': 60,  # Keepalive co 60s
            'keepalives_interval': 10,  # Interval 10s
            'keepalives_count': 5,  # 5 prób
            'options': '-c statement_timeout=300000 -c lock_timeout=300000'  # 5 minutes
        }
    },
    'zzz_default': {
        'ENGINE': 'core.db_backend',
        'NAME': os.getenv('DEFAULT_DB_NAME'),
        'USER': os.getenv('DEFAULT_DB_USER'),
        'PASSWORD': os.getenv('DEFAULT_DB_PASSWORD'),
        'HOST': os.getenv('DEFAULT_DB_HOST'),
        'PORT': os.getenv('DEFAULT_DB_PORT'),
        # Musi być 0 z powodu database routing - routery wymagają zamykania połączeń po każdym użyciu
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 30,  # Zwiększone do 30s dla zewnętrznych serwerów
            'keepalives': 1,       # Włącz TCP keepalive
            'keepalives_idle': 60,  # Keepalive co 60s
            'keepalives_interval': 10,  # Interval 10s
            'keepalives_count': 5,  # 5 prób
            'options': '-c statement_timeout=300000 -c lock_timeout=300000'  # 5 minutes
        }
    },
    'MPD': {
        'ENGINE': 'core.db_backend',
        'NAME': os.getenv('MPD_DB_NAME'),
        'USER': os.getenv('MPD_DB_USER'),
        'PASSWORD': os.getenv('MPD_DB_PASSWORD'),
        'HOST': os.getenv('MPD_DB_HOST'),
        'PORT': os.getenv('MPD_DB_PORT'),
        # Musi być 0 z powodu database routing - routery wymagają zamykania połączeń po każdym użyciu
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 30,  # Zwiększone do 30s dla zewnętrznych serwerów
            'keepalives': 1,       # Włącz TCP keepalive
            'keepalives_idle': 60,  # Keepalive co 60s
            'keepalives_interval': 10,  # Interval 10s
            'keepalives_count': 5,  # 5 prób
            'options': '-c statement_timeout=300000 -c lock_timeout=300000'  # 5 minutes
        }
    },
    'zzz_MPD': {
        'ENGINE': 'core.db_backend',
        'NAME': os.getenv('MPD_DB_NAME'),
        'USER': os.getenv('MPD_DB_USER'),
        'PASSWORD': os.getenv('MPD_DB_PASSWORD'),
        'HOST': os.getenv('MPD_DB_HOST'),
        'PORT': os.getenv('MPD_DB_PORT'),
        # Musi być 0 z powodu database routing - routery wymagają zamykania połączeń po każdym użyciu
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 30,  # Zwiększone do 30s dla zewnętrznych serwerów
            'keepalives': 1,       # Włącz TCP keepalive
            'keepalives_idle': 60,  # Keepalive co 60s
            'keepalives_interval': 10,  # Interval 10s
            'keepalives_count': 5,  # 5 prób
            'options': '-c statement_timeout=300000 -c lock_timeout=300000'  # 5 minutes
        }
    },
    'matterhorn1': {
        'ENGINE': 'core.db_backend',
        'NAME': os.getenv('MATTERHORN1_DB_NAME'),
        'USER': os.getenv('MATTERHORN1_DB_USER'),
        'PASSWORD': os.getenv('MATTERHORN1_DB_PASSWORD'),
        'HOST': os.getenv('MATTERHORN1_DB_HOST'),
        'PORT': os.getenv('MATTERHORN1_DB_PORT'),
        # Musi być 0 z powodu database routing - routery wymagają zamykania połączeń po każdym użyciu
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 30,  # Zwiększone do 30s dla zewnętrznych serwerów
            'keepalives': 1,       # Włącz TCP keepalive
            'keepalives_idle': 60,  # Keepalive co 60s
            'keepalives_interval': 10,  # Interval 10s
            'keepalives_count': 5,  # 5 prób
            'options': '-c statement_timeout=300000 -c lock_timeout=300000'  # 5 minutes
        }
    },
    'web_agent': {
        'ENGINE': 'core.db_backend',
        'NAME': os.getenv('WEB_AGENT_DB_NAME'),
        'USER': os.getenv('WEB_AGENT_DB_USER'),
        'PASSWORD': os.getenv('WEB_AGENT_DB_PASSWORD'),
        'HOST': os.getenv('WEB_AGENT_DB_HOST'),
        'PORT': os.getenv('WEB_AGENT_DB_PORT'),
        # Musi być 0 z powodu database routing - routery wymagają zamykania połączeń po każdym użyciu
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 30,  # Zwiększone do 30s dla zewnętrznych serwerów
            'keepalives': 1,       # Włącz TCP keepalive
            'keepalives_idle': 60,  # Keepalive co 60s
            'keepalives_interval': 10,  # Interval 10s
            'keepalives_count': 5,  # 5 prób
            'options': '-c statement_timeout=300000 -c lock_timeout=300000'  # 5 minutes
        }
    },
    'tabu': {
        'ENGINE': 'core.db_backend',
        'NAME': os.getenv('TABU_DB_NAME'),
        'USER': os.getenv('TABU_DB_USER'),
        'PASSWORD': os.getenv('TABU_DB_PASSWORD'),
        'HOST': os.getenv('TABU_DB_HOST'),
        'PORT': os.getenv('TABU_DB_PORT'),
        # Musi być 0 z powodu database routing - routery wymagają zamykania połączeń po każdym użyciu
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 30,  # Zwiększone do 30s dla zewnętrznych serwerów
            'keepalives': 1,       # Włącz TCP keepalive
            'keepalives_idle': 60,  # Keepalive co 60s
            'keepalives_interval': 10,  # Interval 10s
            'keepalives_count': 5,  # 5 prób
            'options': '-c statement_timeout=300000 -c lock_timeout=300000'  # 5 minutes
        }
    },
}

# Database routers
DATABASE_ROUTERS = [
    'core.db_routers.MPDRouter',
    'core.db_routers.Matterhorn1Router',
    'core.db_routers.WebAgentRouter',
    'core.db_routers.TabuRouter',
    'core.db_routers.DefaultRouter',
]

# Database retry configuration
# Konfiguracja automatycznego ponawiania połączeń z bazami danych
DATABASE_RETRY_CONFIG = {
    'max_retries': 8,              # Maksymalna liczba prób (po restarcie Dockera tunel SSH potrzebuje czasu)
    # Bazowe opóźnienie między próbami (w sekundach)
    'retry_delay': 3,
    # Czy używać exponential backoff (2^attempt * delay)
    'retry_backoff': True,
    # Maksymalne opóźnienie między próbami (w sekundach)
    'retry_max_delay': 30,
}

WSGI_APPLICATION = 'core.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'pl'
TIME_ZONE = 'Europe/Warsaw'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Obsługiwane języki
LANGUAGES = [
    ('pl', 'Polski'),
    ('en', 'English'),
]

# Ścieżka do plików tłumaczeń
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
] if os.path.exists(BASE_DIR / 'static') else []
# STATICFILES_STORAGE - konfigurowany w settings.dev.py i settings.prod.py

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Celery Configuration
CELERY_BROKER_URL = 'redis://:dev_password@redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://:dev_password@redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Warsaw'
CELERY_TASK_ACKS_LATE = True

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

# Cache Configuration - Redis dla blokad między workerami
_CACHE_REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'CHANGE_ME_IN_ENV')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        # Używamy bazy 1 dla cache; hasło musi być ustawione w REDIS_PASSWORD w .env
        'LOCATION': f'redis://:{_CACHE_REDIS_PASSWORD}@redis:6379/1',
    }
}
CELERY_TASK_TRACK_STARTED = True

# Celery Beat Configuration
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery Task Configuration
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Warsaw'
CELERY_ENABLE_UTC = True

# Celery Task Routes - routing do odpowiednich kolejek
# Musi być zsynchronizowane z app.conf.task_routes w core/celery.py
CELERY_TASK_ROUTES = {
    # Task importu trafia do kolejki 'import'
    'matterhorn1.tasks.full_import_and_update': {'queue': 'import'},
    # Pozostałe taski używają kolejki 'default' (worker celery-default z -Q default)
    'matterhorn1.tasks.*': {'queue': 'default'},
    'MPD.tasks.*': {'queue': 'default'},
    'tabu.tasks.*': {'queue': 'default'},
}

# Celery Beat Schedule - używaj Django periodic tasks zamiast tego
# CELERY_BEAT_SCHEDULE = {}

# WhiteNoise usunięty - Nginx obsługuje pliki statyczne w obu środowiskach


# Debug Toolbar Configuration
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.history.HistoryPanel',
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'debug_toolbar.panels.profiling.ProfilingPanel',
]

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

# Storage configuration (MinIO / S3-compatible)
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT')
MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')

S3_ENDPOINT = MINIO_ENDPOINT or os.getenv('AWS_S3_ENDPOINT_URL')
S3_BUCKET_NAME = MINIO_BUCKET_NAME or os.getenv('AWS_STORAGE_BUCKET_NAME')
S3_ACCESS_KEY = MINIO_ACCESS_KEY or os.getenv('AWS_ACCESS_KEY_ID')
S3_SECRET_KEY = MINIO_SECRET_KEY or os.getenv('AWS_SECRET_ACCESS_KEY')

if S3_BUCKET_NAME and S3_ACCESS_KEY and S3_SECRET_KEY:
    try:
        import storages  # noqa: F401
    except ImportError:
        pass
    else:
        if 'storages' not in INSTALLED_APPS:
            INSTALLED_APPS.append('storages')

        DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
        AWS_ACCESS_KEY_ID = S3_ACCESS_KEY
        AWS_SECRET_ACCESS_KEY = S3_SECRET_KEY
        AWS_STORAGE_BUCKET_NAME = S3_BUCKET_NAME
        AWS_S3_REGION_NAME = (
            os.getenv('MINIO_REGION')
            or os.getenv('AWS_S3_REGION_NAME')
            or 'us-east-1'
        )
        AWS_S3_ENDPOINT_URL = S3_ENDPOINT
        AWS_S3_ADDRESSING_STYLE = os.getenv('AWS_S3_ADDRESSING_STYLE', 'path')
        AWS_S3_SIGNATURE_VERSION = os.getenv(
            'AWS_S3_SIGNATURE_VERSION', 's3v4')
        if MINIO_ENDPOINT:
            AWS_S3_VERIFY = os.getenv(
                'MINIO_VERIFY_SSL', 'false').lower() == 'true'
        else:
            AWS_S3_VERIFY = os.getenv(
                'AWS_S3_VERIFY', 'true').lower() == 'true'
        AWS_DEFAULT_ACL = os.getenv('AWS_DEFAULT_ACL') or None
        AWS_QUERYSTRING_AUTH = os.getenv(
            'AWS_QUERYSTRING_AUTH', 'false').lower() == 'true'

        if AWS_S3_ENDPOINT_URL and AWS_STORAGE_BUCKET_NAME:
            MEDIA_URL = os.getenv(
                'MEDIA_URL',
                f"{AWS_S3_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME}/"
            )
