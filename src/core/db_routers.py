import os

# Cache'owanie dostępnych baz danych - lazy evaluation
_MPD_DB = None
_MATTERHORN1_DB = None
_DEFAULT_DB = None


def _get_mpd_db():
    """Lazy evaluation dla bazy MPD"""
    global _MPD_DB
    if _MPD_DB is None:
        from django.conf import settings
        _MPD_DB = 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'
    return _MPD_DB


def _get_matterhorn1_db():
    """Lazy evaluation dla bazy matterhorn1"""
    global _MATTERHORN1_DB
    if _MATTERHORN1_DB is None:
        from django.conf import settings
        _MATTERHORN1_DB = 'zzz_matterhorn1' if 'zzz_matterhorn1' in settings.DATABASES else 'matterhorn1'
    return _MATTERHORN1_DB


def _get_default_db():
    """Lazy evaluation dla bazy default"""
    global _DEFAULT_DB
    if _DEFAULT_DB is None:
        from django.conf import settings
        if 'zzz_default' in settings.DATABASES:
            _DEFAULT_DB = 'zzz_default'
        elif 'default' in settings.DATABASES:
            _DEFAULT_DB = 'default'
        else:
            _DEFAULT_DB = False  # Używamy False zamiast None dla cache'owania
    return _DEFAULT_DB if _DEFAULT_DB is not False else None


class MPDRouter:
    """
    Router dla aplikacji MPD
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'MPD':
            return _get_mpd_db()
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'MPD':
            return _get_mpd_db()
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        if obj1._meta.app_label == 'MPD' or obj2._meta.app_label == 'MPD':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'MPD':
            return db == _get_mpd_db()
        return None


class Matterhorn1Router:
    """
    Router dla aplikacji matterhorn1
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'matterhorn1':
            return _get_matterhorn1_db()
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'matterhorn1':
            return _get_matterhorn1_db()
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'matterhorn1':
            return db == _get_matterhorn1_db()
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


class TabuRouter:
    """
    Router dla aplikacji tabu - dedykowana baza danych
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'tabu':
            from django.conf import settings
            # Development używa zzz_tabu, produkcja tabu
            if 'zzz_tabu' in settings.DATABASES:
                return 'zzz_tabu'
            return 'tabu'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'tabu':
            from django.conf import settings
            # Development używa zzz_tabu, produkcja tabu
            if 'zzz_tabu' in settings.DATABASES:
                return 'zzz_tabu'
            return 'tabu'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        if obj1._meta.app_label == 'tabu' or obj2._meta.app_label == 'tabu':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'tabu':
            from django.conf import settings
            # Development używa zzz_tabu, produkcja tabu
            if 'zzz_tabu' in settings.DATABASES:
                return db == 'zzz_tabu'
            return db == 'tabu'
        return None


class DefaultRouter:
    """
    Router dla aplikacji systemowych Django (bez web_agent)
    """
    # Lista aplikacji systemowych - tworzona raz jako atrybut klasy
    SYSTEM_APPS = frozenset([
        'admin', 'auth', 'contenttypes', 'sessions', 'django_celery_beat',
        'django_celery_results', 'admin_interface', 'colorfield'
    ])

    def db_for_read(self, model, **hints):
        # Aplikacje systemowe Django idą do bazy default
        if model._meta.app_label in self.SYSTEM_APPS:
            return _get_default_db()
        return None

    def db_for_write(self, model, **hints):
        # Aplikacje systemowe Django idą do bazy default
        if model._meta.app_label in self.SYSTEM_APPS:
            return _get_default_db()
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Aplikacje systemowe Django idą do bazy default
        if app_label in self.SYSTEM_APPS:
            default_db = _get_default_db()
            if default_db is None:
                return False
            return db == default_db
        return None
