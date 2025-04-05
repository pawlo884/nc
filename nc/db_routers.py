class MatterhornRouter:
    """
    Router dla aplikacji matterhorn
    """
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'matterhorn':
            return 'matterhorn'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'matterhorn':
            return 'matterhorn'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Zezwalamy na relacje między obiektami z różnych baz danych
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'matterhorn':
            return db == 'matterhorn'
        # Wszystkie inne aplikacje (w tym django.contrib) migrujemy do bazy default
        return db == 'default'