class ReadOnlyLogAdminMixin:
    """Dla adminów log/audytowych (ApiSyncLog, SagaStep, StockHistory): rekordy są
    generowane systemowo i nigdy nie powinny być ręcznie dodawane/edytowane, ale
    mogą być usuwane (czyszczenie starych wpisów)."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True


class RouterScopedQuerysetMixin:
    """Kieruje get_queryset() przez helper *_get_<app>_db() z core.db_routers zamiast
    zahardkodowanego stringa z nazwą bazy, żeby respektować podmianę na alias zzz_*
    na testach/staging (patrz core/db_routers.py)."""

    db_alias_getter = None  # ustawić na subklasie: callable zwracający alias bazy

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.db_alias_getter is not None:
            qs = qs.using(self.db_alias_getter())
        return qs
