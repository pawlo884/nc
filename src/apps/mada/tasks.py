"""
Taski Celery dla aplikacji Mada.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command

from core.pg_locks import advisory_lock

logger = get_task_logger(__name__)


@shared_task(bind=True, name='mada.tasks.sync_mada_full', max_retries=2, default_retry_delay=600)
def sync_mada_full(self):
    """Pełny import katalogu Mada. Wywoływany raz dziennie przez Celery Beat."""
    with advisory_lock('mada:sync_mada_full') as acquired:
        if not acquired:
            logger.warning('Pomijam sync_mada_full: poprzedni task nadal trwa (lock aktywny).')
            return {'status': 'skipped', 'reason': 'already_running'}
        try:
            call_command('sync_mada_full')
            return {'status': 'ok'}
        except Exception as exc:
            logger.exception('Błąd pełnego importu Mada: %s', exc)
            raise self.retry(exc=exc)


@shared_task(bind=True, name='mada.tasks.sync_mada_partial', max_retries=3, default_retry_delay=120)
def sync_mada_partial(self):
    """Import przyrostowy Mada (pliki partial). Wywoływany co kilkanaście minut."""
    with advisory_lock('mada:sync_mada_partial') as acquired:
        if not acquired:
            logger.warning('Pomijam sync_mada_partial: poprzedni task nadal trwa (lock aktywny).')
            return {'status': 'skipped', 'reason': 'already_running'}
        try:
            call_command('sync_mada_partial')
            return {'status': 'ok'}
        except Exception as exc:
            logger.exception('Błąd importu przyrostowego Mada: %s', exc)
            raise self.retry(exc=exc)


@shared_task(bind=True, name='mada.tasks.cleanup_empty_products', max_retries=2, default_retry_delay=600)
def cleanup_empty_products(self):
    """
    Usuwa puste produkty Mada (bez NAME w feedzie, nigdy nie zmapowane do MPD).
    Wywoływany raz dziennie, po pełnym imporcie.
    """
    with advisory_lock('mada:cleanup_empty_products') as acquired:
        if not acquired:
            logger.warning('Pomijam cleanup_empty_products: poprzedni task nadal trwa (lock aktywny).')
            return {'status': 'skipped', 'reason': 'already_running'}
        try:
            call_command('cleanup_empty_mada_products')
            return {'status': 'ok'}
        except Exception as exc:
            logger.exception('Błąd czyszczenia pustych produktów Mada: %s', exc)
            raise self.retry(exc=exc)
