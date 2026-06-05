"""
Konfiguracja Sentry – monitoring błędów Django, Celery i Redis.
Aktywuje się tylko gdy ustawiono SENTRY_DSN.
"""
import logging
import os

logger = logging.getLogger(__name__)


def _traces_sampler(sampling_context):
    """Pomiń health check w performance traces."""
    default_rate = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1'))
    transaction_context = sampling_context.get('transaction_context') or {}
    name = transaction_context.get('name', '')
    if name in ('/health/', '/health'):
        return 0.0
    return default_rate


def _before_send(event, hint):
    """Filtruj znane, nieistotne wyjątki."""
    if 'exc_info' in hint:
        exc_type, _, _ = hint['exc_info']
        if exc_type.__name__ in ('DisallowedHost', 'SuspiciousOperation'):
            return None
    return event


def init_sentry():
    """Inicjalizuj Sentry SDK jeśli SENTRY_DSN jest ustawiony."""
    dsn = os.getenv('SENTRY_DSN', '').strip()
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
    except ImportError:
        logger.warning('sentry-sdk nie jest zainstalowany – pomijam inicjalizację Sentry')
        return

    environment = os.getenv(
        'SENTRY_ENVIRONMENT',
        os.getenv('DJANGO_ENV', 'development'),
    )
    release = os.getenv('SENTRY_RELEASE', '').strip() or None

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(monitor_beat_tasks=True),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        traces_sampler=_traces_sampler,
        profiles_sample_rate=float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0')),
        send_default_pii=os.getenv('SENTRY_SEND_DEFAULT_PII', 'true').lower() in (
            '1', 'true', 'yes', 'on',
        ),
        before_send=_before_send,
        enable_tracing=True,
    )
    logger.info('Sentry zainicjalizowany (environment=%s)', environment)
