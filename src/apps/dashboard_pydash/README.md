# Dashboard PyDash (ćwiczenie pod ofertę ZF)

Środowisko do ćwiczeń technologii z oferty **Web Developer (PyDash)** – Dash, RBAC, Celery, Redis, audit log.

## Co możesz wyświetlić w Dash (z aplikacji NC)

| Źródło | Dane | Przykład |
|--------|------|----------|
| **MPD** | Produkty, warianty, stany, ceny | Liczba produktów, wykres po markach/kategoriach |
| **matterhorn1** | Produkty, mapowanie do MPD, sync | Liczba produktów, zmapowane vs niezmapowane |
| **tabu** | TabuProduct, warianty, stock | Liczba produktów Tabu, historia stanów |
| **web_agent** | AutomationRun, ProductProcessingLog | Uruchomienia automatyzacji (wykres w czasie), sukces/błąd |
| **dashboard_pydash** | DashAuditLog | Liczba wpisów audytu, ostatnie akcje |
| **Celery** | Taski (django-celery-results) | Liczba zadań, sukces/fail, czas wykonania |

Aktualnie w layoucie: **KPI** (MPD, matterhorn1, web_agent, audit), **wykres słupkowy** uruchomień automatyzacji (ostatnie 14 dni), **demo** wykres z Redis cache.

## Co jest zaimplementowane

- **Plotly Dash** – wykres (dropdown → callback) z użyciem `plotly.graph_objects`.
- **django-plotly-dash** – integracja z Django (osadzenie w szablonie, `{% plotly_app %}`).
- **RBAC** – dostęp do dashboardu tylko dla zalogowanych (`login_required`); audit log tylko dla **staff**.
- **Redis cache** – dane wykresu w cache (opcjonalne – działa bez Redis).
- **Celery** – task `run_simulation` wywoływany z widoku (przycisk „Uruchom task Celery”).
- **Audit log** – model `DashAuditLog` (kto, kiedy, jaka akcja).

## Uruchomienie

1. Zainstaluj zależności: `pip install -r src/requirements.txt`, potem **opcjonalnie** `pip install -r src/requirements-pydash.txt` (dash, plotly, django-plotly-dash). Bez tych pakietów build Docker (web) przechodzi; dashboard PyDash jest wtedy wyłączony.
2. Migracje:  
   `python src/manage.py migrate --database=default --settings=core.settings.dev`
3. Uruchom serwer (i opcjonalnie Celery/Redis).
4. Wejdź na **/pydash/** – wymagane logowanie (Django Admin).  
   Strona główna ma link: [Dashboard PyDash](/pydash/).

## Adresy

| URL | Opis |
|-----|------|
| `/pydash/` | Dashboard z wykresem Dash |
| `/pydash/audit/` | Audit log (tylko staff) |
| `/pydash/trigger-simulation/` | POST – uruchamia task Celery |

## Rozwój (praktyka ZF)

- Dodać więcej wykresów i callbacków (state, caching).
- Rozszerzyć RBAC (grupy, uprawnienia).
- Dodać zapis konfiguracji użytkownika (user config persistence).
- Integracja z SSO/OAuth (np. django-allauth).
