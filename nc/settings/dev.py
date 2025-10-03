import socket
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-zlntqh&x6vv%$+87ycj-)=#isuos^f_h4w%e#9+&w%xd5mph)!'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.1.109', '*']

# API URL configuration for development
API_BASE_URL = os.getenv('API_BASE_URL', 'http://212.127.93.27:8000')
MPD_API_URL = os.getenv('MPD_API_URL', 'http://localhost:8000/mpd')

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

# Debug Toolbar Configuration
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = ['127.0.0.1', 'localhost', '192.168.1.109'] + \
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
]

# Celery Configuration for development
CELERY_BROKER_URL = 'redis://:dev_password@redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://:dev_password@redis:6379/0'

# Celery heartbeat configuration
CELERY_WORKER_HEARTBEAT = 30
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

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
