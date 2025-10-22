# 🔌 Integracja nowej hurtowni do MPD - Przewodnik krok po kroku

## 📋 Przygotowanie

### Co będziesz potrzebować:
1. **Dane z hurtowni**:
   - Lista produktów (nazwa, opis, ceny)
   - Nazwy marek
   - Kategorie produktów
   - Rozmiary i kolory
   - Kody EAN/SKU

2. **Dostęp do systemu**:
   - Token API lub login do Django Admin
   - URL do API: `https://twoja-domena.com/mpd/`

---

## 🎯 Krok 1: Dodaj źródło (Source) w bazie danych

### Przez Django Admin:
1. Zaloguj się do `/admin/`
2. Przejdź do **MPD → Sources**
3. Kliknij **"Add Source"**
4. Wypełnij dane:
   ```
   Name: NowaHurtownia
   Long name: Nowa Hurtownia Sp. z o.o.
   Short name: NH
   Type: hurtownia
   Location: Warszawa
   Email: kontakt@nowahurtownia.pl
   Tel: +48 123 456 789
   WWW: https://nowahurtownia.pl
   Street: ul. Główna 1
   Zipcode: 00-001
   City: Warszawa
   Country: Polska
   ```
5. Zapisz - zanotuj **ID źródła** (np. 3)

### Przez SQL (opcjonalnie):
```sql
INSERT INTO sources (name, long_name, short_name, type, location, email, tel, www, street, zipcode, city, country)
VALUES (
    'NowaHurtownia',
    'Nowa Hurtownia Sp. z o.o.',
    'NH',
    'hurtownia',
    'Warszawa',
    'kontakt@nowahurtownia.pl',
    '+48 123 456 789',
    'https://nowahurtownia.pl',
    'ul. Główna 1',
    '00-001',
    'Warszawa',
    'Polska'
);
```

---

## 🎯 Krok 2: Przygotuj dane produktów

### Przykładowy format JSON dla jednego produktu:

```json
{
  "name": "Sukienka letnia NowaHurtownia",
  "description": "Lekka sukienka na lato, idealna na upały",
  "short_description": "Sukienka damska",
  "brand_name": "NowaHurtownia",
  "size_category": "standard",
  "series_name": "Lato 2024",
  "unit_id": 1,
  "visibility": true
}
```

### Przykładowy skrypt Python do przygotowania danych:

```python
# prepare_products.py
import json

# Twoje produkty z hurtowni
raw_products = [
    {
        "sku": "NH-001",
        "name": "Sukienka letnia",
        "description": "Lekka sukienka na lato",
        "brand": "NowaHurtownia",
        "price": 89.99,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Czerwony", "Niebieski"]
    },
    {
        "sku": "NH-002",
        "name": "Spódnica midi",
        "description": "Elegancka spódnica do kolan",
        "brand": "NowaHurtownia",
        "price": 69.99,
        "sizes": ["S", "M", "L"],
        "colors": ["Czarny", "Biały"]
    }
]

# Przekształć do formatu MPD
mpd_products = []
for product in raw_products:
    mpd_product = {
        "name": product["name"],
        "description": product["description"],
        "short_description": product["name"],
        "brand_name": product["brand"],
        "size_category": "standard",
        "series_name": "Kolekcja 2024",
        "unit_id": 1,  # sztuka
        "visibility": True
    }
    mpd_products.append(mpd_product)

# Zapisz do pliku
with open("products_to_import.json", "w", encoding="utf-8") as f:
    json.dump({"products": mpd_products}, f, indent=2, ensure_ascii=False)

print(f"✅ Przygotowano {len(mpd_products)} produktów do importu")
```

---

## 🎯 Krok 3: Import produktów do MPD

### Opcja A: Bulk Import (zalecane dla >10 produktów)

```python
# import_products.py
import requests
import json

BASE_URL = "https://twoja-domena.com/mpd"
API_TOKEN = "twoj_token_tutaj"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# Wczytaj przygotowane produkty
with open("products_to_import.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"📦 Importuję {len(data['products'])} produktów...")

# Wykonaj bulk import
response = requests.post(
    f"{BASE_URL}/bulk-create/",
    headers=headers,
    data=json.dumps(data)
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ Sukces! Utworzono {result['total_created']} produktów")
    print(f"❌ Błędów: {len(result['errors'])}")
    
    if result['errors']:
        print("\nBłędy:")
        for error in result['errors']:
            print(f"  - {error}")
    
    # Zapisz ID utworzonych produktów
    created_ids = [p['id'] for p in result['created_products']]
    with open("created_product_ids.json", "w") as f:
        json.dump(created_ids, f)
    
    print(f"\n💾 Zapisano ID produktów do: created_product_ids.json")
else:
    print(f"❌ Błąd: {response.status_code}")
    print(response.text)
```

### Opcja B: Pojedyncze dodawanie

```python
# import_single_product.py
import requests
import json

BASE_URL = "https://twoja-domena.com/mpd"
API_TOKEN = "twoj_token_tutaj"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# Pojedynczy produkt
product_data = {
    "name": "Sukienka letnia NowaHurtownia",
    "description": "Lekka sukienka na lato, idealna na upały",
    "short_description": "Sukienka damska",
    "brand_name": "NowaHurtownia",
    "series_name": "Lato 2024",
    "unit_id": 1,
    "visibility": True
}

response = requests.post(
    f"{BASE_URL}/products/create/",
    headers=headers,
    data=json.dumps(product_data)
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ Utworzono produkt ID: {result['product_id']}")
    print(f"   Nazwa: {result['product_name']}")
else:
    print(f"❌ Błąd: {response.status_code}")
    print(response.text)
```

---

## 🎯 Krok 4: Dodaj kategorie (ścieżki) do produktów

```python
# assign_categories.py
import requests
import json

BASE_URL = "https://twoja-domena.com/mpd"
API_TOKEN = "twoj_token_tutaj"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# Wczytaj ID utworzonych produktów
with open("created_product_ids.json", "r") as f:
    product_ids = json.load(f)

# ID kategorii do przypisania (sprawdź w admin panel: MPD → Paths)
category_ids = [10, 15, 20]  # np. Odzież > Sukienki > Letnie

print(f"📂 Przypisuję kategorie do {len(product_ids)} produktów...")

for product_id in product_ids:
    for category_id in category_ids:
        data = {
            "product_id": product_id,
            "path_id": category_id,
            "action": "assign"
        }
        
        response = requests.post(
            f"{BASE_URL}/manage-product-paths/",
            headers=headers,
            data=json.dumps(data)
        )
        
        if response.status_code == 200:
            print(f"✅ Produkt {product_id}: przypisano kategorię {category_id}")
        else:
            print(f"❌ Produkt {product_id}: błąd kategorii {category_id}")

print("🏁 Zakończono przypisywanie kategorii")
```

---

## 🎯 Krok 5: Dodaj atrybuty do produktów

```python
# assign_attributes.py
import requests
import json

BASE_URL = "https://twoja-domena.com/mpd"
API_TOKEN = "twoj_token_tutaj"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# Wczytaj ID produktów
with open("created_product_ids.json", "r") as f:
    product_ids = json.load(f)

# ID atrybutów (sprawdź w admin: MPD → Attributes)
# np. 1=Nowość, 2=Promocja, 3=Bestseller
attribute_ids = [1, 3]

print(f"🏷️ Dodaję atrybuty do produktów...")

for product_id in product_ids:
    data = {
        "product_id": product_id,
        "action": "add",
        "attribute_ids": attribute_ids
    }
    
    response = requests.post(
        f"{BASE_URL}/manage-product-attributes/",
        headers=headers,
        data=json.dumps(data)
    )
    
    if response.status_code == 200:
        print(f"✅ Produkt {product_id}: dodano atrybuty")
    else:
        print(f"❌ Produkt {product_id}: błąd dodawania atrybutów")

print("🏁 Zakończono dodawanie atrybutów")
```

---

## 🎯 Krok 6: Weryfikacja i testy

### Sprawdź utworzone produkty:

```python
# verify_products.py
import requests
import json

BASE_URL = "https://twoja-domena.com/mpd"
API_TOKEN = "twoj_token_tutaj"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# Wczytaj ID produktów
with open("created_product_ids.json", "r") as f:
    product_ids = json.load(f)

print(f"🔍 Weryfikuję {len(product_ids)} produktów...\n")

for product_id in product_ids:
    response = requests.get(
        f"{BASE_URL}/products/{product_id}/",
        headers=headers
    )
    
    if response.status_code == 200:
        product = response.json()['product']
        print(f"✅ Produkt {product_id}:")
        print(f"   Nazwa: {product['name']}")
        print(f"   Marka: {product['brand_id']}")
        print(f"   Kategorie: {len(product['paths'])} szt.")
        print(f"   Atrybuty: {len(product['attributes'])} szt.")
        print(f"   Widoczny: {product['visibility']}")
        print()
    else:
        print(f"❌ Produkt {product_id}: błąd pobierania")

print("🏁 Weryfikacja zakończona")
```

### Sprawdź w Django Admin:
1. Przejdź do `/admin/`
2. **MPD → Products**
3. Filtruj po marce: "NowaHurtownia"
4. Sprawdź czy wszystkie dane są poprawne

---

## 🎯 Krok 7: Generowanie XML dla zewnętrznych systemów

Po dodaniu produktów, możesz wygenerować pliki XML:

```python
# generate_xml.py
import requests

BASE_URL = "https://twoja-domena.com/mpd"
API_TOKEN = "twoj_token_tutaj"

headers = {
    "Authorization": f"Token {API_TOKEN}"
}

print("🔄 Generuję pliki XML...")

# 1. Gateway XML (linki do wszystkich plików)
response = requests.get(
    f"{BASE_URL}/generate-gateway-xml-api/",
    headers=headers
)
if response.status_code == 200:
    with open("gateway.xml", "wb") as f:
        f.write(response.content)
    print("✅ gateway.xml")

# 2. Full XML (wszystkie produkty)
response = requests.post(
    f"{BASE_URL}/generate-full-xml/",
    headers=headers
)
if response.status_code == 200:
    with open("full.xml", "wb") as f:
        f.write(response.content)
    print("✅ full.xml")

# 3. Light XML (uproszczona wersja)
response = requests.post(
    f"{BASE_URL}/generate-light-xml/",
    headers=headers
)
if response.status_code == 200:
    with open("light.xml", "wb") as f:
        f.write(response.content)
    print("✅ light.xml")

print("🏁 Pliki XML wygenerowane")
```

---

## 📊 Kompletny skrypt automatyzacji

Wszystko w jednym pliku:

```python
# complete_integration.py
import requests
import json
import time

class MPDIntegration:
    def __init__(self, base_url, api_token):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json"
        }
    
    def import_products(self, products):
        """Importuje produkty do MPD"""
        print(f"📦 Importuję {len(products)} produktów...")
        
        data = {"products": products}
        response = requests.post(
            f"{self.base_url}/bulk-create/",
            headers=self.headers,
            data=json.dumps(data)
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Utworzono {result['total_created']} produktów")
            return [p['id'] for p in result['created_products']]
        else:
            print(f"❌ Błąd: {response.status_code}")
            return []
    
    def assign_categories(self, product_ids, category_ids):
        """Przypisuje kategorie do produktów"""
        print(f"📂 Przypisuję kategorie...")
        
        for product_id in product_ids:
            for category_id in category_ids:
                data = {
                    "product_id": product_id,
                    "path_id": category_id,
                    "action": "assign"
                }
                requests.post(
                    f"{self.base_url}/manage-product-paths/",
                    headers=self.headers,
                    data=json.dumps(data)
                )
                time.sleep(0.1)  # Rate limiting
        
        print(f"✅ Przypisano kategorie")
    
    def assign_attributes(self, product_ids, attribute_ids):
        """Dodaje atrybuty do produktów"""
        print(f"🏷️ Dodaję atrybuty...")
        
        for product_id in product_ids:
            data = {
                "product_id": product_id,
                "action": "add",
                "attribute_ids": attribute_ids
            }
            requests.post(
                f"{self.base_url}/manage-product-attributes/",
                headers=self.headers,
                data=json.dumps(data)
            )
            time.sleep(0.1)
        
        print(f"✅ Dodano atrybuty")
    
    def generate_xml(self):
        """Generuje pliki XML"""
        print("🔄 Generuję XML...")
        
        # Gateway XML
        response = requests.get(
            f"{self.base_url}/generate-gateway-xml-api/",
            headers=self.headers
        )
        if response.status_code == 200:
            print("✅ gateway.xml")
        
        # Full XML
        response = requests.post(
            f"{self.base_url}/generate-full-xml/",
            headers=self.headers
        )
        if response.status_code == 200:
            print("✅ full.xml")
        
        print("🏁 XML wygenerowany")

# UŻYCIE
if __name__ == "__main__":
    # Konfiguracja
    integration = MPDIntegration(
        base_url="https://twoja-domena.com/mpd",
        api_token="twoj_token_tutaj"
    )
    
    # Produkty do importu
    products = [
        {
            "name": "Sukienka NowaHurtownia 1",
            "description": "Lekka sukienka na lato",
            "short_description": "Sukienka damska",
            "brand_name": "NowaHurtownia",
            "series_name": "Lato 2024",
            "unit_id": 1,
            "visibility": True
        },
        {
            "name": "Spódnica NowaHurtownia 1",
            "description": "Elegancka spódnica midi",
            "short_description": "Spódnica damska",
            "brand_name": "NowaHurtownia",
            "series_name": "Lato 2024",
            "unit_id": 1,
            "visibility": True
        }
    ]
    
    # 1. Import produktów
    product_ids = integration.import_products(products)
    
    if product_ids:
        # 2. Przypisz kategorie (ID z admin panel)
        integration.assign_categories(product_ids, [10, 15])
        
        # 3. Dodaj atrybuty (ID z admin panel)
        integration.assign_attributes(product_ids, [1, 3])
        
        # 4. Wygeneruj XML
        integration.generate_xml()
        
        print(f"\n🎉 Integracja zakończona!")
        print(f"📊 Utworzono {len(product_ids)} produktów")
        print(f"💾 ID produktów: {product_ids}")
```

---

## 🔧 Przydatne komendy

### Sprawdź dostępne kategorie:
```python
# list_categories.py
import requests

response = requests.get("https://twoja-domena.com/admin/MPD/paths/")
# Sprawdź w Django Admin: MPD → Paths
```

### Sprawdź dostępne atrybuty:
```python
# list_attributes.py
import requests

# Sprawdź w Django Admin: MPD → Attributes
```

### Sprawdź dostępne jednostki:
```python
# list_units.py
import requests

# Sprawdź w Django Admin: MPD → Units
# Typowe: 1=sztuka, 2=para, 3=komplet
```

---

## 📝 Checklist integracji

- [ ] Dodano źródło (Source) w bazie danych
- [ ] Przygotowano dane produktów w formacie JSON
- [ ] Zaimportowano produkty przez API
- [ ] Przypisano kategorie do produktów
- [ ] Dodano atrybuty do produktów
- [ ] Zweryfikowano produkty w Django Admin
- [ ] Wygenerowano pliki XML
- [ ] Przetestowano integrację end-to-end

---

## 🚨 Najczęstsze problemy

### Problem 1: "Brand not found"
**Rozwiązanie**: Utwórz markę w Django Admin (MPD → Brands) przed importem

### Problem 2: "Unit_id required"
**Rozwiązanie**: Dodaj `unit_id: 1` (sztuka) do wszystkich produktów

### Problem 3: "Unauthorized"
**Rozwiązanie**: Sprawdź czy token API jest poprawny

### Problem 4: Rate limiting
**Rozwiązanie**: Dodaj `time.sleep(0.1)` między requestami

---

## 📞 Potrzebujesz pomocy?

1. Sprawdź pełną dokumentację: `MPD_API_DOKUMENTACJA.md`
2. Zobacz logi: `/logs/matterhorn/`
3. Django Admin: `/admin/`
4. Swagger UI: `/api/docs/`

---

**Powodzenia z integracją! 🚀**
