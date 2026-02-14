import os
from celery import Celery

# Ustaw domyślne ustawienia Django dla Celery
# Użyj zmiennej środowiskowej lub domyślnie dev
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'core.settings.dev'))

app = Celery('core')

# Użyj stringa zamiast obiektu, aby worker nie musiał serializować konfiguracji
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatyczne wyszukiwanie tasków w aplikacjach Django
app.autodiscover_tasks()

# Explicit import tasków (force registration)
app.autodiscover_tasks(['MPD', 'matterhorn1', 'web_agent', 'tabu'])

# Konfiguracja tasków
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Warsaw',
    enable_utc=True,
    # Wyłącz próby zmiany uprawnień - kontener już działa jako użytkownik 999:999
    worker_drop_privileges=False,
)

# Konfiguracja routingu tasków - routing do odpowiednich kolejek
app.conf.task_routes = {
    # Task importu trafia do kolejki 'import'
    'matterhorn1.tasks.full_import_and_update': {'queue': 'import'},

    # Pozostałe taski używają domyślnej kolejki
    'matterhorn1.tasks.*': {'queue': 'default'},
    'MPD.tasks.*': {'queue': 'default'},
    'tabu.tasks.*': {'queue': 'default'},
}

# Konfiguracja retry
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = False  # Zmienione na False dla stabilności

# Konfiguracja heartbeat
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True
app.conf.worker_hijack_root_logger = False
app.conf.worker_log_color = False

# Konfiguracja heartbeat i monitoringu
app.conf.worker_heartbeat = 0  # Wyłączony heartbeat dla stabilności
app.conf.worker_pool_restarts = True
app.conf.worker_prefetch_multiplier = 1
app.conf.worker_disable_rate_limits = True  # Wyłącz limity dla stabilności

# Konfiguracja beat - używaj Django periodic tasks zamiast tego
# app.conf.beat_schedule = {}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Konfiguracja logowania dla Celery
import logging
logging.getLogger('celery').setLevel(logging.INFO)
logging.getLogger('celery.worker').setLevel(logging.INFO)
logging.getLogger('celery.task').setLevel(logging.INFO)
