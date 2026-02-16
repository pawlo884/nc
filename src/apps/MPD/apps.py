from django.apps import AppConfig


class MdpConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'MPD'

    def ready(self):
        import MPD.signals  # noqa
        from MPD.source_adapters.registry import register_default_adapters
        register_default_adapters()
