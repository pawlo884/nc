import socket
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-zlntqh&x6vv%$+87ycj-)=#isuos^f_h4w%e#9+&w%xd5mph)!'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.1.109', '*']

# API URL configuration for development
API_BASE_URL = os.getenv('API_BASE_URL', 'http://212.127.93.27:8000')

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

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: True,
    'SHOW_TEMPLATE_CONTEXT': True,
    'ENABLE_STACKTRACES': True,
    'SQL_WARNING_THRESHOLD': 500,  # milliseconds
}

# Celery Configuration for development
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
