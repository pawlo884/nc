import socket
import sys
from .base import *
from core.middleware import get_debug

# Development rozszerza DATABASES z base.py o wersje z zzz_
# Dodajemy bazy z przedrostkiem zzz_ (routery wybiorą je automatycznie)
DATABASES['zzz_default'] = DATABASES['default'].copy()
DATABASES['zzz_MPD'] = DATABASES['MPD'].copy()
DATABASES['zzz_matterhorn1'] = DATABASES['matterhorn1'].copy()
DATABASES['zzz_web_agent'] = DATABASES['web_agent'].copy()
DATABASES['zzz_tabu'] = DATABASES['tabu'].copy()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY', 'django-insecure-zlntqh&x6vv%$+87ycj-)=#isuos^f_h4w%e#9+&w%xd5mph)!')

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG można kontrolować przez zmienną środowiskową DJANGO_DEBUG
# Dla publicznego dostępu ustaw DJANGO_DEBUG=0 w .env.dev
# Jeśli DJANGO_DEBUG nie jest ustawione, DEBUG będzie dynamicznie kontrolowane przez middleware
# na podstawie IP klienta (True dla localhost, False dla zewnętrznych IP)
debug_env = os.getenv('DJANGO_DEBUG', '')
if debug_env:
    # Jeśli DJANGO_DEBUG jest ustawione, użyj tej wartości
    DEBUG = debug_env.lower() in ('1', 'true', 'yes', 'on')
else:
    # Domyślnie True - middleware zmieni to dynamicznie na podstawie IP
    DEBUG = True

# ALLOWED_HOSTS - usunięto '*' i '_' dla bezpieczeństwa
# Dodaj konkretne IP/domeny do .env.dev jako DJANGO_ALLOWED_HOSTS (oddzielone przecinkami)
allowed_hosts_env = os.getenv('DJANGO_ALLOWED_HOSTS', '')
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',')]
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1',
                     '192.168.50.63', '83.168.79.109', '212.127.93.27', 'nc-dev.sowa.ch']

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
# Dodatkowe zabezpieczenia nawet w trybie dev dla publicznego dostępu
CORS_REPLACE_HTTPS_REFERER = False
HOST_SCHEME = "http://"
SECURE_PROXY_SSL_HEADER = None
SECURE_SSL_REDIRECT = False
USE_X_FORWARDED_HOST = True  # Wymagane dla nginx reverse proxy
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = None
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_FRAME_DENY = False

# Dodatkowe zabezpieczenia dla publicznego dostępu
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'  # Zmienione z False dla bezpieczeństwa
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Cross-Origin-Opener-Policy settings for development
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# CSRF Configuration for development
CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://127.0.0.1',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:8090',
    'http://127.0.0.1:8090',
    'http://192.168.50.63',
    'http://192.168.50.63:8000',
    'http://83.168.79.109',
    'http://83.168.79.109:8000',
    'http://212.127.93.27',
    'http://212.127.93.27:8000',
    'http://212.127.93.27:8001',
    'http://212.127.93.27:8090',
    'https://nc-dev.sowa.ch',
]
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False

# Debug Toolbar Configuration
# Debug Toolbar jest wyłączony dla publicznego dostępu ze względów bezpieczeństwa
# Pokazuje się tylko dla IP z INTERNAL_IPS
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = ['127.0.0.1', 'localhost', '192.168.50.63'] + \
    [ip[:-1] + '1' for ip in ips]

# Wyłącz debug toolbar dla publicznego dostępu - pokazuje się tylko dla localhost
# Używa dynamicznego DEBUG z middleware


def show_debug_toolbar(request):
    """Callback dla debug toolbar - pokazuje się tylko dla localhost."""
    return get_debug() and request.META.get('REMOTE_ADDR') in INTERNAL_IPS


DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': show_debug_toolbar,
    'SHOW_TEMPLATE_CONTEXT': True,
    'ENABLE_STACKTRACES': True,
    'SQL_WARNING_THRESHOLD': 500,  # milliseconds
}

# CORS Configuration
# Dla bezpieczeństwa wyłączamy CORS_ALLOW_ALL_ORIGINS i używamy tylko dozwolonych źródeł
CORS_ALLOW_ALL_ORIGINS = False  # Zmienione z True dla bezpieczeństwa
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8090",
    "http://127.0.0.1:8090",
    "http://192.168.50.63:8000",
    "http://83.168.79.109:8000",
    "http://212.127.93.27:8090",
    "http://212.127.93.27:8000",
    'https://nc-dev.sowa.ch',
]
# Dodatkowe dozwolone źródła z zmiennej środowiskowej
cors_origins_env = os.getenv('CORS_ALLOWED_ORIGINS', '')
if cors_origins_env:
    CORS_ALLOWED_ORIGINS.extend([origin.strip()
                                for origin in cors_origins_env.split(',')])

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

# STATICFILES_FINDERS - używamy domyślnych z base.py
# Ostrzeżenia o duplikatach (np. admin/js/cancel.js) są normalne - 
# Django używa pierwszego znalezionego pliku zgodnie z kolejnością w INSTALLED_APPS
# admin_interface jest przed django.contrib.admin, więc jego pliki mają priorytet

# Usuń WhiteNoise z middleware w development - Nginx obsługuje pliki statyczne
# DynamicDebugMiddleware jest dodawane jako pierwsze, aby kontrolować DEBUG na podstawie IP
# BotBlockerMiddleware blokuje znane boty i crawlery
MIDDLEWARE = [
    # Dodane jako pierwsze dla dynamicznego DEBUG
    'core.middleware.DynamicDebugMiddleware',
    # Blokowanie botów i crawlerów
    'core.middleware.BotBlockerMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Zawsze dodane - middleware kontroluje widoczność
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Konfiguracja testów - określa które bazy mają być używane podczas testów
# Django automatycznie tworzy testowe bazy z prefiksem test_
# Dla wielu baz danych, Django tworzy testowe wersje wszystkich baz
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Wyłącz database routers podczas testów - używamy tylko bazy default
# To rozwiązuje problemy z tworzeniem wielu testowych baz jednocześnie
if 'test' in sys.argv:
    DATABASE_ROUTERS = []  # Wyłącz routing podczas testów - wszystkie modele idą do default

    # Wyłącz cache/throttling dla testów - użyj dummy cache zamiast Redis
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

    # Wyłącz throttling dla testów (REST_FRAMEWORK jest już zdefiniowany w base.py)
    from .base import REST_FRAMEWORK as BASE_REST_FRAMEWORK
    REST_FRAMEWORK = BASE_REST_FRAMEWORK.copy()
    # Wyłącz throttling całkowicie
    REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
        'user': '1000000/day',  # Bardzo wysoki limit dla testów
        'anon': '1000000/day',
        'bulk': '1000000/min',
    }

# Konfiguracja testów dla baz danych
# Dla testów wszystkie bazy używają tej samej testowej bazy (MIRROR)
# To rozwiązuje problemy z tworzeniem wielu testowych baz jednocześnie
DATABASES['default']['TEST'] = {
    'NAME': None,  # Django automatycznie utworzy test_zzz_default
    'DEPENDENCIES': [],
}
# Pozostałe bazy używają tej samej testowej bazy co default
DATABASES['zzz_default']['TEST'] = {
    'MIRROR': 'default',  # Użyj tej samej bazy co default
}
DATABASES['MPD']['TEST'] = {
    'MIRROR': 'default',  # Użyj tej samej bazy co default dla testów
}
DATABASES['zzz_MPD']['TEST'] = {
    'MIRROR': 'default',  # Użyj tej samej bazy co default dla testów
}
DATABASES['matterhorn1']['TEST'] = {
    'MIRROR': 'default',  # Użyj tej samej bazy co default dla testów
}
DATABASES['zzz_matterhorn1']['TEST'] = {
    'MIRROR': 'default',  # Użyj tej samej bazy co default dla testów
}
DATABASES['web_agent']['TEST'] = {
    'MIRROR': 'default',  # Użyj tej samej bazy co default dla testów
}
DATABASES['zzz_web_agent']['TEST'] = {
    'MIRROR': 'default',  # Użyj tej samej bazy co default dla testów
}
DATABASES['tabu']['TEST'] = {
    'MIRROR': 'default',  # Użyj tej samej bazy co default dla testów
}
DATABASES['zzz_tabu']['TEST'] = {
    'MIRROR': 'default',  # Użyj tej samej bazy co default dla testów
}
