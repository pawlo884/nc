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

# Konfiguracja routingu tasków - routing do odpowiednich kolejek
app.conf.task_routes = {
    # ML taski → kolejka 'ml' (osobny worker z PyTorch)
    'web_agent.tasks.generate_embeddings': {'queue': 'ml'},
    'web_agent.tasks.semantic_search': {'queue': 'ml'},
    'web_agent.tasks.generate_product_embeddings': {'queue': 'ml'},
    'web_agent.tasks.find_similar_products': {'queue': 'ml'},

    # Task importu trafia do kolejki 'import'
    'matterhorn1.tasks.full_import_and_update': {'queue': 'import'},

    # Pozostałe taski używają domyślnej kolejki
    'matterhorn1.tasks.*': {'queue': 'default'},
    'web_agent.tasks.*': {'queue': 'default'},
}

# Konfiguracja retry
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True

# Konfiguracja heartbeat
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True
app.conf.worker_hijack_root_logger = False
app.conf.worker_log_color = False

# Konfiguracja heartbeat i monitoringu
app.conf.worker_heartbeat = 30  # heartbeat co 30 sekund
app.conf.worker_pool_restarts = True
app.conf.worker_prefetch_multiplier = 1

# Konfiguracja beat - używaj Django periodic tasks zamiast tego
# app.conf.beat_schedule = {}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
