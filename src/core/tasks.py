"""
Taski monitorujące dla Sentry Crons.
"""
from celery import shared_task

try:
    from sentry_sdk.crons import monitor as sentry_monitor
except ImportError:
    def sentry_monitor(**_kwargs):
        def decorator(func):
            return func
        return decorator


@shared_task(name='core.tasks.server_heartbeat')
@sentry_monitor(monitor_slug='nc-server-heartbeat')
def server_heartbeat():
    """
    Heartbeat serwera – uruchamiany przez Celery Beat co 5 minut.
    Sentry Crons alertuje gdy task nie wykona się w oczekiwanym czasie.
    """
    return {'status': 'ok'}
