"""
Taski Celery dla aplikacji Mada.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.core.management import call_command

logger = get_task_logger(__name__)

_LOCK_TTL_SECONDS = 3 * 60 * 60  # 3h awaryjnie (przy crashu lock sam wygaśnie)


@shared_task(bind=True, name='mada.tasks.sync_mada_full', max_retries=2, default_retry_delay=600)
def sync_mada_full(self):
    """Pełny import katalogu Mada. Wywoływany raz dziennie przez Celery Beat."""
    lock_key = 'mada:lock:sync_mada_full'
    if not cache.add(lock_key, self.request.id, timeout=_LOCK_TTL_SECONDS):
        logger.warning('Pomijam sync_mada_full: poprzedni task nadal trwa (lock aktywny).')
        return {'status': 'skipped', 'reason': 'already_running'}

    try:
        call_command('sync_mada_full')
        return {'status': 'ok'}
    except Exception as exc:
        logger.exception('Błąd pełnego importu Mada: %s', exc)
        raise self.retry(exc=exc)
    finally:
        cache.delete(lock_key)


@shared_task(bind=True, name='mada.tasks.sync_mada_partial', max_retries=3, default_retry_delay=120)
def sync_mada_partial(self):
    """Import przyrostowy Mada (pliki partial). Wywoływany co kilkanaście minut."""
    lock_key = 'mada:lock:sync_mada_partial'
    if not cache.add(lock_key, self.request.id, timeout=_LOCK_TTL_SECONDS):
        logger.warning('Pomijam sync_mada_partial: poprzedni task nadal trwa (lock aktywny).')
        return {'status': 'skipped', 'reason': 'already_running'}

    try:
        call_command('sync_mada_partial')
        return {'status': 'ok'}
    except Exception as exc:
        logger.exception('Błąd importu przyrostowego Mada: %s', exc)
        raise self.retry(exc=exc)
    finally:
        cache.delete(lock_key)
