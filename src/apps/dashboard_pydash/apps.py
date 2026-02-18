from django.apps import AppConfig


class DashboardPydashConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard_pydash'
    verbose_name = 'Dashboard PyDash (ZF practice)'

    def ready(self):
        import dashboard_pydash.dash_app  # noqa: F401 – rejestracja aplikacji Dash
