# Dokumentacja API MPD - Integracja dla hurtowni

## 📋 Spis treści
1. [Wprowadzenie](#wprowadzenie)
2. [Podstawowe informacje](#podstawowe-informacje)
3. [Autentykacja](#autentykacja)
4. [Endpointy API](#endpointy-api)
5. [Modele danych](#modele-danych)
6. [Przykłady integracji](#przykłady-integracji)
7. [Kody błędów](#kody-błędów)

---

## 🎯 Wprowadzenie

API MPD (Master Product Database) umożliwia hurtowniom integrację z centralną bazą produktów. System pozwala na:
- Dodawanie i aktualizację produktów
- Zarządzanie wariantami (rozmiary, kolory)
- Zarządzanie cenami i stanami magazynowymi
- Generowanie plików XML dla systemów zewnętrznych
- Mapowanie produktów między różnymi systemami

---

## 🔧 Podstawowe informacje

### URL bazowy
```
Development: http://localhost:8000/mpd/
Production: https://twoja-domena.com/mpd/
```

### Format danych
- **Request**: `application/json`
- **Response**: `application/json` lub `application/xml` (dla eksportów)

### Dokumentacja interaktywna
- **Swagger UI**: `/api/docs/`
- **ReDoc**: `/api/redoc/`
- **OpenAPI Schema**: `/api/schema/`

---

## 🔐 Autentykacja

API MPD wymaga autentykacji dla wszystkich operacji zapisu. Wspierane metody:
- Token Authentication (REST Framework)
- Session Authentication (dla aplikacji webowych)

### Przykład użycia tokena:
```bash
curl -X POST https://domena.com/mpd/products/create/ \
  -H "Authorization: Token twoj_token_tutaj" \
  -H "Content-Type: application/json" \
  -d '{"name": "Produkt testowy"}'
```

---

## 📡 Endpointy API

### 1. Tworzenie produktu

**Endpoint**: `POST /mpd/products/create/`

**Opis**: Tworzy nowy produkt w bazie MPD.

**Request Body**:
```json
{
  "name": "Strój kąpielowy Matterhorn Summer 2024",
  "description": "Elegancki strój kąpielowy z wysokiej jakości materiału",
  "short_description": "Strój kąpielowy damski",
  "brand_id": 5,
  "unit_id": 1,
  "series_id": 12,
  "visibility": true,
  "variants": [
    {
      "color_id": 3,
      "producer_color_id": 3,
      "producer_color_name": "Czerwony",
      "size_id": 8,
      "producer_code": "MH-2024-RED-M",
      "iai_product_id": null,
      "price": 149.99,
      "vat": 23.0,
      "currency": "PLN",
      "net_price": 121.95
    }
  ],
  "path_ids": [10, 15, 20],
  "attribute_ids": [1, 3, 7]
}
```

**Response** (Success - 200):
```json
{
  "status": "success",
  "message": "Produkt został utworzony pomyślnie",
  "product_id": 1234,
  "product_name": "Strój kąpielowy Matterhorn Summer 2024",
  "variants_created": 1,
  "variants": [5678]
}
```

---

### 2. Aktualizacja produktu

**Endpoint**: `PUT/PATCH /mpd/products/{product_id}/update/`

**Opis**: Aktualizuje istniejący produkt.

**Request Body**:
```json
{
  "name": "Strój kąpielowy Matterhorn Summer 2024 - UPDATED",
  "description": "Zaktualizowany opis produktu",
  "visibility": false,
  "path_ids": [10, 15],
  "attribute_ids": [1, 3]
}
```

**Response** (Success - 200):
```json
{
  "status": "success",
  "message": "Produkt został zaktualizowany pomyślnie",
  "product_id": 1234,
  "product_name": "Strój kąpielowy Matterhorn Summer 2024 - UPDATED"
}
```

---

### 3. Pobieranie produktu

**Endpoint**: `GET /mpd/products/{product_id}/`

**Opis**: Pobiera szczegóły produktu wraz z wariantami, ścieżkami i atrybutami.

**Response** (Success - 200):
```json
{
  "status": "success",
  "product": {
    "id": 1234,
    "name": "Strój kąpielowy Matterhorn Summer 2024",
    "description": "Elegancki strój kąpielowy",
    "short_description": "Strój kąpielowy damski",
    "brand_id": 5,
    "unit_id": 1,
    "series_id": 12,
    "visibility": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "variants": [
      {
        "variant_id": 5678,
        "color_id": 3,
        "producer_color_id": 3,
        "size_id": 8,
        "producer_code": "MH-2024-RED-M",
        "iai_product_id": null,
        "exported_to_iai": false,
        "price": {
          "retail_price": 149.99,
          "vat": 23.0,
          "currency": "PLN",
          "net_price": 121.95
        }
      }
    ],
    "paths": [10, 15, 20],
    "attributes": [1, 3, 7]
  }
}
```

---

### 4. Bulk tworzenie produktów

**Endpoint**: `POST /mpd/bulk-create/`

**Opis**: Tworzy wiele produktów jednocześnie. Idealny do masowego importu.

**Request Body**:
```json
{
  "products": [
    {
      "name": "Produkt 1",
      "description": "Opis produktu 1",
      "short_description": "Krótki opis 1",
      "brand_name": "Matterhorn",
      "size_category": "standard",
      "series_name": "Summer 2024",
      "unit_id": 1,
      "visibility": true
    },
    {
      "name": "Produkt 2",
      "description": "Opis produktu 2",
      "short_description": "Krótki opis 2",
      "brand_name": "Matterhorn",
      "size_category": "standard",
      "series_name": "Winter 2024",
      "unit_id": 1,
      "visibility": true
    }
  ]
}
```

**Response** (Success - 200):
```json
{
  "status": "success",
  "created_products": [
    {
      "id": 1234,
      "name": "Produkt 1",
      "variants": []
    },
    {
      "id": 1235,
      "name": "Produkt 2",
      "variants": []
    }
  ],
  "errors": [],
  "total_created": 2
}
```

---

### 5. Mapowanie produktów z Matterhorn1

**Endpoint**: `POST /mpd/matterhorn1/bulk-map/`

**Opis**: Mapuje produkty z systemu Matterhorn do MPD.

**Request Body**:
```json
{
  "products": [
    {
      "matterhorn_product_id": "MH-12345",
      "name": "Strój kąpielowy",
      "description": "Opis produktu",
      "short_description": "Krótki opis",
      "visibility": true,
      "variants": [
        {
          "color_name": "Czerwony",
          "hex_code": "#FF0000",
          "size_name": "M",
          "producer_code": "MH-RED-M",
          "iai_product_id": null,
          "price": 149.99,
          "vat": 23.0,
          "currency": "PLN",
          "net_price": 121.95
        }
      ],
      "path_ids": [10, 15],
      "attribute_ids": [1, 3]
    }
  ]
}
```

**Response** (Success - 200):
```json
{
  "status": "success",
  "message": "Zamapowano 1 produktów",
  "created_products": [
    {
      "mpd_product_id": 1234,
      "matterhorn_product_id": "MH-12345",
      "name": "Strój kąpielowy",
      "variants_created": 1
    }
  ],
  "errors": [],
  "total_processed": 1,
  "success_count": 1,
  "error_count": 0
}
```

---

### 6. Pobieranie produktów Matterhorn1

**Endpoint**: `GET /mpd/matterhorn1/products/`

**Opis**: Pobiera listę produktów z systemu Matterhorn1 do mapowania.

**Query Parameters**:
- `search` (optional): Wyszukiwanie po nazwie, opisie, marce
- `page` (optional, default: 1): Numer strony
- `per_page` (optional, default: 20): Liczba produktów na stronę

**Przykład**:
```
GET /mpd/matterhorn1/products/?search=strój&page=1&per_page=20
```

**Response** (Success - 200):
```json
{
  "status": "success",
  "products": [
    {
      "product_id": "MH-12345",
      "name": "Strój kąpielowy",
      "description": "Opis",
      "active": true,
      "color": "Czerwony",
      "new_collection": true,
      "prices": {"PLN": 149.99},
      "brand": {
        "brand_id": "BR-001",
        "name": "Matterhorn"
      },
      "category": {
        "category_id": "CAT-10",
        "name": "Stroje kąpielowe",
        "path": "Odzież/Stroje kąpielowe"
      },
      "variants": [],
      "images": [],
      "mapped_product_uid": null
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 5,
    "total_products": 100,
    "has_next": true,
    "has_previous": false
  }
}
```

---

### 7. Zarządzanie atrybutami produktu

**Endpoint**: `POST /mpd/manage-product-attributes/`

**Opis**: Dodaje lub usuwa atrybuty produktu.

**Request Body** (Dodawanie):
```json
{
  "product_id": 1234,
  "action": "add",
  "attribute_ids": [1, 3, 7]
}
```

**Request Body** (Usuwanie):
```json
{
  "product_id": 1234,
  "action": "remove",
  "attribute_id": 3
}
```

**Response** (Success - 200):
```json
{
  "status": "success",
  "message": "Dodano 3 atrybutów do produktu Strój kąpielowy",
  "product_id": 1234,
  "action": "add"
}
```

---

### 8. Zarządzanie ścieżkami produktu

**Endpoint**: `POST /mpd/manage-product-paths/`

**Opis**: Przypisuje lub odłącza ścieżki (kategorie) do produktu.

**Request Body** (Przypisanie):
```json
{
  "product_id": 1234,
  "path_id": 10,
  "action": "assign"
}
```

**Request Body** (Odłączenie):
```json
{
  "product_id": 1234,
  "path_id": 10,
  "action": "unassign"
}
```

**Response** (Success - 200):
```json
{
  "status": "success",
  "message": "Ścieżka 10 została przypisana do produktu Strój kąpielowy",
  "product_id": 1234,
  "path_id": 10,
  "action": "assign"
}
```

---

### 9. Zarządzanie składem materiałowym

**Endpoint**: `POST /mpd/manage-product-fabric/`

**Opis**: Zarządza składem materiałowym produktu (np. 80% bawełna, 20% poliester).

**Request Body** (Dodawanie):
```json
{
  "product_id": 1234,
  "action": "add",
  "component_id": 5,
  "percentage": 80
}
```

**Request Body** (Usuwanie):
```json
{
  "product_id": 1234,
  "action": "remove",
  "component_id": 5
}
```

**Response** (Success - 200):
```json
{
  "status": "success",
  "message": "Dodano komponent Bawełna (80%) do składu produktu Strój kąpielowy",
  "product_id": 1234,
  "action": "add"
}
```

---

### 10. Generowanie XML

#### Gateway XML
**Endpoint**: `GET /mpd/generate-gateway-xml-api/`

**Opis**: Generuje plik gateway.xml z linkami do wszystkich plików XML.

**Response**: Plik XML

---

#### Full XML
**Endpoint**: `POST /mpd/generate-full-xml/`

**Opis**: Generuje pełny eksport produktów w formacie XML (eksport przyrostowy).

**Response**: Plik XML

---

#### Full Change XML
**Endpoint**: `POST /mpd/generate-full-change-xml/`

**Opis**: Generuje XML tylko ze zmienionymi produktami.

**Response**: Plik XML lub informacja o braku zmian

---

#### Light XML
**Endpoint**: `POST /mpd/generate-light-xml/`

**Opis**: Generuje uproszczony eksport produktów.

**Response**: Plik XML

---

#### Inne formaty XML
- **Producers**: `POST /mpd/generate-producers-xml/`
- **Stocks**: `POST /mpd/generate-stocks-xml/`
- **Units**: `POST /mpd/generate-units-xml/`
- **Categories**: `POST /mpd/generate-categories-xml/`
- **Sizes**: `POST /mpd/generate-sizes-xml/`

---

## 📊 Modele danych

### Produkt (Product)
```json
{
  "id": "integer",
  "name": "string (max 255)",
  "description": "text (optional)",
  "short_description": "string (max 500, optional)",
  "brand_id": "integer (foreign key, optional)",
  "unit_id": "integer (foreign key, optional)",
  "series_id": "integer (foreign key, optional)",
  "visibility": "boolean (default: true)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Wariant produktu (Product Variant)
```json
{
  "variant_id": "integer",
  "product_id": "integer (foreign key)",
  "color_id": "integer (foreign key, optional)",
  "producer_color_id": "integer (foreign key, optional)",
  "size_id": "integer (foreign key, optional)",
  "producer_code": "string (max 255, optional)",
  "iai_product_id": "integer (optional)",
  "exported_to_iai": "boolean (default: false)",
  "updated_at": "datetime"
}
```

### Cena wariantu (Variant Retail Price)
```json
{
  "variant_id": "integer (foreign key, primary key)",
  "retail_price": "decimal(10,2)",
  "vat": "decimal(5,2)",
  "currency": "string (max 10)",
  "net_price": "decimal(10,2)",
  "updated_at": "datetime"
}
```

### Marka (Brand)
```json
{
  "id": "integer",
  "name": "string (max 255)",
  "logo_url": "text (optional)",
  "opis": "text (optional)",
  "url": "url (optional)",
  "iai_brand_id": "integer (optional)"
}
```

### Kolor (Color)
```json
{
  "id": "integer",
  "name": "string (max 50)",
  "hex_code": "string (max 7)",
  "parent_id": "integer (self-reference, optional)",
  "iai_colors_id": "integer (optional)"
}
```

### Rozmiar (Size)
```json
{
  "id": "integer",
  "name": "string (max 255)",
  "category": "string (max 255, optional)",
  "unit": "string (max 255, optional)",
  "name_lower": "string (max 255, optional)",
  "iai_size_id": "string (max 255, optional)"
}
```

### Ścieżka/Kategoria (Path)
```json
{
  "id": "integer",
  "name": "string (max 255)",
  "path": "string (max 255)",
  "parent_id": "integer (optional)",
  "iai_category_id": "integer (optional)",
  "iai_menu_id": "integer (optional)",
  "iai_menu_parent_id": "integer (optional)"
}
```

### Atrybut (Attribute)
```json
{
  "id": "integer",
  "name": "string (max 255)"
}
```

### Składnik materiału (Fabric Component)
```json
{
  "id": "integer",
  "name": "string (max 100, unique)"
}
```

### Skład produktu (Product Fabric)
```json
{
  "product_id": "integer (foreign key)",
  "component_id": "integer (foreign key)",
  "percentage": "integer (0-100)"
}
```

---

## 🔄 Przykłady integracji

### Scenariusz 1: Nowa hurtownia dodaje produkty

```python
import requests
import json

BASE_URL = "https://twoja-domena.com/mpd"
API_TOKEN = "twoj_token_tutaj"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# 1. Utwórz markę (jeśli nie istnieje)
# Najpierw sprawdź czy marka istnieje przez admin panel

# 2. Przygotuj dane produktu
product_data = {
    "name": "Nowy strój kąpielowy XYZ",
    "description": "Wysokiej jakości strój kąpielowy",
    "short_description": "Strój damski",
    "brand_name": "NowaHurtownia",
    "size_category": "standard",
    "series_name": "Kolekcja Lato 2024",
    "unit_id": 1,
    "visibility": True
}

# 3. Utwórz produkt przez bulk-create
bulk_data = {
    "products": [product_data]
}

response = requests.post(
    f"{BASE_URL}/bulk-create/",
    headers=headers,
    data=json.dumps(bulk_data)
)

if response.status_code == 200:
    result = response.json()
    product_id = result['created_products'][0]['id']
    print(f"✅ Utworzono produkt ID: {product_id}")
    
    # 4. Dodaj atrybuty
    attributes_data = {
        "product_id": product_id,
        "action": "add",
        "attribute_ids": [1, 3, 7]
    }
    
    attr_response = requests.post(
        f"{BASE_URL}/manage-product-attributes/",
        headers=headers,
        data=json.dumps(attributes_data)
    )
    
    print(f"✅ Dodano atrybuty: {attr_response.json()}")
    
    # 5. Przypisz do kategorii
    path_data = {
        "product_id": product_id,
        "path_id": 10,
        "action": "assign"
    }
    
    path_response = requests.post(
        f"{BASE_URL}/manage-product-paths/",
        headers=headers,
        data=json.dumps(path_data)
    )
    
    print(f"✅ Przypisano do kategorii: {path_response.json()}")
else:
    print(f"❌ Błąd: {response.status_code} - {response.text}")
```

---

### Scenariusz 2: Aktualizacja istniejących produktów

```python
import requests
import json

BASE_URL = "https://twoja-domena.com/mpd"
API_TOKEN = "twoj_token_tutaj"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

product_id = 1234

# 1. Pobierz aktualny stan produktu
response = requests.get(
    f"{BASE_URL}/products/{product_id}/",
    headers=headers
)

if response.status_code == 200:
    current_product = response.json()['product']
    print(f"📦 Aktualny produkt: {current_product['name']}")
    
    # 2. Zaktualizuj wybrane pola
    update_data = {
        "name": f"{current_product['name']} - PROMOCJA",
        "visibility": True,
        "description": "Aktualizowany opis z promocją"
    }
    
    update_response = requests.put(
        f"{BASE_URL}/products/{product_id}/update/",
        headers=headers,
        data=json.dumps(update_data)
    )
    
    if update_response.status_code == 200:
        print(f"✅ Zaktualizowano produkt: {update_response.json()}")
    else:
        print(f"❌ Błąd aktualizacji: {update_response.status_code}")
else:
    print(f"❌ Nie znaleziono produktu: {response.status_code}")
```

---

### Scenariusz 3: Masowy import z systemu Matterhorn

```python
import requests
import json

BASE_URL = "https://twoja-domena.com/mpd"
API_TOKEN = "twoj_token_tutaj"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# 1. Pobierz produkty z Matterhorn1
response = requests.get(
    f"{BASE_URL}/matterhorn1/products/?per_page=50",
    headers=headers
)

if response.status_code == 200:
    matterhorn_products = response.json()['products']
    
    # 2. Filtruj produkty bez mapowania
    unmapped = [p for p in matterhorn_products if not p['mapped_product_uid']]
    
    print(f"📊 Znaleziono {len(unmapped)} niezamapowanych produktów")
    
    # 3. Przygotuj dane do mapowania
    products_to_map = []
    for product in unmapped[:10]:  # Mapujemy pierwsze 10
        map_data = {
            "matterhorn_product_id": product['product_id'],
            "name": product['name'],
            "description": product['description'],
            "visibility": product['active']
        }
        products_to_map.append(map_data)
    
    # 4. Wykonaj bulk mapowanie
    bulk_map_data = {
        "products": products_to_map
    }
    
    map_response = requests.post(
        f"{BASE_URL}/matterhorn1/bulk-map/",
        headers=headers,
        data=json.dumps(bulk_map_data)
    )
    
    if map_response.status_code == 200:
        result = map_response.json()
        print(f"✅ Zamapowano {result['success_count']} produktów")
        print(f"❌ Błędów: {result['error_count']}")
    else:
        print(f"❌ Błąd mapowania: {map_response.status_code}")
```

---

### Scenariusz 4: Generowanie plików XML dla systemu zewnętrznego

```python
import requests

BASE_URL = "https://twoja-domena.com/mpd"
API_TOKEN = "twoj_token_tutaj"

headers = {
    "Authorization": f"Token {API_TOKEN}"
}

# 1. Wygeneruj full XML
print("🔄 Generuję full.xml...")
full_response = requests.post(
    f"{BASE_URL}/generate-full-xml/",
    headers=headers
)

if full_response.status_code == 200:
    # Zapisz plik
    with open("full.xml", "wb") as f:
        f.write(full_response.content)
    print("✅ Zapisano full.xml")

# 2. Wygeneruj full_change XML (tylko zmiany)
print("🔄 Generuję full_change.xml...")
change_response = requests.post(
    f"{BASE_URL}/generate-full-change-xml/",
    headers=headers
)

if change_response.status_code == 200:
    if change_response.headers.get('Content-Type') == 'application/json':
        result = change_response.json()
        if result.get('status') == 'skipped':
            print("ℹ️ Brak zmian do eksportu")
    else:
        with open("full_change.xml", "wb") as f:
            f.write(change_response.content)
        print("✅ Zapisano full_change.xml")

# 3. Pobierz gateway.xml (linki do wszystkich plików)
print("🔄 Pobieram gateway.xml...")
gateway_response = requests.get(
    f"{BASE_URL}/generate-gateway-xml-api/",
    headers=headers
)

if gateway_response.status_code == 200:
    with open("gateway.xml", "wb") as f:
        f.write(gateway_response.content)
    print("✅ Zapisano gateway.xml")
```

---

## ⚠️ Kody błędów

### HTTP Status Codes

| Kod | Znaczenie | Opis |
|-----|-----------|------|
| 200 | OK | Operacja zakończona sukcesem |
| 400 | Bad Request | Nieprawidłowe dane wejściowe |
| 401 | Unauthorized | Brak lub nieprawidłowa autentykacja |
| 404 | Not Found | Zasób nie istnieje |
| 405 | Method Not Allowed | Nieprawidłowa metoda HTTP |
| 500 | Internal Server Error | Błąd serwera |

### Przykładowe odpowiedzi błędów

**400 Bad Request**:
```json
{
  "status": "error",
  "message": "Nazwa produktu jest wymagana"
}
```

**404 Not Found**:
```json
{
  "status": "error",
  "message": "Produkt nie istnieje"
}
```

**500 Internal Server Error**:
```json
{
  "status": "error",
  "message": "Błąd serwera: szczegóły błędu"
}
```

---

## 📞 Wsparcie i kontakt

### Zgłaszanie problemów
- Sprawdź logi: `/logs/matterhorn/`
- Skontaktuj się z zespołem technicznym
- Udostępnij:
  - Request body
  - Response
  - Timestamp
  - Product ID (jeśli dotyczy)

### Najlepsze praktyki
1. **Używaj bulk operacji** dla masowych importów
2. **Cachuj odpowiedzi** słownikowe (marki, kategorie, rozmiary)
3. **Implementuj retry logic** dla błędów przejściowych
4. **Waliduj dane** przed wysłaniem
5. **Monitoruj rate limiting**
6. **Loguj wszystkie operacje**

### Rate Limiting
- Domyślnie: **100 requestów/minutę** per API token
- Dla bulk operacji: **10 requestów/minutę**
- Sprawdź headery: `X-RateLimit-Limit`, `X-RateLimit-Remaining`

---

## 🔄 Changelog API

### v1.0 (2024-01-15)
- Pierwsza wersja API MPD
- Podstawowe operacje CRUD na produktach
- Bulk tworzenie i mapowanie
- Generowanie XML
- Zarządzanie atrybutami, ścieżkami i składem

---

## 📚 Dodatkowe zasoby

- **Swagger UI**: `/api/docs/` - Interaktywna dokumentacja
- **ReDoc**: `/api/redoc/` - Dokumentacja w formacie ReDoc
- **OpenAPI Schema**: `/api/schema/` - Schemat API w formacie OpenAPI 3.0

---

**Dokumentacja wygenerowana**: 2024-01-15  
**Wersja API**: 1.0  
**Autor**: NC Project Team
