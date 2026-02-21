# Konfiguracja codziennego generowania full.xml

## 📋 Przygotowane zadanie Celery

Zostało utworzone zadanie `generate_daily_full_xml` w pliku `MPD/tasks.py`:

```python
@shared_task(name='generate_daily_full_xml')
def generate_daily_full_xml():
    """
    Zadanie Celery do codziennego generowania pliku full.xml
    Można dodać w panelu admina jako zadanie okresowe (raz na dobę)
    """
```

## ⚙️ Jak dodać zadanie w panelu admina Django

### 1. **Przejdź do panelu admina Django**
```
http://localhost:8000/admin/
```

### 2. **Znajdź sekcję "Periodic Tasks" lub "Django Celery Beat"**
- Szukaj sekcji związanej z Celery Beat
- Może być w kategorii "DJANGO_CELERY_BEAT" lub podobnej

### 3. **Dodaj nowe zadanie okresowe (Periodic Task)**

#### **Podstawowe ustawienia:**
- **Name**: `Daily Full XML Generation`
- **Task**: `generate_daily_full_xml`
- **Enabled**: ✅ (zaznaczone)

#### **Harmonogram (Schedule):**
Wybierz jedną z opcji:

**Opcja A - Cron Schedule:**
- **Minute**: `0`
- **Hour**: `2` (2:00 w nocy)
- **Day of month**: `*`
- **Month of year**: `*`
- **Day of week**: `*`

**Opcja B - Interval Schedule:**
- **Every**: `1`
- **Period**: `days`

### 4. **Dodatkowe ustawienia (opcjonalne):**
- **Description**: `Codzienne generowanie pliku full.xml dla Matterhorn`
- **Queue**: pozostaw puste (domyślna kolejka)
- **Priority**: pozostaw puste
- **Expires**: pozostaw puste

## 🧪 Testowanie zadania

### **Test synchroniczny (bez Celery):**
```bash
python test_daily_full_xml_task.py
```

### **Test asynchroniczny (przez Celery):**
1. Uruchom Celery worker:
```bash
celery -A nc worker --loglevel=info
```

2. Uruchom test:
```bash
python test_daily_full_xml_task.py
```

### **Ręczne uruchomienie zadania:**
```python
from MPD.tasks import generate_daily_full_xml

# Synchronicznie
result = generate_daily_full_xml()

# Asynchronicznie
task = generate_daily_full_xml.delay()
```

## 📊 Co robi zadanie

1. **Generuje full.xml** używając `FullXMLExporter`
2. **Zapisuje lokalnie** do `MPD_test/xml/full.xml`
3. **Przesyła na bucket** Digital Ocean Spaces
4. **Aktualizuje gateway.xml** automatycznie
5. **Loguje wszystkie operacje** z czasami wykonania

## 📝 Logi zadania

Zadanie loguje szczegółowe informacje:
- ✅ Start i koniec zadania z timestampami
- 📁 Ścieżki do wygenerowanych plików
- 🔗 URL-e na bucket
- ⏱️ Czas wykonania
- ❌ Błędy w przypadku problemów

## 🎯 Nazwa zadania dla panelu admina

**Nazwa zadania**: `generate_daily_full_xml`

To jest dokładna nazwa, którą musisz wpisać w polu "Task" w panelu admina.

## ⚠️ Uwagi

- Zadanie automatycznie używa tylko źródła Matterhorn (id=2)
- Po wygenerowaniu full.xml automatycznie aktualizuje gateway.xml
- Wszystkie pliki są zapisywane w folderze `MPD_test/xml/`
- Zadanie zwraca szczegółowe informacje o rezultacie