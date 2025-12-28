# ⚠️ Problem z testowymi bazami danych w Django 6.0

## Problem

Podczas uruchamiania testów Django 6.0 pojawia się błąd:

```
django.db.utils.ProgrammingError: relation "auth_user" does not exist
```

Błąd występuje podczas tworzenia testowej bazy danych i wykonywania migracji.

## Przyczyna

Problem może być związany z:

1. **Django 6.0** - nowa wersja może mieć problemy z tworzeniem testowych baz dla wielu baz danych
2. **Konfiguracja wielu baz danych** - projekt używa 8 baz danych (default, zzz_default, MPD, zzz_MPD, matterhorn1, zzz_matterhorn1, web_agent, zzz_web_agent)
3. **Database routers** - mogą powodować konflikty podczas tworzenia testowych baz

## Rozwiązania

### Rozwiązanie 1: Użyj tylko bazy default dla testów (zalecane)

Zmodyfikuj `nc/settings/dev.py` aby wszystkie bazy używały MIRROR dla testów:

```python
# Konfiguracja testów - wszystkie bazy używają tej samej testowej bazy
DATABASES['default']['TEST'] = {
    'NAME': None,
}
DATABASES['zzz_default']['TEST'] = {'MIRROR': 'default'}
DATABASES['MPD']['TEST'] = {'MIRROR': 'default'}
DATABASES['zzz_MPD']['TEST'] = {'MIRROR': 'default'}
DATABASES['matterhorn1']['TEST'] = {'MIRROR': 'default'}
DATABASES['zzz_matterhorn1']['TEST'] = {'MIRROR': 'default'}
DATABASES['web_agent']['TEST'] = {'MIRROR': 'default'}
DATABASES['zzz_web_agent']['TEST'] = {'MIRROR': 'default'}
```

### Rozwiązanie 2: Tymczasowy rollback do Django 5.2.4

Jeśli problem jest krytyczny, możesz wrócić do Django 5.2.4:

```bash
pip install Django==5.2.4
```

### Rozwiązanie 3: Użyj in-memory SQLite dla testów

Możesz skonfigurować testy aby używały SQLite w pamięci (szybsze, ale może mieć ograniczenia):

```python
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
```

## Status

- ✅ Testy zostały utworzone (91 testów)
- ⚠️ Problem z tworzeniem testowych baz danych w Django 6.0
- 🔄 Wymaga dalszej diagnostyki lub workaround

## Następne kroki

1. Sprawdź czy problem występuje w Django 6.0.1 (jeśli dostępne)
2. Zgłoś issue do Django jeśli to bug
3. Użyj rozwiązania 1 (MIRROR) jako workaround
4. Rozważ użycie pytest-django zamiast standardowych testów Django
