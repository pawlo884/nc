from celery import Celery
import os

# Ustawienie odpowiedniego pliku ustawień w zależności od środowiska
environment = os.getenv('DJANGO_ENV', 'dev')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'nc.settings.{environment}')

app = Celery('nc')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Ustawienie nazwy aplikacji
app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

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
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = True
app.conf.worker_max_memory_per_child = 200000  # 200MB limit pamięci na worker
app.conf.worker_max_tasks_per_child = 50  # Restart worker po 50 zadaniach

# Konfiguracja brokera i backendu
redis_password = os.getenv('REDIS_PASSWORD', 'prod_password')
app.conf.broker_url = f'redis://:{redis_password}@redis:6379/0'
app.conf.result_backend = f'redis://:{redis_password}@redis:6379/0'

# Konfiguracja serializacji
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']

# Konfiguracja strefy czasowej
app.conf.timezone = 'Europe/Warsaw'

# Konfiguracja monitorowania i zdarzeń
app.conf.worker_enable_remote_control = True
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True
app.conf.task_track_started = True
app.conf.task_ignore_result = False
app.conf.task_store_eager_result = True
app.conf.task_events = True

# Konfiguracja workerów - optymalizacja pamięci
app.conf.worker_pool_restarts = True
app.conf.worker_proc_alive_timeout = 60.0
app.conf.worker_state_db = os.getenv(
    'CELERY_STATE_DB', '/var/lib/celery/worker_state')
app.conf.event_queue_ttl = 5.0
app.conf.event_queue_expires = 60.0
app.conf.worker_hijack_root_logger = False

# Dodatkowe ustawienia dla Flower - usunięto duplikaty
app.conf.worker_enable_remote_control = True
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True
app.conf.task_events = True
app.conf.task_track_started = True
app.conf.task_ignore_result = False
app.conf.task_store_eager_result = True

# Konfiguracja heartbeatów i połączenia
app.conf.broker_heartbeat = 60  # Zwiększony interwał heartbeat do 60 sekund
app.conf.broker_connection_timeout = 120  # Zwiększony timeout do 120 sekund
app.conf.broker_connection_retry = True
app.conf.broker_connection_max_retries = 30  # Zwiększona liczba prób
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_pool_limit = 20  # Zwiększony limit połączeń w puli
app.conf.broker_transport_options = {
    'visibility_timeout': 3600,  # 1 godzina
    'socket_timeout': 60,
    'socket_connect_timeout': 60,
    'socket_keepalive': True,
    'health_check_interval': 30,
    'heartbeat_interval': 60,
    'heartbeat_timeout': 120,
}

app.autodiscover_tasks()
