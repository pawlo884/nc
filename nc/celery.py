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
app.conf.task_send_sent_event = True
app.conf.worker_send_task_events = True
app.conf.task_store_eager_result = True

# Konfiguracja kolejek
app.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'import_queue': {
        'exchange': 'import_queue',
        'routing_key': 'import_queue',
    },
}

# Konfiguracja workerów
app.conf.worker_prefetch_multiplier = 1  # Pobieraj tylko jedno zadanie na raz
app.conf.task_acks_late = True  # Potwierdzaj zadania dopiero po wykonaniu

# Konfiguracja dla Flower
app.conf.broker_url = 'redis://redis:6379/0'
app.conf.result_backend = 'redis://redis:6379/0'
app.conf.worker_enable_remote_control = True
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = 'UTC'

# Dodatkowe ustawienia dla lepszej komunikacji z Flower
app.conf.worker_pool_restarts = True
app.conf.worker_proc_alive_timeout = 60.0
app.conf.worker_max_tasks_per_child = 1000
app.conf.worker_state_db = os.getenv('CELERY_STATE_DB', '/var/lib/celery/worker_state')
app.conf.event_queue_ttl = 5.0
app.conf.event_queue_expires = 60.0
app.conf.worker_hijack_root_logger = False

# Dodatkowe ustawienia dla Flower
app.conf.worker_enable_remote_control = True
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True
app.conf.task_events = True
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True
app.conf.task_track_started = True
app.conf.task_ignore_result = False
app.conf.task_store_eager_result = True
app.conf.worker_enable_remote_control = True
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

app.autodiscover_tasks()


