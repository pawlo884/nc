from django.apps import AppConfig


class ProducerCatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'producer_catalog'
    verbose_name = 'Katalog producenta'
    verbose_name_plural = 'Katalogi producentów'
