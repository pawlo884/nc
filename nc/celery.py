from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')

app = Celery('nc')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Ustawienie nazwy aplikacji
app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'
app.conf.task_track_started = True
app.conf.task_ignore_result = False

app.autodiscover_tasks()


