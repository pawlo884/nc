class MatterhornRouter:
    """
    Router dla aplikacji matterhorn
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'matterhorn':
            return 'matterhorn'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'matterhorn':
            return 'matterhorn'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'matterhorn':
            return db == 'matterhorn'
        return None


class MPDRouter:
    """
    Router dla aplikacji MPD
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'MPD':
            return 'MPD'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'MPD':
            return 'MPD'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        if obj1._meta.app_label == 'MPD' or obj2._meta.app_label == 'MPD':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'MPD':
            return db == 'MPD'
        return None


class WebAgentRouter:
    """
    Router dla aplikacji web_agent
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'web_agent':
            # Na produkcji baza nazywa się 'web_agent', lokalnie 'zzz_web_agent'
            from django.conf import settings
            if 'zzz_web_agent' in settings.DATABASES:
                return 'zzz_web_agent'
            elif 'web_agent' in settings.DATABASES:
                return 'web_agent'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'web_agent':
            # Na produkcji baza nazywa się 'web_agent', lokalnie 'zzz_web_agent'
            from django.conf import settings
            if 'zzz_web_agent' in settings.DATABASES:
                return 'zzz_web_agent'
            elif 'web_agent' in settings.DATABASES:
                return 'web_agent'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        if obj1._meta.app_label == 'web_agent' or obj2._meta.app_label == 'web_agent':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'web_agent':
            # Na produkcji baza nazywa się 'web_agent', lokalnie 'zzz_web_agent'
            from django.conf import settings
            if 'zzz_web_agent' in settings.DATABASES:
                return db == 'zzz_web_agent'
            elif 'web_agent' in settings.DATABASES:
                return db == 'web_agent'
        return None


class Matterhorn1Router:
    """
    Router dla aplikacji matterhorn1
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'matterhorn1':
            return 'matterhorn1'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'matterhorn1':
            return 'matterhorn1'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'matterhorn1':
            return db == 'matterhorn1'
        return None


class DefaultRouter:
    """
    Router dla aplikacji systemowych Django
    """

    def db_for_read(self, model, **hints):
        # Aplikacje systemowe Django idą do bazy default
        system_apps = ['admin', 'auth', 'contenttypes', 'sessions', 'django_celery_beat',
                       'django_celery_results', 'admin_interface', 'colorfield']
        if model._meta.app_label in system_apps:
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        # Aplikacje systemowe Django idą do bazy default
        system_apps = ['admin', 'auth', 'contenttypes', 'sessions', 'django_celery_beat',
                       'django_celery_results', 'admin_interface', 'colorfield']
        if model._meta.app_label in system_apps:
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
            return db == 'default'
        return None
