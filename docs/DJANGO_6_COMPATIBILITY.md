# Analiza kompatybilności z Django 6.0

## Status kompatybilności

**Data analizy:** 2026-07-15  
**Branch:** `chore/django-upgrade-compat`  
**Aktualna wersja Django (ten branch):** **6.0.7**  
**Docelowa wersja Django:** **6.0.7** (najnowsza na PyPI)  
**Status:** ✅ **PODNIESIONE — migracje zzz_default zastosowane, check OK**

## Wyniki weryfikacji (2026-07-15)

| Test | Wynik |
|------|-------|
| `pip install` Django 6.0.7 + zależności | ✅ OK |
| `pip check` | ✅ Brak konfliktów |
| `python manage.py check --settings=core.settings.dev` | ✅ 0 issues |
| `python manage.py check -Wa` (deprecation warnings) | ✅ 0 issues |
| `makemigrations --dry-run` | ✅ Brak nowych migracji |
| `matterhorn1.tests.BrandModelTest` (3 testy, `--keepdb`) | ✅ OK |
| Migracje pakietów (admin_interface, celery_results) | ✅ Zastosowane w test DB |

## Python

- ✅ **Python 3.13** (Dockerfile.prod, venv lokalne)
- Django 6.0 wymaga Python **3.12+**

## Zaktualizowane zależności Django

| Pakiet | Było (main) | Docelowe (Django 6) | Status |
|--------|-------------|---------------------|--------|
| `Django` | 5.2.4 | **6.0.7** | ✅ |
| `asgiref` | 3.8.1 | **3.12.1** | ✅ wymagane przez Django 6 |
| `django-celery-beat` | 2.8.0 | **2.9.0** | ✅ |
| `django-celery-results` | 2.5.1 | **2.6.0** | ✅ |
| `djangorestframework` | 3.16.0 | **3.17.1** | ✅ |
| `drf-spectacular` | 0.28.0 | **0.30.0** | ✅ |
| `django-cors-headers` | 4.7.0 | **4.9.0** | ✅ |
| `django-debug-toolbar` | 5.1.0 | **7.0.0** | ✅ |
| `django-redis` | 5.4.0 | **7.0.0** | ✅ |
| `django-admin-interface` | 0.30.0 | **0.32.0** | ✅ |
| `django-colorfield` | 0.13.0 | **0.14.0** | ✅ |
| `django-storages` | 1.14.4 | **1.14.6** | ✅ |
| `django-timezone-field` | 7.1 | **7.2.2** | ✅ |

## Kod projektu — sprawdzone elementy

- ✅ URL patterns używają `path()` — OK
- ✅ Brak `CheckConstraint(check=...)` (usunięte w Django 6)
- ✅ Brak deprecated API (`url()`, `ugettext`, `django.utils.six`)
- ✅ `DEFAULT_AUTO_FIELD = BigAutoField` — OK
- ✅ Multi-database routing — OK
- 🔧 Usunięto martwe `USE_L10N = True` z `base.py` (setting usunięty od Django 5.0)

## Alternatywa: patch LTS bez skoku na 6

Na PyPI dostępna jest też linia **5.2.16** (LTS). Branch `feature/sentry-monitoring` ma patch **5.2.13** — mniejsze ryzyko, bez breaking changes Django 6.

| Opcja | Wersja | Ryzyko |
|-------|--------|--------|
| Patch LTS | 5.2.16 | Niskie |
| Upgrade major | 6.0.7 | Średnie — wymaga pełnej regresji |

## Co jeszcze przetestować przed merge

- [ ] Pełna suite testów: `python manage.py test --settings=core.settings.dev`
- [ ] Migracje na wszystkich bazach (default, matterhorn1, MPD, web_agent, tabu)
- [ ] Admin panel + django-admin-interface
- [ ] API / Swagger (drf-spectacular)
- [ ] Celery beat + results
- [ ] Build Docker (`deployments/docker/Dockerfile.prod`)
- [ ] Deploy testowy na k3s nc-test

## Komendy weryfikacji

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r src/requirements.ci.txt
cd src
python manage.py check --settings=core.settings.dev
python -Wa manage.py check --settings=core.settings.dev
python manage.py makemigrations --dry-run --settings=core.settings.dev
python manage.py test --settings=core.settings.dev --keepdb
```

## Wnioski

Projekt **startuje poprawnie na Django 6.0.7** — zależności się instalują, `check` przechodzi, próbka testów OK.  
**Rekomendacja:** kontynuować pełną regresję na branchu `chore/django-upgrade-compat`, potem merge do main.

## Linki

- [Django 6.0 Release Notes](https://docs.djangoproject.com/en/6.0/releases/6.0/)
- [Django 6.0 Upgrade Guide](https://docs.djangoproject.com/en/6.0/howto/upgrade-version/)
- [Django 5.0 — usunięte features (w tym USE_L10N)](https://docs.djangoproject.com/en/6.0/releases/5.0/)
