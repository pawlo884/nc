"""
Celery taski dla dashboard_pydash – symulacja (ZF) oraz okresowe ładowanie danych dashboardu.
"""
from celery import shared_task
from django.core.cache import cache

# Cache: ostatni wynik taska (Redis)
CACHE_KEY_LAST_TASK_RESULT = 'dashboard_pydash:last_task_result'


@shared_task(bind=True, name='dashboard_pydash.run_simulation')
def run_simulation(self, user_id=None, params=None):
    """
    Symulacja „heavy” operacji (np. symulacja z parametrami).
    Zapisuje wynik w Redis (cache) i można go odczytać w Dash.
    """
    params = params or {}
    # Symulacja pracy (w praktyce: obliczenia, wywołania API, itd.)
    result = {'status': 'ok', 'task_id': self.request.id, 'params': params}
    cache.set(CACHE_KEY_LAST_TASK_RESULT, result, 300)
    return result


@shared_task(name='dashboard_pydash.refresh_dashboard_data')
def refresh_dashboard_data():
    """
    Ładuje dane dashboardu (KPI + wykresy) i zapisuje w Redis.
    Wywoływany okresowo przez Celery Beat; Dash przy budowaniu layoutu czyta z cache.
    """
    from dashboard_pydash.dash_app import (
        CACHE_KEY_DASHBOARD_PAYLOAD,
        CACHE_TIMEOUT_DASHBOARD,
        _get_dashboard_stats,
        _get_automation_chart_figure,
        _get_stock_history_figure,
        _build_demo_figure,
    )
    try:
        stats = _get_dashboard_stats()
        automation_fig = _get_automation_chart_figure()
        stock_fig = _get_stock_history_figure('mpd')
        demo_fig = _build_demo_figure(0)
        payload = {
            'stats': stats,
            'automation_fig': automation_fig.to_dict() if hasattr(automation_fig, 'to_dict') else None,
            'stock_fig': stock_fig.to_dict() if hasattr(stock_fig, 'to_dict') else None,
            'demo_fig': demo_fig.to_dict() if hasattr(demo_fig, 'to_dict') else None,
        }
        cache.set(CACHE_KEY_DASHBOARD_PAYLOAD, payload, CACHE_TIMEOUT_DASHBOARD)
        return {'status': 'ok', 'cached': True}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
