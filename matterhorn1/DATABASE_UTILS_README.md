# Database Utils - Utility Functions dla Operacji Między Bazami Danych

## Przegląd

Moduł `database_utils.py` zawiera gotowe utility functions do bezpiecznego wykonywania operacji między bazami danych `matterhorn1` i `MPD`. Funkcje te zapewniają:

- **Automatyczne logowanie** wszystkich operacji
- **Obsługę błędów** z pełnym kontekstem
- **Bezpieczne transakcje** między bazami danych
- **Kompensację** w przypadku błędów
- **Jednolite API** dla wszystkich operacji

## Klasy i Funkcje

### DatabaseUtils

Klasa z podstawowymi operacjami na bazach danych.

#### Metody statyczne:

##### `get_or_create_color(color_name: str, parent_color_id: int = None) -> Optional[int]`
Pobiera lub tworzy kolor w bazie MPD.

```python
# Pobierz główny kolor
color_id = DatabaseUtils.get_or_create_color("Red")

# Pobierz/utwórz kolor producenta
producer_color_id = DatabaseUtils.get_or_create_color("Red-Producer", parent_color_id=color_id)
```

##### `get_or_create_size(size_name: str, category: str = None) -> Optional[int]`
Pobiera lub tworzy rozmiar w bazie MPD.

```python
size_id = DatabaseUtils.get_or_create_size("M", "Unisex")
```

##### `get_product_data(product_id: int) -> Optional[Dict[str, Any]]`
Pobiera dane produktu z bazy matterhorn1.

```python
product_data = DatabaseUtils.get_product_data(123)
if product_data:
    print(f"Produkt: {product_data['name']}, Kolor: {product_data['color']}")
```

##### `get_product_variants(product_id: int) -> List[Dict[str, Any]]`
Pobiera warianty produktu z bazy matterhorn1.

```python
variants = DatabaseUtils.get_product_variants(123)
for variant in variants:
    print(f"Wariant: {variant['name']}, Stock: {variant['stock']}")
```

##### `create_mpd_product(product_data: Dict[str, Any]) -> Optional[int]`
Tworzy produkt w bazie MPD.

```python
product_data = {
    'name': 'Test Product',
    'description': 'Test Description',
    'short_description': 'Test Short',
    'brand_id': 1
}
product_id = DatabaseUtils.create_mpd_product(product_data)
```

##### `create_mpd_variant(variant_data: Dict[str, Any]) -> Optional[int]`
Tworzy wariant produktu w bazie MPD.

```python
variant_data = {
    'product_id': 123,
    'color_id': 1,
    'size_id': 2,
    'producer_code': 'ABC123',
    'iai_product_id': 1
}
variant_id = DatabaseUtils.create_mpd_variant(variant_data)
```

##### `update_product_mapping(product_id: int, mapped_product_id: int) -> bool`
Aktualizuje mapowanie produktu w bazie matterhorn1.

```python
success = DatabaseUtils.update_product_mapping(123, 456)
```

##### `add_product_attribute(product_id: int, attribute_id: int) -> bool`
Dodaje atrybut do produktu w bazie MPD.

```python
success = DatabaseUtils.add_product_attribute(123, 1)
```

##### `add_product_path(product_id: int, path_id: int) -> bool`
Dodaje ścieżkę do produktu w bazie MPD.

```python
success = DatabaseUtils.add_product_path(123, 1)
```

### SafeCrossDatabaseOperations

Klasa z bezpiecznymi operacjami między bazami danych.

#### Metody statyczne:

##### `create_product_with_mapping(matterhorn_product_id: int, mpd_product_data: Dict[str, Any]) -> Dict[str, Any]`
Bezpieczne utworzenie produktu w MPD z mapowaniem w matterhorn1.

```python
mpd_product_data = {
    'name': 'Test Product',
    'description': 'Test Description',
    'short_description': 'Test Short',
    'brand_id': 1
}

result = SafeCrossDatabaseOperations.create_product_with_mapping(
    matterhorn_product_id=123,
    mpd_product_data=mpd_product_data
)

if result['success']:
    print(f"Produkt utworzony: MPD ID {result['mpd_product_id']}")
else:
    print(f"Błąd: {result['error']}")
```

##### `create_variants_with_mapping(matterhorn_product_id: int, mpd_product_id: int, size_category: str, producer_color_id: int = None) -> Dict[str, Any]`
Bezpieczne utworzenie wariantów w MPD z mapowaniem w matterhorn1.

```python
result = SafeCrossDatabaseOperations.create_variants_with_mapping(
    matterhorn_product_id=123,
    mpd_product_id=456,
    size_category='Unisex',
    producer_color_id=1
)

if result['success']:
    print(f"Utworzono {result['created_variants']} wariantów")
    if result['failed_variants']:
        print(f"Nie udało się utworzyć: {result['failed_variants']}")
```

## Przykłady Użycia

### Podstawowe Operacje

```python
from matterhorn1.database_utils import DatabaseUtils

# Pobierz dane produktu
product_data = DatabaseUtils.get_product_data(123)
if product_data:
    # Utwórz kolor w MPD
    color_id = DatabaseUtils.get_or_create_color(product_data['color'])
    
    # Utwórz rozmiar w MPD
    size_id = DatabaseUtils.get_or_create_size("M", "Unisex")
    
    # Utwórz produkt w MPD
    mpd_product_data = {
        'name': product_data['name'],
        'description': product_data['description'],
        'short_description': product_data['short_description'],
        'brand_id': 1
    }
    mpd_product_id = DatabaseUtils.create_mpd_product(mpd_product_data)
    
    # Zaktualizuj mapowanie
    if mpd_product_id:
        DatabaseUtils.update_product_mapping(123, mpd_product_id)
```

### Bezpieczne Operacje

```python
from matterhorn1.database_utils import SafeCrossDatabaseOperations

# Utwórz produkt z mapowaniem
result = SafeCrossDatabaseOperations.create_product_with_mapping(
    matterhorn_product_id=123,
    mpd_product_data={
        'name': 'Test Product',
        'description': 'Test Description',
        'short_description': 'Test Short',
        'brand_id': 1
    }
)

if result['success']:
    # Utwórz warianty
    variants_result = SafeCrossDatabaseOperations.create_variants_with_mapping(
        matterhorn_product_id=123,
        mpd_product_id=result['mpd_product_id'],
        size_category='Unisex'
    )
    
    print(f"Wynik: {variants_result}")
```

### Integracja z Admin.py

Zamiast ręcznego kodu:

```python
# Stary sposób
with connections['MPD'].cursor() as cursor:
    cursor.execute("SELECT id FROM colors WHERE name = %s", [color_name])
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO colors (name) VALUES (%s) RETURNING id", [color_name])
        result = cursor.fetchone()
    color_id = result[0]
```

Użyj utility functions:

```python
# Nowy sposób
color_id = DatabaseUtils.get_or_create_color(color_name)
```

## Logowanie

Wszystkie operacje są automatycznie logowane z:
- Typem operacji (SELECT, INSERT, UPDATE, DELETE)
- Bazą danych i tabelą
- Danymi wejściowymi i wynikami
- Czasem trwania operacji
- Informacjami o błędach

## Obsługa Błędów

Wszystkie funkcje zwracają:
- `None` lub `False` w przypadku błędu
- Słownik z `success: bool` i `error: str` dla złożonych operacji
- Pełne logowanie błędów z kontekstem

## Kompensacja

Funkcje `SafeCrossDatabaseOperations` implementują podstawową kompensację:
- W przypadku błędu mapowania, produkt zostaje oznaczony do usunięcia
- Wszystkie operacje są logowane dla łatwego rollback
- Saga Pattern zapewnia pełną kompensację

## Migracja z Istniejącego Kodu

1. **Zidentyfikuj** operacje między bazami w kodzie
2. **Zastąp** ręczne zapytania SQL utility functions
3. **Dodaj** obsługę błędów używając zwracanych wartości
4. **Przetestuj** operacje z nowymi funkcjami
5. **Usuń** stary kod po weryfikacji

## Przykład Migracji

### Przed:
```python
with connections['MPD'].cursor() as cursor:
    cursor.execute("SELECT id FROM colors WHERE name = %s", [color_name])
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO colors (name) VALUES (%s) RETURNING id", [color_name])
        result = cursor.fetchone()
        connections['MPD'].commit()
    color_id = result[0]
```

### Po:
```python
color_id = DatabaseUtils.get_or_create_color(color_name)
if not color_id:
    # Obsługa błędu
    return {"error": "Failed to create color"}
```

## Korzyści

- ✅ **Bezpieczeństwo** - automatyczna obsługa błędów i kompensacja
- ✅ **Logowanie** - pełne śledzenie wszystkich operacji
- ✅ **Czytelność** - prostszy i bardziej zrozumiały kod
- ✅ **Konsystencja** - jednolite API dla wszystkich operacji
- ✅ **Testowalność** - łatwiejsze testowanie jednostkowe
- ✅ **Maintenance** - centralizacja logiki operacji między bazami




