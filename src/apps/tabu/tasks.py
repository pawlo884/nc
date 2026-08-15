"""
Taski Celery dla aplikacji Tabu.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name='tabu.tasks.sync_tabu_stock',
    max_retries=3,
    default_retry_delay=120,
)
def sync_tabu_stock(self):
    """
    Synchronizacja stanów magazynowych i cen Tabu (GET products/basic).
    Wywoływany co 10 minut przez Celery Beat.
    update_from = data ostatniego rozpoczęcia aktualizacji stock (ApiSyncLog),
    żeby żadne dane nie uciekły.
    """
    from tabu.models import ApiSyncLog
    from django.db import router

    lock_key = 'tabu:lock:sync_tabu_stock'
    lock_ttl_seconds = 3 * 60 * 60  # 3h awaryjnie (przy crashu lock sam wygaśnie)
    lock_value = f'{self.request.id}'

    # cache.add działa atomowo: tylko pierwszy task ustawi lock.
    if not cache.add(lock_key, lock_value, timeout=lock_ttl_seconds):
        logger.warning(
            'Pomijam sync_tabu_stock: poprzedni task nadal trwa (lock aktywny).'
        )
        return {'status': 'skipped', 'reason': 'already_running'}

    db = router.db_for_read(ApiSyncLog)
    try:
        last_sync = (
            ApiSyncLog.objects.using(db)  # type: ignore[attr-defined]
            .filter(sync_type__in=('stock_update', 'stock_full'))
            .order_by('-started_at')
            .values('started_at')
            .first()
        )
        if last_sync and last_sync.get('started_at'):
            update_from = last_sync['started_at'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            update_from = (
                timezone.now() - timedelta(hours=24)
            ).strftime('%Y-%m-%d %H:%M:%S')

        call_command('sync_tabu_stock', '--update-from', update_from)
        return {'status': 'ok', 'update_from': update_from}
    except Exception as exc:
        logger.exception(f'Błąd synchronizacji stanów Tabu: {exc}')
        raise self.retry(exc=exc)
    finally:
        # Zwolnij lock tylko jeśli nadal należy do tego taska.
        if cache.get(lock_key) == lock_value:
            cache.delete(lock_key)


@shared_task(bind=True, name='tabu.tasks.watchdog_tabu_stock_lock')
def watchdog_tabu_stock_lock(self):
    """
    Sprząta martwy lock sync_tabu_stock.

    Lock ma awaryjny TTL 3h (patrz sync_tabu_stock), ale jeśli worker padnie
    w trakcie (np. restart kontenera), `finally` nigdy się nie wykona i lock
    blokuje kolejne uruchomienia przez cały TTL mimo że nic już nie działa.
    Ten watchdog porównuje właściciela locka z listą active/reserved tasków
    na workerach i usuwa lock, jeśli okaże się martwy.
    Wywoływany co 5 minut przez Celery Beat.
    """
    lock_key = 'tabu:lock:sync_tabu_stock'
    lock_owner = cache.get(lock_key)

    if not lock_owner:
        return {'status': 'ok', 'lock_present': False}

    inspect = self.app.control.inspect(timeout=5)
    active = inspect.active()
    reserved = inspect.reserved()

    if active is None and reserved is None:
        # Workery nie odpowiedziały - nie wiemy nic pewnego, nie ryzykujemy usunięcia
        logger.warning(
            'Watchdog sync_tabu_stock: brak odpowiedzi od workerów, pomijam sprawdzanie locka.'
        )
        return {'status': 'skipped', 'reason': 'no_workers_responding'}

    running_ids = {
        task['id']
        for tasks in (active or {}).values()
        for task in tasks
    } | {
        task['id']
        for tasks in (reserved or {}).values()
        for task in tasks
    }

    if lock_owner in running_ids:
        return {'status': 'ok', 'lock_present': True, 'lock_owner': lock_owner}

    cache.delete(lock_key)
    logger.warning(
        f'🧹 Watchdog: usunięto martwy lock sync_tabu_stock '
        f'(task {lock_owner} nie jest już active/reserved na żadnym workerze).'
    )
    return {'status': 'cleaned', 'stale_lock_owner': lock_owner}


@shared_task(
    bind=True,
    name='tabu.tasks.sync_tabu_products_update',
    max_retries=3,
    default_retry_delay=120,
    soft_time_limit=9900,  # 2h 45m
    time_limit=10800,  # 3h hard limit
)
def sync_tabu_products_update(self):
    """
    Sprawdza nowe produkty Tabu: max(api_id)+1 w bazie, GET products/{id}.
    404 = brak nowych, 200 = import i sprawdź kolejne.
    Wywoływany co kilka godzin (np. 4h).
    """
    try:
        call_command('sync_tabu_new_products')
        return {'status': 'ok'}
    except Exception as exc:
        logger.exception(f'Błąd sprawdzania nowych produktów Tabu: {exc}')
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name='tabu.tasks.sync_tabu_categories',
    max_retries=3,
    default_retry_delay=120,
)
def sync_tabu_categories_task(self):
    """
    Synchronizacja kategorii z API Tabu (GET products/categories).
    Wywoływany co tydzień – sprawdza czy są nowe kategorie.
    """
    try:
        logger.info('Rozpoczynam synchronizację kategorii Tabu')
        call_command('sync_tabu_categories')
        logger.info('Synchronizacja kategorii Tabu zakończona')
        return {'status': 'ok'}
    except Exception as exc:
        logger.exception(f'Błąd synchronizacji kategorii Tabu: {exc}')
        raise self.retry(exc=exc)
