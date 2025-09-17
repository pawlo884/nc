import os
from celery import Celery

# Ustaw domyślne ustawienia Django dla Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')

app = Celery('nc')

# Użyj stringa zamiast obiektu, aby worker nie musiał serializować konfiguracji
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatyczne wyszukiwanie tasków w aplikacjach Django
app.autodiscover_tasks()

# Konfiguracja tasków
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Warsaw',
    enable_utc=True,
)

# Konfiguracja routingu tasków
app.conf.task_routes = {
    'matterhorn1.tasks.*': {'queue': 'matterhorn1_queue'},
}

# Konfiguracja retry
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True

# Konfiguracja beat - używaj Django periodic tasks zamiast tego
# app.conf.beat_schedule = {}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
