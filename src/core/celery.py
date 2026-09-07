import os

from celery import Celery

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    os.getenv('DJANGO_SETTINGS_MODULE', 'core.settings.dev'),
)

app = Celery('core')

# CAŁA konfiguracja Celery żyje w Django settings (CELERY_* w core/settings/base.py,
# nadpisania w prod.py). Ten plik tylko wpina appkę i wyszukuje taski.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
