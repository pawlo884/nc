from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-zlntqh&x6vv%$+87ycj-)=#isuos^f_h4w%e#9+&w%xd5mph)!')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', '164.92.251.171']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

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