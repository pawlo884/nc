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

# Routing tasków do kolejek. Workery:
#   celery-fast  (-Q default)       — częste/krótkie: stock tracking, watchdog,
#                                     most stanów MPD, synci przyrostowe, eksport XML
#   celery-heavy (-Q import,heavy)  — długie/pamięciożerne, żeby nie blokowały fast
#                                     (import przed heavy = priorytet dla full_import)
#   celery-beat / flower / celery-ml (szkielet, -Q ml)
# UWAGA: druga kopia tej mapy jest w settings/base.py (CELERY_TASK_ROUTES) —
# trzymać zsynchronizowane (dedup zaplanowany osobno).
app.conf.task_default_queue = 'default'  # cokolwiek bez reguły → celery-fast
app.conf.task_routes = {
    # Ciężki import z pipeline'em — własna kolejka 'import' (celery-heavy)
    'matterhorn1.tasks.full_import_and_update': {'queue': 'import'},

    # Długie / rzadkie → 'heavy' (celery-heavy, concurrency 2 → nie blokują full_import)
    'tabu.tasks.sync_tabu_products_update': {'queue': 'heavy'},
    'mada.tasks.sync_mada_full': {'queue': 'heavy'},
    'web_agent.tasks.*': {'queue': 'heavy'},
    'MPD.tasks.link_all_products_to_new_source': {'queue': 'heavy'},

    # Reszta → 'default' (celery-fast)
    'matterhorn1.tasks.*': {'queue': 'default'},
    'MPD.tasks.*': {'queue': 'default'},
    'tabu.tasks.*': {'queue': 'default'},
    'mada.tasks.*': {'queue': 'default'},
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
