import os
from django.conf import settings

# Cache'owanie wartości środowiska - wywoływane tylko raz przy starcie
_DJANGO_ENV = os.getenv('DJANGO_ENV')
_IS_PROD = _DJANGO_ENV == 'prod'


class MPDRouter:
    """
    Router dla aplikacji MPD
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'MPD':
            if _IS_PROD and 'MPD' in settings.DATABASES:
                return 'MPD'
            if 'zzz_MPD' in settings.DATABASES:
                return 'zzz_MPD'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'MPD':
            if _IS_PROD and 'MPD' in settings.DATABASES:
                return 'MPD'
            if 'zzz_MPD' in settings.DATABASES:
                return 'zzz_MPD'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        if obj1._meta.app_label == 'MPD' or obj2._meta.app_label == 'MPD':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'MPD':
            if _IS_PROD and 'MPD' in settings.DATABASES:
                return db == 'MPD'
            if 'zzz_MPD' in settings.DATABASES:
                return db == 'zzz_MPD'
        return None


class Matterhorn1Router:
    """
    Router dla aplikacji matterhorn1
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'matterhorn1':
            # Na produkcji używaj 'matterhorn1', lokalnie 'zzz_matterhorn1'
            if _IS_PROD and 'matterhorn1' in settings.DATABASES:
                return 'matterhorn1'
            if 'zzz_matterhorn1' in settings.DATABASES:
                return 'zzz_matterhorn1'
            if 'matterhorn1' in settings.DATABASES:
                return 'matterhorn1'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'matterhorn1':
            # Na produkcji używaj 'matterhorn1', lokalnie 'zzz_matterhorn1'
            if _IS_PROD and 'matterhorn1' in settings.DATABASES:
                return 'matterhorn1'
            if 'zzz_matterhorn1' in settings.DATABASES:
                return 'zzz_matterhorn1'
            if 'matterhorn1' in settings.DATABASES:
                return 'matterhorn1'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'matterhorn1':
            # Na produkcji używaj 'matterhorn1', lokalnie 'zzz_matterhorn1'
            if _IS_PROD and 'matterhorn1' in settings.DATABASES:
                return db == 'matterhorn1'
            if 'zzz_matterhorn1' in settings.DATABASES:
                return db == 'zzz_matterhorn1'
            if 'matterhorn1' in settings.DATABASES:
                return db == 'matterhorn1'
        return None


class DefaultRouter:
    """
    Router dla aplikacji systemowych Django
    """
    # Lista aplikacji systemowych - tworzona tylko raz jako atrybut klasy
    SYSTEM_APPS = frozenset([
        'admin', 'auth', 'contenttypes', 'sessions', 'django_celery_beat',
        'django_celery_results', 'admin_interface', 'colorfield'
    ])

    def db_for_read(self, model, **hints):
        # Aplikacje systemowe Django idą do bazy default
        if model._meta.app_label in self.SYSTEM_APPS:
            # Na produkcji używaj 'default', lokalnie 'zzz_default'
            if 'zzz_default' in settings.DATABASES:
                return 'zzz_default'
            elif 'default' in settings.DATABASES:
                return 'default'
        return None

    def db_for_write(self, model, **hints):
        # Aplikacje systemowe Django idą do bazy default
        if model._meta.app_label in self.SYSTEM_APPS:
            # Na produkcji używaj 'default', lokalnie 'zzz_default'
            if 'zzz_default' in settings.DATABASES:
                return 'zzz_default'
            elif 'default' in settings.DATABASES:
                return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Aplikacje systemowe Django idą do bazy default
        if app_label in self.SYSTEM_APPS:
            # Na produkcji używaj 'default', lokalnie 'zzz_default'
            if 'zzz_default' in settings.DATABASES:
                return db == 'zzz_default'
            elif 'default' in settings.DATABASES:
                return db == 'default'
            # Jeśli nie ma bazy default, nie pozwalaj na migracje
            return False

        return None
