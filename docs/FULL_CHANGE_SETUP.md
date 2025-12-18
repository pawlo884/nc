# Konfiguracja systemu full_change.xml z datą w nazwie

## Opis zmian

System eksportu XML został zmodyfikowany aby:

1. **Pliki full_change.xml generują się z datą w nazwie**: `full_changeYYYY-MM-DDThh-mm-ss.xml`
2. **Pliki nie są nadpisywane** - każdy eksport tworzy nowy plik
3. **W gateway.xml dodano węzeł `changes`** z podwęzłami `change` zawierającymi linki do wszystkich plików full_change
4. **Dodano model `FullChangeFile`** do śledzenia wygenerowanych plików

## Struktura węzła changes w gateway.xml

```xml
<changes>
  <change url="https://mojbucket.fra1.digitaloceanspaces.com/MPD_test/xml/matterhorn/full_change2025-08-25T10-30-45.xml" 
          hash="982a963722ff18c7e1580de635841caa" 
          changed="2025-08-25 10:30:45"/>
  <change url="https://mojbucket.fra1.digitaloceanspaces.com/MPD_test/xml/matterhorn/full_change2025-08-25T11-15-22.xml" 
          hash="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" 
          changed="2025-08-25 11:15:22"/>
</changes>
```

## Instalacja

### 1. Utwórz tabelę full_change_files w bazie danych

```bash
cd nc_project
python MPD/create_full_change_files_db.py
```

### 2. Sprawdź czy tabele zostały utworzone

```sql
-- Sprawdź czy tabela istnieje
SELECT table_name FROM information_schema.tables 
WHERE table_name = 'full_change_files';

-- Sprawdź strukturę tabeli
\d full_change_files
```

## Użycie

### Eksport pojedynczego pliku full_change.xml

```python
from MPD.export_to_xml import export_full_change_xml

# Eksport pełny wszystkich produktów do pliku z datą w nazwie
result = export_full_change_xml()
print(f"Utworzono plik: {result['local_path']}")
print(f"URL: {result['bucket_url']}")
```

### Eksport przyrostowy

```python
from MPD.export_to_xml import export_incremental_full_change_xml

# Eksport przyrostowy zmienionych produktów do pliku z datą w nazwie
result = export_incremental_full_change_xml()
```

### Eksport wszystkich plików XML

```python
from MPD.export_to_xml import export_all_xml

# Eksport wszystkich plików (włącznie z full_change.xml z datą w nazwie)
results = export_all_xml()
```

### Odświeżenie gateway.xml

```python
from MPD.export_to_xml import export_gateway_xml

# Odśwież gateway.xml (zaktualizuje węzeł changes)
result = export_gateway_xml()
```

## Monitoring

### Panel administracyjny Django

1. Przejdź do `/admin/MPD/fullchangefile/`
2. Zobaczysz listę wszystkich wygenerowanych plików full_change.xml
3. Każdy rekord zawiera:
   - Nazwę pliku
   - Timestamp
   - Datę utworzenia
   - URL do bucketa
   - Ścieżkę lokalną
   - Rozmiar pliku

### Sprawdzenie w bazie danych

```sql
-- Pokaż wszystkie pliki full_change
SELECT id, filename, timestamp, created_at, file_size 
FROM full_change_files 
ORDER BY created_at DESC;

-- Pokaż ostatnie 10 plików
SELECT id, filename, timestamp, created_at, file_size 
FROM full_change_files 
ORDER BY created_at DESC 
LIMIT 10;
```

## Struktura plików

### Lokalne pliki
```
MPD_test/xml/matterhorn/
├── full.xml
├── full_change2025-08-25T10-30-45.xml
├── full_change2025-08-25T11-15-22.xml
├── light.xml
└── gateway.xml
```

### Bucket S3/DO Spaces
```
MPD_test/xml/matterhorn/
├── full.xml
├── full_change2025-08-25T10-30-45.xml
├── full_change2025-08-25T11-15-22.xml
├── light.xml
└── gateway.xml
```

## Automatyzacja

### Cron job dla eksportu przyrostowego

```bash
# Dodaj do crontab - eksport co godzinę
0 * * * * cd /path/to/nc_project && python -c "from MPD.export_to_xml import export_incremental_full_change_xml; export_incremental_full_change_xml()"
```

### Celery task

```python
from MPD.export_to_xml import export_incremental_full_change_xml

@shared_task
def export_full_change_task():
    return export_incremental_full_change_xml()
```

## Czyszczenie starych plików

### Automatyczne czyszczenie (opcjonalne)

Możesz dodać skrypt do usuwania starych plików:

```python
import os
from datetime import datetime, timedelta
from MPD.models import FullChangeFile

def cleanup_old_full_change_files(days_to_keep=30):
    """Usuwa pliki full_change starsze niż X dni"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # Usuń rekordy z bazy
    old_files = FullChangeFile.objects.filter(created_at__lt=cutoff_date)
    
    for file_record in old_files:
        # Usuń lokalny plik
        if os.path.exists(file_record.local_path):
            os.remove(file_record.local_path)
        
        # Usuń z bucketa (opcjonalne)
        # s3_client.delete_object(Bucket=DO_SPACES_BUCKET, Key=f"MPD_test/xml/matterhorn/{file_record.filename}")
        
        # Usuń rekord z bazy
        file_record.delete()
    
    print(f"Usunięto {old_files.count()} starych plików full_change")
```

## Rozwiązywanie problemów

### Błąd: "Tabela full_change_files nie istnieje"

```bash
# Uruchom skrypt tworzenia tabeli
python MPD/create_full_change_files_db.py
```

### Błąd: "Nie można zaimportować FullChangeFile"

```bash
# Sprawdź czy model jest poprawnie zdefiniowany
python manage.py shell
>>> from MPD.models import FullChangeFile
>>> FullChangeFile.objects.all()
```

### Pliki nie są widoczne w gateway.xml

```python
# Odśwież gateway.xml
from MPD.export_to_xml import export_gateway_xml
export_gateway_xml()
```

## Testowanie

### Test eksportu

```python
from MPD.export_to_xml import export_full_change_xml

# Test eksportu
result = export_full_change_xml()
print(f"Test eksportu: {result}")

# Sprawdź czy plik został utworzony
import os
print(f"Plik istnieje: {os.path.exists(result['local_path'])}")

# Sprawdź czy rekord został zapisany w bazie
from MPD.models import FullChangeFile
files = FullChangeFile.objects.all()
print(f"Liczba plików w bazie: {files.count()}")
```

### Test gateway.xml

```python
from MPD.export_to_xml import export_gateway_xml

# Test odświeżenia gateway.xml
result = export_gateway_xml()
print(f"Gateway.xml zaktualizowany: {result}")

# Sprawdź zawartość pliku
with open('MPD_test/xml/matterhorn/gateway.xml', 'r') as f:
    content = f.read()
    print("Węzeł changes w gateway.xml:")
    if '<changes>' in content:
        print("✅ Węzeł changes został dodany")
    else:
        print("❌ Węzeł changes nie został znaleziony")
```

