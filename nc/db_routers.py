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