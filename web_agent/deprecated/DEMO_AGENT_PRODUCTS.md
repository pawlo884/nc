# Demonstracja: Jak agent dodaje produkty

## Przegląd procesu

Agent web automatycznie dodaje produkty z bazy `matterhorn1` do bazy `MPD` przez interfejs Django Admin. Proces składa się z następujących kroków:

## 1. Logowanie do Django Admin

Agent używa Playwright do:

- Nawigacji do strony logowania (`/admin/`)
- Wypełnienia pól `username` i `password`
- Kliknięcia przycisku logowania
- Oczekiwania na zalogowanie

## 2. Przechodzenie przez produkty

Dla każdego produktu z marki (np. Marko) agent:

### a) Sprawdza czy produkt istnieje w MPD

- Przechodzi do strony produktu w Django Admin (`/admin/matterhorn1/product/{id}/change/`)
- Sprawdza czy produkt ma `mapped_product_uid` (czy jest już zmapowany)
- Jeśli nie, sprawdza sugerowane produkty z MPD (coverage)

### b) Jeśli produkt istnieje (coverage = 100%)

- Kliknie przycisk "Przypisz do istniejącego produktu"
- Produkt zostanie zmapowany

### c) Jeśli produkt nie istnieje (coverage < 100%)

Agent wypełnia formularz i tworzy nowy produkt:

#### Krok 1: Formatowanie nazwy produktu

Dla marki Marko formatuje nazwę:

- **Wejście**: `"Kostium dwuczęściowy Kostium kąpielowy Model Rose M-818 (5) Yellow/Pink - Marko"`
- **Wyjście**: `"Kostium kąpielowy Rose"`

#### Krok 2: Wypełnianie pól formularza

Agent wypełnia następujące pola:

1. **mpd_name** - Sformatowana nazwa produktu
2. **mpd_description** - Opis produktu (może być edytowany przez AI)
3. **mpd_short_description** - Krótki opis
4. **mpd_brand** - Marka produktu
5. **mpd_size_category** - Kategoria rozmiarów
6. **main_color_id** - Główny kolor (z bazy MPD)
7. **producer_color_name** - Kolor producenta (wyciągnięty z nazwy produktu)
8. **producer_code** - Kod producenta (format M-XXX, wyciągnięty z nazwy)
9. **series_name** - Nazwa serii (format: `"strój kąpielowy {model_name} - Lupo Line"`)
10. **unit_id** - Jednostka produktu

#### Krok 3: Kliknięcie przycisku "Utwórz nowy produkt w MPD"

- Agent sprawdza czy wszystkie pola są wypełnione
- Kliknie przycisk `#create-mpd-product-btn`
- Czeka na potwierdzenie utworzenia produktu

#### Krok 4: Weryfikacja utworzenia produktu

Agent sprawdza:

- Komunikat sukcesu w `#status-message`
- Pole `is_mapped` (czy produkt jest zmapowany)
- Pole `mapped_product_uid` (ID produktu w MPD)
- Czy strona się przeładowała

#### Krok 5: Upload obrazów (jeśli dostępne)

- Jeśli produkt ma obrazy, agent je uploaduje
- Sprawdza czy obrazy zostały załadowane

#### Krok 6: Powrót do listy produktów

- Po zakończeniu, agent wraca do listy produktów
- Przechodzi do następnego produktu

## 3. Przykładowy przepływ dla jednego produktu

```
1. Navigate: /admin/matterhorn1/product/123/change/
2. Wait for: Form fields
3. Evaluate: Sprawdź czy produkt jest zmapowany
4. Evaluate: Sprawdź suggested products (coverage)
5. If coverage < 100%:
   a. Evaluate: Formatuj nazwę produktu
   b. Fill: mpd_name = "Kostium kąpielowy Rose"
   c. Fill: mpd_description = "..."
   d. Fill: mpd_short_description = "..."
   e. Fill: mpd_brand = "Marko"
   f. Fill: mpd_size_category = "..."
   g. Fill: main_color_id = "..."
   h. Fill: producer_color_name = "Yellow/Pink"
   i. Fill: producer_code = "M-818"
   j. Fill: series_name = "strój kąpielowy Rose - Lupo Line"
   k. Fill: unit_id = "..."
   l. Evaluate: Sprawdź czy wszystkie pola są wypełnione
   m. Click: #create-mpd-product-btn
   n. Wait: 5 sekund
   o. Evaluate: Sprawdź czy produkt został utworzony
   p. If images: Upload images
6. Navigate: /admin/matterhorn1/product/
```

## 4. Uruchomienie agenta

### Przez Django shell:

```python
from web_agent.tasks import start_web_agent_task
from web_agent.models import WebAgentTask

# Pobierz zadanie
task = WebAgentTask.objects.using('zzz_web_agent').get(id=2)

# Uruchom zadanie (synchronicznie dla testów)
start_web_agent_task(task.id)

# Lub asynchronicznie przez Celery
start_web_agent_task.delay(task.id)
```

### Przez API:

```bash
POST /api/web_agent/api/tasks/{task_id}/start/
```

### Przez komendę Django:

```bash
python manage.py create_brand_task --brand-name "Marko" --settings=nc.settings.dev
```

## 5. Monitorowanie postępu

### Sprawdzenie logów:

```python
from web_agent.models import WebAgentTask, WebAgentLog

task = WebAgentTask.objects.using('zzz_web_agent').get(id=2)
logs = WebAgentLog.objects.using('zzz_web_agent').filter(task=task).order_by('-timestamp')

for log in logs[:10]:
    print(f"[{log.timestamp}] {log.get_level_display()}: {log.message}")
```

### Sprawdzenie statusu zadania:

```python
task = WebAgentTask.objects.using('zzz_web_agent').get(id=2)
print(f"Status: {task.status}")
print(f"Wynik: {task.result}")
print(f"Błąd: {task.error_message}")
```

## 6. Wymagania

- **Playwright**: Zainstalowany i skonfigurowany
- **Django Admin**: Działający serwer na `http://localhost:8000`
- **Baza danych**: Połączenie z bazami `matterhorn1` i `MPD`
- **Celery**: Działający worker (dla asynchronicznego uruchomienia)

## 7. Przykładowe dane produktu

**Wejście (matterhorn1):**

```json
{
  "product_uid": 12345,
  "name": "Kostium dwuczęściowy Kostium kąpielowy Model Rose M-818 (5) Yellow/Pink - Marko",
  "description": "Elegancki kostium kąpielowy...",
  "color": "Yellow/Pink",
  "brand": "Marko",
  "active": true,
  "is_mapped": false
}
```

**Wyjście (MPD):**

```json
{
  "name": "Kostium kąpielowy Rose",
  "description": "Elegancki kostium kąpielowy...",
  "brand_id": 1,
  "producer_color_name": "Yellow/Pink",
  "producer_code": "M-818",
  "series_name": "strój kąpielowy Rose - Lupo Line",
  "mapped_product_uid": 12345
}
```

## 8. Obsługa błędów

Agent obsługuje następujące sytuacje:

- Produkt już istnieje → Przypisuje do istniejącego
- Pola nie wypełnione → Czeka i ponawia próbę
- Błąd tworzenia → Loguje błąd i przechodzi do następnego produktu
- Timeout → Próbuje ponownie (max 3 razy)

