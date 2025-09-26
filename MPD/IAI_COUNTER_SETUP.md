# Konfiguracja licznika IAI Product ID

## Problem
Wcześniej `iai_product_id` było generowane na podstawie maksymalnej wartości w tabeli `product_variants`:
```sql
SELECT COALESCE(MAX(iai_product_id), 0) + 1 FROM product_variants
```

To powodowało problem: gdy usuwano produkty z bazy danych, `iai_product_id` mogło się zmniejszać i nowe produkty otrzymywały już użyte ID.

## Rozwiązanie
Utworzono dedykowaną tabelę `iai_product_counter`, która zawsze rośnie i nigdy się nie zmniejsza.

### Struktura tabeli
```sql
CREATE TABLE iai_product_counter (
    id INTEGER PRIMARY KEY DEFAULT 1,
    counter_value BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT single_row CHECK (id = 1)
);
```

### Logika działania
1. Tabela ma tylko jeden wiersz (id = 1)
2. Przy każdym dodaniu nowego produktu, `counter_value` jest zwiększane o 1
3. Używa się `ON CONFLICT (id) DO UPDATE SET counter_value = counter_value + 1`

## Instalacja

### Opcja 1: Uruchomienie migracji Django
```bash
python manage.py migrate MPD
```

### Opcja 2: Uruchomienie skryptu SQL
```bash
psql -h <host> -U <user> -d <database> -f MPD/sql/create_iai_counter.sql
```

### Opcja 3: Uruchomienie skryptu Python
```bash
cd MPD
python init_iai_counter.py
```

## Weryfikacja
Po instalacji sprawdź w panelu admin Django (MPD > Liczniki IAI Product ID) lub bezpośrednio w bazie:
```sql
SELECT * FROM iai_product_counter;
```

## Zmiany w kodzie
1. **MPD/defs_db.py** - dodano definicję tabeli
2. **MPD/models.py** - dodano model Django
3. **MPD/admin.py** - dodano panel admin
4. **MPD/migrations/0019_iai_product_counter.py** - migracja Django
5. **matterhorn/admin.py** - zmieniono logikę generowania `iai_product_id`

## Korzyści
- ✅ `iai_product_id` zawsze rośnie
- ✅ Brak duplikatów ID
- ✅ Niezależność od usuwania produktów
- ✅ Łatwe śledzenie w panelu admin
- ✅ Automatyczna inicjalizacja przy nowych instalacjach
