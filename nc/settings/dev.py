import socket
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-zlntqh&x6vv%$+87ycj-)=#isuos^f_h4w%e#9+&w%xd5mph)!'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1',
                 '192.168.50.63', '83.168.79.109', '212.127.93.27', '*', '_']

# API URL configuration for development
API_BASE_URL = os.getenv('API_BASE_URL', 'http://83.168.79.109:8000')
MPD_API_URL = os.getenv('MPD_API_URL', 'http://localhost:8000/mpd')

# Timeout settings for long-running requests
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Django timeout settings
USE_TZ = True
TIME_ZONE = 'Europe/Warsaw'

# Database connection timeout
DATABASE_CONNECTION_TIMEOUT = 300  # 5 minutes

# Security settings for development
CORS_REPLACE_HTTPS_REFERER = False
HOST_SCHEME = "http://"
SECURE_PROXY_SSL_HEADER = None
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = None
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_FRAME_DENY = False

# Cross-Origin-Opener-Policy settings for development
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# CSRF Configuration for development
CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://127.0.0.1',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://192.168.50.63',
    'http://192.168.50.63:8000',
    'http://83.168.79.109',
    'http://83.168.79.109:8000',
    'http://212.127.93.27',
    'http://212.127.93.27:8000',
]
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False

# Debug Toolbar Configuration
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = ['127.0.0.1', 'localhost', '192.168.50.63', '212.127.93.27'] + \
    [ip[:-1] + '1' for ip in ips]

# Wyłącz debug toolbar tymczasowo aby sprawdzić czy wpływa na admin interface
# DEBUG_TOOLBAR_CONFIG = {
#     'SHOW_TOOLBAR_CALLBACK': lambda request: True,
#     'SHOW_TEMPLATE_CONTEXT': True,
#     'ENABLE_STACKTRACES': True,
#     'SQL_WARNING_THRESHOLD': 500,  # milliseconds
# }

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://192.168.50.63:8000",
    "http://83.168.79.109:8000",
]

# Celery Configuration for development
CELERY_BROKER_URL = 'redis://:dev_password@redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://:dev_password@redis:6379/0'

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

# Celery heartbeat configuration - wyłączony dla development
CELERY_WORKER_HEARTBEAT = 0  # Wyłączony heartbeat dla development
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = False  # Zmieniony na False dla development
CELERY_WORKER_DISABLE_RATE_LIMITS = True  # Wyłącz limity dla development
# Zwiększone limity dla długotrwałych tasków importu (3600s = 1 godzina)
CELERY_TASK_TIME_LIMIT = 3600  # 1 godzina hard limit dla tasków
CELERY_TASK_SOFT_TIME_LIMIT = 3300  # 55 minut soft limit

# Static files configuration for development with Nginx
# Nginx obsługuje pliki statyczne, nie WhiteNoise
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Usuń WhiteNoise z middleware w development - Nginx obsługuje pliki statyczne
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
