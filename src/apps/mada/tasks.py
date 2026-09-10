"""
Taski Celery dla aplikacji Mada.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command

from core.pg_locks import advisory_lock

logger = get_task_logger(__name__)


def _fail_orphaned_running(sync_type, reason):
    """Oznacza wpisy ApiSyncLog danego sync_type utknięte w 'running' jako
    'failed'. Wołane po zdobyciu advisory locka - skoro trzymamy wyłączny
    lock, żaden inny run nie działa, więc każdy 'running' to sierota po
    workerze ubitym w poprzednim przebiegu (SIGKILL, hard time limit Celery -
    ten ostatni nie daje procesowi dojść nawet do except/finally w komendzie).
    Bez tego log wisi w 'running' w nieskończoność (brak widoczności - #267).
    """
    from django.utils import timezone
    from mada.models import ApiSyncLog

    n = ApiSyncLog.objects.filter(sync_type=sync_type, status='running').update(
        status='failed',
        completed_at=timezone.now(),
        error_message=reason,
    )
    if n:
        logger.warning(
            '🧹 mada %s: sprzątnięto %s osierocony(ch) wpis(ów) running przed nowym przebiegiem',
            sync_type, n,
        )


@shared_task(bind=True, name='mada.tasks.sync_mada_full', max_retries=2, default_retry_delay=600)
def sync_mada_full(self):
    """Pełny import katalogu Mada. Wywoływany raz dziennie przez Celery Beat."""
    with advisory_lock('mada:sync_mada_full') as acquired:
        if not acquired:
            logger.warning('Pomijam sync_mada_full: poprzedni task nadal trwa (lock aktywny).')
            return {'status': 'skipped', 'reason': 'already_running'}
        _fail_orphaned_running(
            'full_import',
            'Osierocony wpis running - poprzedni worker padł w trakcie (lock zwolniony, log nie zaktualizowany)',
        )
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
        _fail_orphaned_running(
            'partial_import',
            'Osierocony wpis running - poprzedni worker padł w trakcie (lock zwolniony, log nie zaktualizowany)',
        )
        try:
            call_command('sync_mada_partial')
            return {'status': 'ok'}
        except Exception as exc:
            logger.exception('Błąd importu przyrostowego Mada: %s', exc)
            raise self.retry(exc=exc)


@shared_task(bind=True, name='mada.tasks.watchdog_import_healthcheck')
def watchdog_import_healthcheck(self):
    """
    Watchdog - siatka bezpieczeństwa dla importów Mada utkniętych w 'running'.
    Uzupełnia sprzątanie w _fail_orphaned_running (które działa tylko na
    starcie KOLEJNEGO przebiegu): gdyby beat przestał odpalać dany task,
    stary wpis 'running' wisiałby bez końca i bez widoczności (#267).
    Uruchamiany co 5 minut przez Celery Beat (migracja 0002).
    """
    from datetime import timedelta

    from django.utils import timezone

    from mada.models import ApiSyncLog

    # Konserwatywne progi - jak w matterhorn1 (#238): import przyrostowy
    # (interwał 15 min) powinien kończyć się w kilka minut, pełny w granicach
    # godziny.
    thresholds_minutes = {
        'partial_import': 60,
        'full_import': 180,
    }
    cleaned = 0
    for sync_type, minutes in thresholds_minutes.items():
        cutoff = timezone.now() - timedelta(minutes=minutes)
        stale = ApiSyncLog.objects.filter(
            sync_type=sync_type, status='running', started_at__lt=cutoff,
        )
        for log in stale:
            age_minutes = int((timezone.now() - log.started_at).total_seconds() / 60)
            log.status = 'failed'
            log.completed_at = timezone.now()
            log.error_message = (
                f'Watchdog: brak zakończenia po {age_minutes} min '
                '(prawdopodobnie ubity worker / hard time limit Celery)'
            )
            log.save()
            logger.warning(
                '🧹 Watchdog mada: log #%s (%s) oznaczony jako failed po %s min',
                log.id, sync_type, age_minutes,
            )
            cleaned += 1

    return {'status': 'success', 'cleaned': cleaned}


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
