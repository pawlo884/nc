import os


class MPDRouter:
    """
    Router dla aplikacji MPD
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'MPD':
            from django.conf import settings
            # Development używa zzz_MPD, produkcja MPD
            if 'zzz_MPD' in settings.DATABASES:
                return 'zzz_MPD'
            return 'MPD'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'MPD':
            from django.conf import settings
            # Development używa zzz_MPD, produkcja MPD
            if 'zzz_MPD' in settings.DATABASES:
                return 'zzz_MPD'
            return 'MPD'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        if obj1._meta.app_label == 'MPD' or obj2._meta.app_label == 'MPD':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'MPD':
            from django.conf import settings
            # Development używa zzz_MPD, produkcja MPD
            if 'zzz_MPD' in settings.DATABASES:
                return db == 'zzz_MPD'
            return db == 'MPD'
        return None


class Matterhorn1Router:
    """
    Router dla aplikacji matterhorn1
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'matterhorn1':
            from django.conf import settings
            # Development używa zzz_matterhorn1, produkcja matterhorn1
            if 'zzz_matterhorn1' in settings.DATABASES:
                return 'zzz_matterhorn1'
            return 'matterhorn1'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'matterhorn1':
            from django.conf import settings
            # Development używa zzz_matterhorn1, produkcja matterhorn1
            if 'zzz_matterhorn1' in settings.DATABASES:
                return 'zzz_matterhorn1'
            return 'matterhorn1'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'matterhorn1':
            from django.conf import settings
            # Development używa zzz_matterhorn1, produkcja matterhorn1
            if 'zzz_matterhorn1' in settings.DATABASES:
                return db == 'zzz_matterhorn1'
            return db == 'matterhorn1'
        return None


class WebAgentRouter:
    """
    Router dla aplikacji web_agent - dedykowana baza danych
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'web_agent':
            from django.conf import settings
            # Development używa zzz_web_agent, produkcja web_agent
            if 'zzz_web_agent' in settings.DATABASES:
                return 'zzz_web_agent'
            return 'web_agent'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'web_agent':
            from django.conf import settings
            # Development używa zzz_web_agent, produkcja web_agent
            if 'zzz_web_agent' in settings.DATABASES:
                return 'zzz_web_agent'
            return 'web_agent'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        if obj1._meta.app_label == 'web_agent' or obj2._meta.app_label == 'web_agent':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'web_agent':
            from django.conf import settings
            # Development używa zzz_web_agent, produkcja web_agent
            if 'zzz_web_agent' in settings.DATABASES:
                return db == 'zzz_web_agent'
            return db == 'web_agent'
        return None


class DefaultRouter:
    """
    Router dla aplikacji systemowych Django (bez web_agent)
    """

    def db_for_read(self, model, **hints):
        # Aplikacje systemowe Django idą do bazy default
        system_apps = ['admin', 'auth', 'contenttypes', 'sessions', 'django_celery_beat',
                      'django_celery_results', 'admin_interface', 'colorfield']
        if model._meta.app_label in system_apps:
            # Na produkcji używaj 'default', lokalnie 'zzz_default'
            from django.conf import settings
            if 'zzz_default' in settings.DATABASES:
                return 'zzz_default'
            elif 'default' in settings.DATABASES:
                return 'default'
        return None

    def db_for_write(self, model, **hints):
        # Aplikacje systemowe Django idą do bazy default
        system_apps = ['admin', 'auth', 'contenttypes', 'sessions', 'django_celery_beat',
                      'django_celery_results', 'admin_interface', 'colorfield']
        if model._meta.app_label in system_apps:
            # Na produkcji używaj 'default', lokalnie 'zzz_default'
            from django.conf import settings
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
        system_apps = ['admin', 'auth', 'contenttypes', 'sessions', 'django_celery_beat',
                      'django_celery_results', 'admin_interface', 'colorfield']
        if app_label in system_apps:
            # Na produkcji używaj 'default', lokalnie 'zzz_default'
            from django.conf import settings
            if 'zzz_default' in settings.DATABASES:
                return db == 'zzz_default'
            elif 'default' in settings.DATABASES:
                return db == 'default'
            # Jeśli nie ma bazy default, nie pozwalaj na migracje
            return False

        return None
