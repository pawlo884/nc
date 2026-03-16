# REST API – kontrakty i przykłady wywołań

Dokument opisuje endpointy REST (Django REST Framework), kontrakty request/response oraz sposób podłączenia (curl, Postman).

---

## 1. Dokumentacja OpenAPI i autoryzacja

| Zasób | URL |
|-------|-----|
| **Schema OpenAPI (JSON)** | `GET /api/schema/` |
| **Swagger UI** | `GET /api/docs/` |
| **ReDoc** | `GET /api/redoc/` |

**Autoryzacja:**  
Endpointy pod `/api/web-agent/` wymagają **IsAuthenticated** (Token lub Session).  
W dev często używa się **Token Authentication**: header `Authorization: Token <token>`.

- Token można wygenerować w Django Admin: **Użytkownicy** → wybierz użytkownika → **Tokeny** (jeśli używasz `rest_framework.authtoken`) lub przez endpoint `POST /api/auth/token/` (jeśli jest skonfigurowany).
- W Postman: w zakładce **Authorization** wybierz **Bearer Token** lub **API Key** (Key: `Authorization`, Value: `Token <twoj_token>`).

---

## 2. API Web Agent (`/api/web-agent/`)

Baza URL (dev): `http://localhost:8000/api/web-agent/`  
Wszystkie endpointy wymagają zalogowanego użytkownika.

---

### 2.1 AutomationRun – lista i szczegóły

**Lista uruchomień (z filtrami)**

- **URL:** `GET /api/web-agent/automation-runs/`
- **Query params (opcjonalne):**
  - `status` – `pending` \| `running` \| `completed` \| `failed`
  - `brand_id` – integer
  - `category_id` – integer
  - `source` – `matterhorn1` \| `tabu`
- **Response 200:** lista obiektów `AutomationRun` (paginated, jeśli włączona paginacja).

**Kontrakt pojedynczego elementu listy / szczegółów:**

```json
{
  "id": 1,
  "started_at": "2025-03-06T10:00:00Z",
  "completed_at": "2025-03-06T10:05:00Z",
  "status": "completed",
  "products_processed": 10,
  "products_success": 9,
  "products_failed": 1,
  "error_message": null,
  "brand_id": 5,
  "category_id": null,
  "filters": {},
  "source": "matterhorn1",
  "product_logs": [ /* lista ProductProcessingLog */ ],
  "duration_seconds": 300.0
}
```

**Przykład curl:**

```bash
curl -s -H "Authorization: Token TWOJ_TOKEN" \
  "http://localhost:8000/api/web-agent/automation-runs/?status=completed"
```

**Szczegóły jednego runa**

- **URL:** `GET /api/web-agent/automation-runs/{id}/`
- **Response 200:** jeden obiekt jak wyżej (z zagnieżdżonymi `product_logs`).

```bash
curl -s -H "Authorization: Token TWOJ_TOKEN" \
  "http://localhost:8000/api/web-agent/automation-runs/1/"
```

---

### 2.2 Uruchomienie automatyzacji

- **URL:** `POST /api/web-agent/automation-runs/start-automation/`
- **Content-Type:** `application/json`
- **Body:**

| Pole | Typ | Wymagane | Opis |
|------|-----|----------|------|
| `source` | string | nie | `matterhorn1` (domyślnie) lub `tabu` |
| `brand_id` | int \| null | dla matterhorn1: tak* | ID marki |
| `category_id` | int \| null | dla matterhorn1: tak* | ID kategorii |
| `filters` | object | nie | Dodatkowe filtry (domyślnie `{}`) |

\* Dla `source: "matterhorn1"` trzeba podać **przynajmniej jedno**: `brand_id` lub `category_id`.

**Przykład request (Matterhorn1):**

```json
{
  "source": "matterhorn1",
  "brand_id": 5,
  "category_id": null,
  "filters": {}
}
```

**Przykład request (Tabu):**

```json
{
  "source": "tabu",
  "brand_id": 12,
  "category_id": 3,
  "filters": {}
}
```

**Response 202 Accepted (sukces):**

- Dla matterhorn1:
```json
{
  "status": "started",
  "task_id": "uuid-celery-task",
  "message": "Automatyzacja została uruchomiona"
}
```
- Dla tabu:
```json
{
  "status": "started",
  "task_id": "uuid-celery-task",
  "automation_run_id": 42,
  "message": "Automatyzacja Tabu→MPD została uruchomiona"
}
```

**Response 400:** błędy walidacji (np. brak `brand_id`/`category_id` dla matterhorn1):

```json
{
  "source": ["..."],
  "brand_id": ["..."],
  "non_field_errors": ["Dla źródła matterhorn1 podaj przynajmniej brand_id lub category_id"]
}
```

**Przykład curl:**

```bash
curl -s -X POST \
  -H "Authorization: Token TWOJ_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":"matterhorn1","brand_id":5}' \
  "http://localhost:8000/api/web-agent/automation-runs/start-automation/"
```

---

### 2.3 Logi produktów dla runa

- **URL:** `GET /api/web-agent/automation-runs/{id}/logs/`
- **Response 200:** lista logów przetwarzania produktów (format jak w `ProductProcessingLog`).

**Kontrakt elementu listy:**

```json
{
  "id": 1,
  "automation_run": 1,
  "product_id": 100,
  "product_name": "Strój kąpielowy XYZ",
  "status": "success",
  "mpd_product_id": 50,
  "error_message": null,
  "processed_at": "2025-03-06T10:01:00Z",
  "processing_data": {}
}
```

```bash
curl -s -H "Authorization: Token TWOJ_TOKEN" \
  "http://localhost:8000/api/web-agent/automation-runs/1/logs/"
```

---

### 2.4 Logi automatyzacji „na żywo”

- **URL:** `GET /api/web-agent/automation-runs/{id}/automation-logs/`
- **Response 200:**

```json
{
  "logs": "tekst logów z automatyzacji",
  "status": "running",
  "products_processed": 5,
  "products_success": 4,
  "products_failed": 1
}
```

```bash
curl -s -H "Authorization: Token TWOJ_TOKEN" \
  "http://localhost:8000/api/web-agent/automation-runs/1/automation-logs/"
```

---

### 2.5 ProductProcessingLog – lista (tylko odczyt)

- **URL:** `GET /api/web-agent/product-logs/`
- **Query params (opcjonalne):**
  - `automation_run` – ID runa
  - `status` – `pending` \| `processing` \| `success` \| `failed`
  - `product_id` – ID produktu (źródłowy)
- **Response 200:** lista obiektów jak w pkt 2.3.

```bash
curl -s -H "Authorization: Token TWOJ_TOKEN" \
  "http://localhost:8000/api/web-agent/product-logs/?automation_run=1&status=success"
```

---

## 3. API MPD – zestawy produktów (ProductSet)

Ścieżki są pod **`/mpd/`** (uwaga: w `i18n_patterns` może być prefiks języka, np. `/pl/mpd/` lub bez prefiksu – zależnie od `prefix_default_language`).  
Przykład zakładam bez prefiksu: `http://localhost:8000/mpd/`.

Te endpointy mogą **nie** wymagać tokena (zależnie od konfiguracji DRF dla tej aplikacji).

---

### 3.1 ProductSet – CRUD

| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/mpd/product-sets/` | Lista zestawów |
| POST | `/mpd/product-sets/` | Utworzenie zestawu |
| GET | `/mpd/product-sets/{id}/` | Szczegóły zestawu |
| PUT / PATCH | `/mpd/product-sets/{id}/` | Aktualizacja |
| DELETE | `/mpd/product-sets/{id}/` | Usunięcie |

**Body POST/PATCH (ProductSet):**  
Pola z modelu (np. `mapped_product`, `name`, `description`). W response zwracane są też `items` (lista elementów zestawu).

**Przykład – lista zestawów:**

```bash
curl -s "http://localhost:8000/mpd/product-sets/"
```

**Przykład – dodanie produktu do zestawu**

- **URL:** `POST /mpd/product-sets/{id}/add_product/`
- **Body:**

```json
{
  "product_id": 10,
  "quantity": 2
}
```

**Response 200:** `{"status": "product added to set"}`  
**Response 404:** `{"error": "Product not found"}`

```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"product_id":10,"quantity":2}' \
  "http://localhost:8000/mpd/product-sets/1/add_product/"
```

**Usunięcie produktu z zestawu**

- **URL:** `POST /mpd/product-sets/{id}/remove_product/`
- **Body:** `{"product_id": 10}`

**Lista produktów w zestawie**

- **URL:** `GET /mpd/product-sets/{id}/products/`
- **Response 200:** lista obiektów typu `ProductSetItem` (id, mapped_product, quantity, created_at).

---

## 4. Matterhorn1 – API bulk i sync

Ścieżki: **`/matterhorn1/api/`** (z możliwym prefiksem języka).  
Przykład bazy: `http://localhost:8000/matterhorn1/api/`.

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/matterhorn1/api/products/bulk/create/` | POST | Masowe tworzenie produktów |
| `/matterhorn1/api/products/bulk/update/` | POST | Masowe aktualizowanie produktów |
| `/matterhorn1/api/variants/bulk/create/` | POST | Masowe tworzenie wariantów |
| `/matterhorn1/api/brands/bulk/create/` | POST | Masowe tworzenie marek |
| `/matterhorn1/api/categories/bulk/create/` | POST | Masowe tworzenie kategorii |
| `/matterhorn1/api/images/bulk/create/` | POST | Masowe tworzenie obrazów |
| `/matterhorn1/api/sync/` | GET/POST | Synchronizacja z API |
| `/matterhorn1/api/sync/products/`, `.../variants/` | GET/POST | Sync produktów / wariantów |
| `/matterhorn1/api/status/` | GET | Status API |
| `/matterhorn1/api/logs/` | GET | Logi API |
| `/matterhorn1/api/products/{product_id}/` | GET | Szczegóły produktu |

Dokładne kontrakty request/response dla bulk/sync są w **OpenAPI** (`/api/schema/`) oraz w widokach w `matterhorn1.views` (np. `ProductBulkCreateView`, `VariantBulkCreateView`). W Postman najlepiej zaimportować schemat z `/api/schema/` – tam są wszystkie tagi i modele.

---

## 5. Postman – szybki start

1. **Import schematu**
   - W Postman: **Import** → **Link** → wklej: `http://localhost:8000/api/schema/`
   - Albo zapisz wynik `GET http://localhost:8000/api/schema/` do pliku `.json` i zaimportuj go.

2. **Zmienna bazowego URL**
   - Utwórz zmienną kolekcji, np. `base_url` = `http://localhost:8000`.
   - W requestach używaj: `{{base_url}}/api/web-agent/automation-runs/`.

3. **Autoryzacja dla Web Agent**
   - W kolekcji (lub w folderze dla web-agent): **Authorization** → Type: **Bearer Token** (albo **API Key**, Key: `Authorization`, Value: `Token TWOJ_TOKEN`).
   - Token uzyskaj z Django Admin (Auth Token) lub z endpointu logowania, jeśli jest w projekcie.

4. **Środowisko**
   - Możesz dodać zmienne: `base_url`, `token`, żeby przełączać dev/staging.

---

## 6. Podsumowanie adresów (dev)

| Obsługa | Bazowy URL |
|---------|------------|
| Dokumentacja (Swagger / ReDoc / schema) | `http://localhost:8000/api/docs/`, `/api/redoc/`, `/api/schema/` |
| Web Agent (automatyzacja, logi) | `http://localhost:8000/api/web-agent/` |
| MPD zestawy produktów | `http://localhost:8000/mpd/product-sets/` |
| Matterhorn1 bulk/sync | `http://localhost:8000/matterhorn1/api/` |

Jeśli serwer działa na innym porcie lub hoście, zamień `localhost:8000` na odpowiedni adres (np. z `API_BASE_URL` w ustawieniach).
