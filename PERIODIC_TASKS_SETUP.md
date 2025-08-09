# 🚀 Konfiguracja Periodic Tasks dla Eksportu XML

## 📋 Zarejestrowane Taski

### ✅ **Taski co godzinę (domyślnie włączone):**

1. **`mpd.export_full_xml_hourly`** - Eksport przyrostowy `full.xml`
   - Eksportuje nowe produkty od ostatniego eksportu
   - Uruchamiany co godzinę

2. **`mpd.export_full_change_xml_hourly`** - Eksport przyrostowy `full_change.xml`
   - Monitoruje zmiany w wyeksportowanych produktach (ostatnie 2 godziny)
   - Uruchamiany co godzinę

### 🔴 **Taski dzienne (domyślnie wyłączone):**

3. **`mpd.export_full_xml_full`** - Eksport pełny `full.xml`
   - Eksportuje wszystkie produkty
   - Uruchamiany raz dziennie (opcjonalnie)

4. **`mpd.export_full_change_xml_full`** - Eksport pełny `full_change.xml`
   - Eksportuje wszystkie produkty
   - Uruchamiany raz dziennie (opcjonalnie)

## 🛠️ **Instrukcja konfiguracji:**

### **Krok 1: Uruchom skrypt konfiguracyjny**
```bash
cd nc_project
python setup_periodic_tasks.py
```

### **Krok 2: Uruchom Celery Worker**
```bash
celery -A nc worker -l info
```

### **Krok 3: Uruchom Celery Beat**
```bash
celery -A nc beat -l info
```

### **Krok 4: Sprawdź status w Django Admin**
- Przejdź do `Django Admin` → `Periodic Tasks`
- Sprawdź czy taski są włączone
- Możesz włączyć/wyłączyć taski dzienne

## 📊 **Monitoring i logi:**

### **Logi Celery:**
- Worker: `celery -A nc worker -l info`
- Beat: `celery -A nc beat -l info`

### **Logi Django:**
- Sprawdź logi w `logs/` lub konsoli Django

### **Status tasków:**
- Django Admin → Periodic Tasks
- Flower (jeśli skonfigurowany)

## 🔧 **Konfiguracja zaawansowana:**

### **Modyfikacja interwałów:**
```python
# W Django Admin → Periodic Tasks → Edit
# Zmień interwał na:
# - co 30 minut: every=30, period=MINUTES
# - co 2 godziny: every=2, period=HOURS
# - co 2 dni: every=2, period=DAYS
```

### **Dodanie nowych tasków:**
```python
# W MPD/tasks.py dodaj nowy task:
@shared_task(bind=True, name='mpd.nazwa_tasku')
def nazwa_funkcji(self):
    # logika taska
    pass
```

### **Usunięcie wszystkich tasków:**
```bash
python setup_periodic_tasks.py --cleanup
```

## ⚠️ **Ważne uwagi:**

1. **Worker musi być uruchomiony** - bez niego taski nie będą wykonywane
2. **Beat musi być uruchomiony** - bez niego taski nie będą planowane
3. **Redis musi działać** - broker dla Celery
4. **Baza danych musi być dostępna** - dla periodic tasks

## 🚨 **Rozwiązywanie problemów:**

### **Task nie wykonuje się:**
- Sprawdź czy worker jest uruchomiony
- Sprawdź logi Celery
- Sprawdź czy task jest włączony w Django Admin

### **Błąd połączenia z Redis:**
- Sprawdź czy Redis działa
- Sprawdź hasło Redis w zmiennych środowiskowych

### **Błąd bazy danych:**
- Sprawdź połączenie z bazą
- Sprawdź migracje Django

## 📝 **Przykład uruchomienia w tle:**

### **Uruchom worker w tle:**
```bash
nohup celery -A nc worker -l info > worker.log 2>&1 &
```

### **Uruchom beat w tle:**
```bash
nohup celery -A nc beat -l info > beat.log 2>&1 &
```

### **Sprawdź procesy:**
```bash
ps aux | grep celery
```

## 🎯 **Gotowe do użycia!**

Po wykonaniu powyższych kroków:
- ✅ Taski są zarejestrowane w Celery
- ✅ Periodic tasks są skonfigurowane w bazie danych
- ✅ Eksport XML będzie działał automatycznie co godzinę
- ✅ Możesz monitorować status w Django Admin

**Wszystko gotowe do uruchomienia periodic tasks! 🚀**
