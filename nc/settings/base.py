"""
Base Django settings for nc project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables
load_dotenv()

# Konfiguracja logowania
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
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/matterhorn/import_all_by_one.log'),
            'maxBytes': 5 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'matterhorn': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Application definition
INSTALLED_APPS = [
    'admin_interface',
    'colorfield',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',
    'django_celery_beat',
    'django_celery_results',
    'debug_toolbar',
    'main',
    'matterhorn',
    'MPD',
    'web_agent',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

ROOT_URLCONF = 'nc.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DEFAULT_DB_NAME'),
        'USER': os.getenv('DEFAULT_DB_USER'),
        'PASSWORD': os.getenv('DEFAULT_DB_PASSWORD'),
        'HOST': os.getenv('DEFAULT_DB_HOST'),
        'PORT': os.getenv('DEFAULT_DB_PORT'),
        'CONN_MAX_AGE': 600,  # 10 minut
    },
    'matterhorn': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('MATTERHORN_DB_NAME'),
        'USER': os.getenv('MATTERHORN_DB_USER'),
        'PASSWORD': os.getenv('MATTERHORN_DB_PASSWORD'),
        'HOST': os.getenv('MATTERHORN_DB_HOST'),
        'PORT': os.getenv('MATTERHORN_DB_PORT'),
        'CONN_MAX_AGE': 600,  # 10 minut
    },
    'MPD': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('MPD_DB_NAME'),
        'USER': os.getenv('MPD_DB_USER'),
        'PASSWORD': os.getenv('MPD_DB_PASSWORD'),
        'HOST': os.getenv('MPD_DB_HOST'),
        'PORT': os.getenv('MPD_DB_PORT'),
        'CONN_MAX_AGE': 600,  # 10 minut
    }
}

# Database routers
DATABASE_ROUTERS = [
    'nc.db_routers.MatterhornRouter',
    'nc.db_routers.MPDRouter',]

WSGI_APPLICATION = 'nc.wsgi.application'

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
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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
CELERY_TASK_TRACK_STARTED = True

# Cache Configuration - Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://:dev_password@redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'nc_cache',
        'TIMEOUT': 300,  # 5 minut domyślnie
    }
}

# Session Cache
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Query Optimization
DATABASE_OPTIMIZATION = {
    'QUERY_TIMEOUT': 30,  # sekundy
    'MAX_QUERY_RESULTS': 10000,  # maksymalna liczba wyników w jednym zapytaniu
    'BATCH_SIZE': 1000,  # rozmiar batch dla bulk operations
}

# Memory Management
MEMORY_OPTIMIZATION = {
    'ENABLE_QUERY_LOGGING': False,  # wyłącz w produkcji
    'ENABLE_SQL_LOGGING': False,    # wyłącz w produkcji
    'MAX_MEMORY_USAGE': 0.8,        # maksymalne użycie RAM (80%)
}

# Celery Beat Configuration
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# WhiteNoise Configuration
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_ALLOW_ALL_ORIGINS = True


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
