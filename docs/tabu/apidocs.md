# Tabu API – dokumentacja

**Dokumentacja oficjalna:** [https://b2b.tabu.com.pl/api/v1](https://b2b.tabu.com.pl/api/v1)

**Baza danych i migracje (dev: alias `zzz_tabu`):** [database.md](database.md)

## Podstawy

- **URL bazowy:** `https://b2b.tabu.com.pl/api/v1`
- **Uwierzytelnienie:** nagłówek `X-API-KEY: Twój klucz API`
- Metody: GET, POST (REST). Zalecane: `Content-Type: application/json` i JSON w body.
- **Limity:** max 100 zapytań/minutę (przy przekroczeniu blokada 2 min). Max 1000 elementów w `limit`.

## Konfiguracja w projekcie

W `.env.dev`:

```env
TABU_API_BASE_URL=https://b2b.tabu.com.pl/api/v1
TABU_API_KEY=Twój_klucz_API
```

Domyślnie `TABU_API_BASE_URL` jest ustawiony na powyższy URL; można go nadpisać.

## Test połączenia

```bash
cd src
python manage.py test_tabu_connection --settings=core.settings.dev
```

Z podaniem klucza w linii:

```bash
python manage.py test_tabu_connection --api-key=TWÓJ_KLUCZ --settings=core.settings.dev
```

Inne zasoby (domyślnie wywoływany jest `GET .../products`):

```bash
python manage.py test_tabu_connection --path=products/categories --settings=core.settings.dev
python manage.py test_tabu_connection --path=users/me --settings=core.settings.dev
```

## Wybrane zasoby (produkty, zamówienia)

| Zasób | Opis |
|-------|------|
| `GET products` | Lista produktów (parametry: path, category_id, update_from, update_to) |
| `GET products/{id}` | Szczegóły produktu |
| `GET products/details` | Szczegółowa lista produktów (max limit 100) |
| `GET products/basic` | Płaska lista wariantów (id=product, variant_id=variant, store, ceny) |
| `GET products/store` | Szczegółowy stan produktów w magazynach (update_from, update_to) |
| `GET products/categories` | Pełna lista kategorii |
| `GET products/producers` | Lista producentów |
| `GET orders` | Lista zamówień |
| `GET orders/{id}` | Szczegóły zamówienia |
| `GET users/me` | Dane użytkownika API |

Stronicowanie: parametry `page`, `limit`, `lang` dla list.

## Kody odpowiedzi

- **200** – sukces  
- **400** – nieprawidłowe dane  
- **401** – błąd autoryzacji  
- **403** – brak dostępu do zasobu  
- **404** – zasób nie istnieje  
- **429** – przekroczony limit zapytań  
- **500** – błąd serwera  

Pełna lista endpointów i parametrów: [https://b2b.tabu.com.pl/api/v1](https://b2b.tabu.com.pl/api/v1).

## Import i synchronizacja produktów

Produkty są pobierane **pojedynczo** (GET products/{id}) – w ten sposób dostępne są pełne dane:
- `desc_long`, `desc_safety` – pełne opisy
- `gallery` – zdjęcia w tym zdjęcia kolorów
- `groups`, `dictionaries` – grupy, atrybuty (Kolor, Rozmiar, Materiał)
- `variants` z pełnymi danymi

Limit API: 100 req/min. Domyślne opóźnienie 1s (~60 req/min). Pełny import ~9300 produktów zajmuje ~2,5 h.

### Synchronizacja kategorii (przed importem produktów)

Pobierz faktyczne nazwy kategorii z API – produkty będą linkowane do prawdziwych kategorii:

```bash
python manage.py sync_tabu_categories --settings=core.settings.dev
```

### Pełny import (produkt po produkcie, od ID 1)

Czyszczenie bazy i import od ID 1 do pierwszego 404:

```bash
cd src
python manage.py sync_tabu_categories --settings=core.settings.dev
python manage.py clear_tabu_data --settings=core.settings.dev
python manage.py import_tabu_by_id --settings=core.settings.dev
```

Opcje `import_tabu_by_id`: `--start-id`, `--stop-after-404`, `--delay`, `--max-products`.

### Pełny import (lista z GET products + pobieranie po ID)

```bash
python manage.py sync_tabu_products --settings=core.settings.dev
```

### Test (mała próbka)
```bash
python manage.py sync_tabu_products --max-products 20 --settings=core.settings.dev
```

### Aktualizacja (tylko produkty zmienione od daty)

```bash
python manage.py sync_tabu_products --update-from "2026-01-01 00:00:00" --settings=core.settings.dev
```

### Periodic task (aktualizacja produktów co 10 minut)

```bash
# Skonfiguruj task (tworzy/aktualizuje wpis w django_celery_beat)
python manage.py setup_tabu_sync_task --settings=core.settings.dev

# Z interwałem 10 minut (domyślnie)
python manage.py setup_tabu_sync_task --interval 10 --settings=core.settings.dev

# Wyłączenie
python manage.py setup_tabu_sync_task --disable --settings=core.settings.dev
```

Wymaga uruchomionego Celery Beat i workera. Task `tabu.tasks.sync_tabu_products_update` pobiera produkty z parametrem `update_from` (ostatnia synchronizacja).

### Synchronizacja stanów i cen (products/basic)

`GET products/basic` zwraca płaską listę wariantów: każdy element ma `id` (product), `variant_id` (variant), `store`, ceny. Historia zmian stanów zapisywana w `tabu_stock_history` (jak Matterhorn).

```bash
# Pełna synchronizacja
python manage.py sync_tabu_stock --settings=core.settings.dev

# Tylko produkty zmienione od daty
python manage.py sync_tabu_stock --update-from "2026-01-01 00:00:00" --settings=core.settings.dev
```

### Periodic task – stany i ceny co 10 minut

```bash
# Skonfiguruj task (domyślnie co 10 minut)
python manage.py setup_tabu_stock_sync_task --settings=core.settings.dev

# Wyłączenie
python manage.py setup_tabu_stock_sync_task --disable --settings=core.settings.dev
```

Task `tabu.tasks.sync_tabu_stock` – update_from = 12 minut wstecz od rozpoczęcia. Historia stanów w adminie.

### Sprawdzanie nowych produktów (max api_id + 1)

```bash
python manage.py sync_tabu_new_products --settings=core.settings.dev
```

Logika: ostatnie `api_id` w bazie + 1 → GET `products/{id}`. 200 = import i sprawdź kolejne, 404 = brak nowych.

### Periodic task – nowe produkty co kilka godzin

```bash
# Skonfiguruj task (domyślnie co 4h = 240 min)
python manage.py setup_tabu_sync_task --settings=core.settings.dev

# Z interwałem np. 4 godziny
python manage.py setup_tabu_sync_task --interval 240 --settings=core.settings.dev
```

Task `tabu.tasks.sync_tabu_products_update` – wywołuje `sync_tabu_new_products`.
