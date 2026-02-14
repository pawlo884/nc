"""
Taski Celery dla aplikacji Tabu.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
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

    db = router.db_for_read(ApiSyncLog)
    last_sync = (
        ApiSyncLog.objects.using(db)
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

    try:
        call_command('sync_tabu_stock', '--update-from', update_from)
        return {'status': 'ok', 'update_from': update_from}
    except Exception as exc:
        logger.exception(f'Błąd synchronizacji stanów Tabu: {exc}')
        raise self.retry(exc=exc)


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
        call_command(
            'sync_tabu_new_products',
            stop_after_404=5,
        )
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
