"""
Aplikacja Plotly Dash – wykresy i KPI z danych aplikacji NC.

Wyświetla: KPI (MPD, matterhorn1, web_agent, audit), wykres uruchomień automatyzacji,
demo wykres z cache (Redis).
"""
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
from django_plotly_dash import DjangoDash
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

# Redis cache: klucz dla danych wykresu (ćwiczenie cache)
CACHE_KEY_CHART_DATA = 'dashboard_pydash:chart_data'
CACHE_TIMEOUT = 60

# Cache: payload z Celery (stats + figury) – task refresh_dashboard_data zapisuje
CACHE_KEY_DASHBOARD_PAYLOAD = 'dashboard_pydash:cached_payload'
CACHE_TIMEOUT_DASHBOARD = 600  # 10 min

app = DjangoDash('NCDashboard', suppress_callback_exceptions=True)


def _get_dashboard_stats():
    """Pobiera liczby z baz (KPI). Obsługa braku tabel / błędów."""
    stats = {}
    try:
        from MPD.models import Products
        stats['mpd_products'] = Products.objects.count()
    except Exception:
        stats['mpd_products'] = '—'
    try:
        from matterhorn1.models import Product
        stats['matterhorn1_products'] = Product.objects.count()
    except Exception:
        stats['matterhorn1_products'] = '—'
    try:
        from web_agent.models import AutomationRun
        stats['automation_runs'] = AutomationRun.objects.count()
        stats['automation_completed'] = AutomationRun.objects.filter(status='completed').count()
    except Exception:
        stats['automation_runs'] = '—'
        stats['automation_completed'] = '—'
    try:
        from dashboard_pydash.models import DashAuditLog
        stats['audit_entries'] = DashAuditLog.objects.count()
    except Exception:
        stats['audit_entries'] = '—'
    return stats


def _get_stock_history_figure(source):
    """
    Wykres: zmiany stanów magazynowych w czasie (ostatnie 14 dni).
    source: 'mpd' | 'matterhorn1' | 'tabu'
    """
    from django.db.models import Count, Sum
    from django.db.models.functions import TruncDate
    since = timezone.now() - timedelta(days=14)
    days_list = []
    counts_list = []
    increases_list = []
    decreases_list = []
    title = 'Stany magazynowe – zmiany w czasie'
    try:
        if source == 'mpd':
            from MPD.models import StockHistory as MPDStockHistory
            per_day = (
                MPDStockHistory.objects.filter(change_date__gte=since)
                .annotate(day=TruncDate('change_date'))
                .values('day')
                .annotate(count=Count('id'))
                .order_by('day')
            )
            for x in per_day:
                days_list.append(x['day'].strftime('%Y-%m-%d'))
                counts_list.append(x['count'])
                increases_list.append(0)
                decreases_list.append(0)
            title = 'MPD – zmiany stanów magazynowych (ostatnie 14 dni)'
        elif source == 'matterhorn1':
            from matterhorn1.models import StockHistory as MH1StockHistory
            per_day = (
                MH1StockHistory.objects.filter(timestamp__gte=since)
                .annotate(day=TruncDate('timestamp'))
                .values('day')
                .annotate(count=Count('id'), diff_sum=Sum('stock_change'))
                .order_by('day')
            )
            for x in per_day:
                days_list.append(x['day'].strftime('%Y-%m-%d'))
                counts_list.append(x['count'])
                d = x.get('diff_sum') or 0
                try:
                    d = int(d)
                    increases_list.append(d if d > 0 else 0)
                    decreases_list.append(-d if d < 0 else 0)
                except (TypeError, ValueError):
                    increases_list.append(0)
                    decreases_list.append(0)
            title = 'Matterhorn1 – zmiany stanów magazynowych (ostatnie 14 dni)'
        elif source == 'tabu':
            from tabu.models import StockHistory as TabuStockHistory
            per_day = (
                TabuStockHistory.objects.filter(timestamp__gte=since)
                .annotate(day=TruncDate('timestamp'))
                .values('day')
                .annotate(count=Count('id'), diff_sum=Sum('stock_change'))
                .order_by('day')
            )
            for x in per_day:
                days_list.append(x['day'].strftime('%Y-%m-%d'))
                counts_list.append(x['count'])
                d = x.get('diff_sum') or 0
                try:
                    d = int(d)
                    increases_list.append(d if d > 0 else 0)
                    decreases_list.append(-d if d < 0 else 0)
                except (TypeError, ValueError):
                    increases_list.append(0)
                    decreases_list.append(0)
            title = 'Tabu – zmiany stanów magazynowych (ostatnie 14 dni)'
        else:
            return go.Figure(layout=dict(title='Wybierz źródło', margin=dict(t=40, b=40)))
        if not days_list:
            empty_title = f'{title} – brak wpisów w ostatnich 14 dniach'
            return go.Figure(layout=dict(
                title=empty_title,
                margin=dict(t=60, b=40, l=50, r=50),
                annotations=[dict(text='Brak danych. Wybierz inne źródło lub poczekaj na synchronizację.', x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False, font=dict(size=14))],
            ))
        fig = go.Figure()
        fig.add_trace(go.Bar(x=days_list, y=counts_list, name='Liczba zmian', marker_color='#636efa'))
        if (increases_list and any(increases_list)) or (decreases_list and any(decreases_list)):
            fig.add_trace(go.Scatter(x=days_list, y=increases_list, name='Suma wzrostów', mode='lines+markers', line=dict(color='#00cc96')))
            fig.add_trace(go.Scatter(x=days_list, y=[-v for v in decreases_list], name='Suma spadków', mode='lines+markers', line=dict(color='#ef553b')))
        fig.update_layout(
            title=title,
            xaxis_title='Data',
            yaxis_title='Liczba zdarzeń',
            margin=dict(l=50, r=50, t=60, b=80),
            xaxis_tickangle=-45,
            showlegend=True,
        )
        return fig
    except Exception:
        return go.Figure(layout=dict(
            title=f'Stany magazynowe ({source})',
            margin=dict(t=60, b=40, l=50, r=50),
            annotations=[dict(text=f'Brak danych lub błąd połączenia z bazą.', x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False, font=dict(size=14))],
        ))


def _get_automation_chart_figure():
    """Wykres: uruchomienia automatyzacji (web_agent) z ostatnich 14 dni."""
    try:
        from web_agent.models import AutomationRun
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        since = timezone.now() - timedelta(days=14)
        per_day = (
            AutomationRun.objects.filter(started_at__gte=since)
            .annotate(day=TruncDate('started_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        days = [x['day'].strftime('%Y-%m-%d') for x in per_day]
        counts = [x['count'] for x in per_day]
        if not days:
            return go.Figure(layout=dict(title='Uruchomienia automatyzacji (ostatnie 14 dni)', margin=dict(t=40, b=40)))
        fig = go.Figure(
            data=[go.Bar(x=days, y=counts, name='Uruchomienia')],
            layout=dict(
                title='Uruchomienia automatyzacji (ostatnie 14 dni)',
                xaxis_title='Data',
                yaxis_title='Liczba',
                margin=dict(l=50, r=30, t=50, b=80),
                xaxis_tickangle=-45,
            ),
        )
        return fig
    except Exception:
        return go.Figure(layout=dict(title='Brak danych (web_agent)', margin=dict(t=40, b=40)))


def _get_chart_data(use_cache=True):
    """Dane demo (Redis cache)."""
    if use_cache:
        try:
            data = cache.get(CACHE_KEY_CHART_DATA)
            if data is not None:
                return data
        except Exception:
            pass
    data = [
        {'x': list(range(1, 11)), 'y': [2, 4, 3, 6, 5, 8, 7, 9, 10, 8], 'name': 'Seria A'},
        {'x': list(range(1, 11)), 'y': [1, 3, 2, 5, 4, 7, 6, 8, 9, 7], 'name': 'Seria B'},
    ]
    try:
        cache.set(CACHE_KEY_CHART_DATA, data, CACHE_TIMEOUT)
    except Exception:
        pass
    return data


def _build_demo_figure(series_index=0):
    data = _get_chart_data()
    series = data[int(series_index) % len(data)] if data else {}
    if not series:
        return go.Figure(layout=dict(title='Brak danych'))
    return go.Figure(
        data=[go.Scatter(x=series.get('x', []), y=series.get('y', []), mode='lines+markers')],
        layout=dict(
            title=f"Demo – {series.get('name', 'Dane')} (Redis cache)",
            xaxis_title='X', yaxis_title='Y',
            margin=dict(l=40, r=40, t=50, b=40),
        ),
    )


# Layout: dane z cache (Celery) lub obliczone w procesie (fallback)
def _fig_from_dict(d):
    """Odtwarza go.Figure z dict (zapis z Celery)."""
    if not d or not isinstance(d, dict):
        return go.Figure(layout=dict(title='Błąd ładowania', margin=dict(t=40, b=40)))
    try:
        return go.Figure(d)
    except Exception:
        try:
            return go.Figure(data=d.get('data'), layout=d.get('layout'))
        except Exception:
            return go.Figure(layout=dict(title='Błąd ładowania', margin=dict(t=40, b=40)))


def _safe_stats():
    try:
        return _get_dashboard_stats()
    except Exception:
        return {'mpd_products': '—', 'matterhorn1_products': '—', 'automation_runs': '—', 'audit_entries': '—'}


def _safe_fig(fn, *args):
    try:
        return fn(*args)
    except Exception:
        return go.Figure(layout=dict(title='Błąd ładowania', margin=dict(t=40, b=40)))


def _load_layout_data():
    """
    Dane do layoutu: tylko KPI (lekkie). Wykresy = puste – callbacki uzupełnią po interakcji.
    Dzięki temu pierwszy response jest mały i strona się ładuje (bez timeoutu / problemów z JSON).
    """
    fallback_stats = {'mpd_products': '—', 'matterhorn1_products': '—', 'automation_runs': '—', 'audit_entries': '—'}
    try:
        payload = cache.get(CACHE_KEY_DASHBOARD_PAYLOAD)
        if payload and isinstance(payload, dict):
            stats = payload.get('stats') or _safe_stats()
        else:
            stats = _safe_stats()
    except Exception:
        stats = fallback_stats
    # Puste figury przy starcie – dane w callbackach (dropdown)
    empty = go.Figure(layout=dict(title='Wybierz z listy lub zmień źródło', margin=dict(t=40, b=40)))
    return stats, empty, empty, empty


_kpi_box = lambda label, val: html.Div([
    html.Div(label, style={'fontSize': 12, 'color': '#666'}),
    html.Div(str(val), style={'fontSize': 24, 'fontWeight': 'bold'}),
], style={'display': 'inline-block', 'margin': '10px 20px', 'padding': '12px 20px', 'border': '1px solid #ddd', 'borderRadius': 8})

# Layout: tylko KPI + puste wykresy (mały payload = szybsze ładowanie pod /django_plotly_dash/app/...)
_empty_fig = go.Figure(layout=dict(title='—', margin=dict(t=30, b=30)))
try:
    _stats, _automation_fig, _stock_fig, _demo_fig = _load_layout_data()
    app.layout = html.Div([
        html.H2('NC Dashboard (Plotly Dash)', style={'textAlign': 'center'}),
        html.Div([
            _kpi_box('MPD – produkty', _stats.get('mpd_products', '—')),
            _kpi_box('Matterhorn1 – produkty', _stats.get('matterhorn1_products', '—')),
            _kpi_box('Web Agent – uruchomienia', _stats.get('automation_runs', '—')),
            _kpi_box('Audit Dash', _stats.get('audit_entries', '—')),
        ], style={'textAlign': 'center', 'marginBottom': 24}),
        dcc.Graph(id='automation-graph', figure=_automation_fig),
        html.Hr(),
        html.H3('Stany magazynowe – zmiany w czasie', style={'textAlign': 'center'}),
        html.P('Źródło historii stanów:', style={'textAlign': 'center', 'marginBottom': 4}),
        dcc.Dropdown(
            id='stock-source-dropdown',
            options=[{'label': 'MPD', 'value': 'mpd'}, {'label': 'Matterhorn1', 'value': 'matterhorn1'}, {'label': 'Tabu', 'value': 'tabu'}],
            value='mpd', clearable=False, style={'width': '220px', 'margin': '0 auto 12px'},
        ),
        dcc.Graph(id='stock-history-graph', figure=_stock_fig),
        html.Hr(),
        html.P('Demo – wybierz serię (callback + Redis cache)', style={'textAlign': 'center'}),
        dcc.Dropdown(
            id='series-dropdown',
            options=[{'label': 'Seria A', 'value': 0}, {'label': 'Seria B', 'value': 1}],
            value=0, clearable=False, style={'width': '200px', 'margin': '0 auto 16px'},
        ),
        dcc.Graph(id='main-graph', figure=_demo_fig),
    ])
except Exception:
    # Fallback: minimalny layout, żeby cokolwiek się wyświetliło (bez blokowania na "Loading")
    app.layout = html.Div([
        html.H2('NC Dashboard (Plotly Dash)', style={'textAlign': 'center'}),
        html.P('Dane nie załadowały się. Odśwież stronę (Ctrl+F5) lub sprawdź logi serwera.', style={'textAlign': 'center', 'color': '#666'}),
        dcc.Graph(id='automation-graph', figure=_empty_fig),
        dcc.Graph(id='stock-history-graph', figure=_empty_fig),
        dcc.Graph(id='main-graph', figure=_empty_fig),
    ])


@app.callback(Output('main-graph', 'figure'), Input('series-dropdown', 'value'))
def update_graph(series_value):
    return _build_demo_figure(series_value or 0)


@app.callback(
    Output('stock-history-graph', 'figure'),
    Input('stock-source-dropdown', 'value'),
)
def update_stock_graph(source_value):
    return _get_stock_history_figure(source_value or 'mpd')
