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
    name='tabu.tasks.sync_tabu_products_update',
    max_retries=3,
    default_retry_delay=120,
)
def sync_tabu_products_update(self, update_window_minutes=15):
    """
    Aktualizacja produktów Tabu - pobiera produkty zmienione od ostatniej synchronizacji.
    Wywoływany co 10 minut przez Celery Beat.
    """
    from tabu.models import ApiSyncLog

    try:
        last_sync = (
            ApiSyncLog.objects
            .filter(
                sync_type__in=('products_full_import', 'products_update'),
                status='completed',
            )
            .order_by('-completed_at')
            .first()
        )

        if last_sync and last_sync.completed_at:
            update_from = (
                last_sync.completed_at - timedelta(minutes=5)
            ).strftime('%Y-%m-%d %H:%M:%S')
        else:
            update_from = (
                timezone.now() - timedelta(minutes=update_window_minutes)
            ).strftime('%Y-%m-%d %H:%M:%S')

        logger.info(
            f'Synchronizacja Tabu: update_from={update_from}'
        )

        call_command('sync_tabu_products', '--update-from', update_from)

        return {'status': 'ok', 'update_from': update_from}

    except Exception as exc:
        logger.exception(f'Błąd synchronizacji Tabu: {exc}')
        raise self.retry(exc=exc)
