# 🔄 System Eksportu Przyrostowego full.xml

## 📋 **Przegląd**

System eksportu przyrostowego dla `full.xml` został zaimplementowany aby zoptymalizować wydajność eksportu dużych zbiorów danych. Zamiast eksportować wszystkie produkty za każdym razem, system eksportuje tylko nowe produkty od ostatniego eksportu.

## 🗄️ **Tabela Tracking**

### **ExportTracking**
```sql
CREATE TABLE xml_export_tracking (
    id SERIAL PRIMARY KEY,
    export_type VARCHAR(255),           -- 'full', 'light', etc.
    last_exported_product_id BIGINT,    -- Ostatni wyeksportowany iai_product_id
    last_exported_timestamp TIMESTAMP,  -- Data ostatniego eksportu
    total_products_exported BIGINT,     -- Łączna liczba wyeksportowanych produktów
    export_status VARCHAR(255),         -- 'success', 'failed', 'reset'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## ⚙️ **Jak to działa**

### **1. Eksport Przyrostowy (domyślny)**
```python
# Pobiera tylko produkty z iai_product_id > ostatni_eksportowany_id
variants_with_iai = ProductVariants.objects.filter(
    iai_product_id__isnull=False,
    iai_product_id__gt=last_exported_id
)
```

### **2. Aktualizacja Tracking**
Po udanym eksporcie:
- `last_exported_product_id` = maksymalny `iai_product_id` z eksportu
- `total_products_exported` += liczba wyeksportowanych produktów
- `export_status` = 'success'

### **3. Pełny Eksport (reset)**
```python
# Reset tracking
tracking.last_exported_product_id = 0
tracking.total_products_exported = 0
tracking.export_status = 'reset'
```

## 🚀 **Użycie**

### **Eksport Przyrostowy (automatyczny)**
```python
from MPD.export_to_xml import FullXMLExporter

exporter = FullXMLExporter()
result = exporter.export_incremental()  # Tylko nowe produkty
```

### **Eksport Pełny (reset)**
```python
exporter = FullXMLExporter()
result = exporter.export_full()  # Wszystkie produkty
```

### **Zadanie Celery**
```python
# Automatyczny eksport przyrostowy raz na dobę
@shared_task(name='generate_daily_full_xml')
def generate_daily_full_xml():
    exporter = FullXMLExporter()
    result = exporter.export_incremental()
```

## 🌐 **Endpoints**

### **Eksport Przyrostowy**
```
GET /MPD/generate-full-xml/
```

### **Reset Eksportu (pełny)**
```
POST /MPD/reset-full-xml-export/
```

**Response:**
```json
{
    "status": "success",
    "message": "Reset eksportu full.xml zakończony pomyślnie",
    "bucket_url": "https://...",
    "local_path": "MPD_test/xml/matterhorn/full.xml"
}
```

## 📊 **Monitoring**

### **Logi**
```
INFO - Eksport przyrostowy full.xml - od iai_product_id: 1234
INFO - Zaktualizowano tracking - ostatni iai_product_id: 5678
```

### **Statystyki**
- `last_exported_product_id`: Ostatni wyeksportowany produkt
- `total_products_exported`: Łączna liczba wyeksportowanych produktów
- `export_status`: Status ostatniego eksportu

## 🔧 **Konfiguracja Celery Beat**

### **Dodanie zadania w panelu admina:**
1. Przejdź do **Django Admin** → **Periodic Tasks**
2. Kliknij **Add Periodic Task**
3. Wypełnij:
   - **Name**: `Daily Full XML Export`
   - **Task**: `generate_daily_full_xml`
   - **Interval**: `1 day`
   - **Enabled**: ✅

## ⚡ **Korzyści**

### **Wydajność**
- ✅ Eksport tylko nowych produktów
- ✅ Znacznie szybsze wykonanie
- ✅ Mniejsze obciążenie serwera
- ✅ Mniejsze zużycie zasobów

### **Bezpieczeństwo**
- ✅ Historia eksportów
- ✅ Możliwość resetu
- ✅ Monitoring statusu
- ✅ Szczegółowe logi

### **Elastyczność**
- ✅ Automatyczny eksport przyrostowy
- ✅ Ręczny reset do pełnego eksportu
- ✅ Konfigurowalne zadania Celery
- ✅ Endpointy REST API

## 🚨 **Uwagi**

1. **Pierwszy eksport**: Jeśli `last_exported_product_id = 0`, wykonuje się pełny eksport
2. **Reset**: Ustawia `last_exported_product_id = 0` i wymusza pełny eksport
3. **Błędy**: Jeśli eksport się nie powiedzie, tracking nie jest aktualizowany
4. **Monitoring**: Sprawdzaj logi i status w tabeli `xml_export_tracking`

## 📈 **Przykład użycia**

```python
# Sprawdź status eksportu
from MPD.models import ExportTracking

tracking = ExportTracking.objects.get(export_type='full')
print(f"Ostatni eksport: {tracking.last_exported_product_id}")
print(f"Łącznie wyeksportowano: {tracking.total_products_exported}")
print(f"Status: {tracking.export_status}")
```

## 🎯 **Następne kroki**

1. **Testowanie**: Sprawdź działanie na małym zbiorze danych
2. **Monitoring**: Dodaj alerty dla błędów eksportu
3. **Optymalizacja**: Rozważ indeksy na `iai_product_id`
4. **Backup**: Regularne kopie zapasowe tabeli tracking 