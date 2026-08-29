"""
Taski Celery dla aplikacji Tabu.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

from core.pg_locks import advisory_lock

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

    # Advisory lock PostgreSQL: zwalnia się sam, gdy worker padnie (bez TTL, bez watchdoga).
    with advisory_lock('tabu:sync_tabu_stock') as acquired:
        if not acquired:
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


@shared_task(bind=True, name='tabu.tasks.watchdog_tabu_stock_lock')
def watchdog_tabu_stock_lock(self):
    """
    No-op. Blokada sync_tabu_stock to teraz PostgreSQL advisory lock
    (patrz core.pg_locks), który zwalnia się automatycznie po padzie workera -
    nie ma "martwych" locków do sprzątania.

    Task i jego PeriodicTask (migracja tabu 0013) zostają zarejestrowane dla
    kompatybilności; kolejny release może je usunąć osobną migracją.
    """
    return {'status': 'ok', 'reason': 'advisory_lock_auto_release_noop'}


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
