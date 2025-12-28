# 🔧 Rozwiązywanie problemu "relation auth_user does not exist" w testach

## Problem

Podczas uruchamiania testów Django pojawia się błąd:
```
django.db.utils.ProgrammingError: relation "auth_user" does not exist
```

To oznacza, że stare testowe bazy danych są uszkodzone lub nieprawidłowo utworzone.

## Rozwiązanie

### Krok 1: Usuń stare testowe bazy danych

**Opcja A: Przez psql (najprostsze)**

```powershell
# Upewnij się, że masz dostęp do PostgreSQL
# Zastąp wartości zgodnie z Twoją konfiguracją z .env.dev

# Przykład (dostosuj do swoich ustawień):
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS test_zzz_default;"
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS test_zzz_MPD;"
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS test_zzz_matterhorn1;"
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS test_zzz_web_agent;"
```

**Opcja B: Przez Python (wymaga aktywnego venv)**

```powershell
# Aktywuj venv
.\.venv\Scripts\Activate.ps1

# Uruchom skrypt
python clean_test_databases.py
```

**Opcja C: Ręcznie przez pgAdmin lub inny klient PostgreSQL**

1. Połącz się z PostgreSQL
2. Znajdź bazy danych zaczynające się od `test_`
3. Usuń je ręcznie

### Krok 2: Uruchom testy ponownie

```powershell
python manage.py test --settings=nc.settings.dev
```

Django automatycznie utworzy nowe testowe bazy danych z poprawnymi migracjami.

## Alternatywne rozwiązanie: --keepdb

Jeśli chcesz zachować istniejące testowe bazy (szybsze, ale może maskować problemy):

```powershell
python manage.py test --settings=nc.settings.dev --keepdb
```

## Zapobieganie problemowi w przyszłości

1. **Zawsze uruchamiaj migracje przed testami** (jeśli zmieniłeś modele)
2. **Używaj `--keepdb` tylko gdy jesteś pewien, że bazy są poprawne**
3. **Regularnie czyść testowe bazy** jeśli pojawiają się problemy

## Sprawdzenie czy bazy istnieją

```powershell
# Lista wszystkich baz danych
psql -h localhost -U postgres -c "\l" | findstr test_
```

## Jeśli problem nadal występuje

1. Sprawdź czy wszystkie migracje są wykonane:
   ```powershell
   python manage.py migrate --settings=nc.settings.dev
   ```

2. Sprawdź czy masz uprawnienia do tworzenia baz danych w PostgreSQL

3. Sprawdź logi PostgreSQL pod kątem błędów

4. Spróbuj uruchomić testy z verbose output:
   ```powershell
   python manage.py test --settings=nc.settings.dev --verbosity=2
   ```

