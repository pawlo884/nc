# 📋 Lista pomijanych produktów - Instrukcja obsługi

## 🎯 Cel

Agent MPD może pomijać wybrane produkty podczas automatycznego przetwarzania. Jest to przydatne gdy:
- Produkty są duplikatami w źródle danych
- Niektóre produkty zostały już przetworzone ręcznie
- Chcesz wykluczyć problematyczne produkty

## 📂 Pliki

- `skip_products_list.py` - główny plik z listą ID do pominięcia
- `README_skip_products.md` - ten plik z instrukcjami

## 🔧 Jak dodać produkty do listy pomijanych

### Metoda 1: Edycja pliku (zalecana)

1. Otwórz plik `web_agent/skip_products_list.py`
2. Znajdź listę `SKIP_PRODUCT_IDS = []`
3. Dodaj ID produktów do listy:

```python
SKIP_PRODUCT_IDS = [
    214962,  # Duplikat produktu Mirage Big
    215001,  # Błędny produkt bez opisu
    215123,  # Już przetworzony ręcznie
    215200,  # Problematyczny import
]
```

4. Zapisz plik

### Metoda 2: Test funkcji

Uruchom plik bezpośrednio aby sprawdzić status:

```bash
cd web_agent
python skip_products_list.py
```

## 🤖 Jak agent używa listy

1. **Przed kliknięciem w produkt** - agent sprawdza ID pierwszego produktu na liście
2. **Jeśli ID jest na liście pomijanych** - agent pomija ten produkt i próbuje kliknąć w następny
3. **Jeśli następny też jest pomijany** - agent kończy pracę na tej stronie
4. **Komunikaty w konsoli**:
   ```
   🔍 Sprawdzam pierwszy produkt (ID: 214962)
   ⏭️ Pomijam produkt ID 214962 - jest na liście pomijanych
   🔍 Sprawdzam drugi produkt (ID: 214963)
   🎯 Klikam w drugi produkt (ID: 214963)
   ```

## 📊 Status listy

Agent wyświetla status listy przy starcie:

```
📋 Status listy pomijanych produktów:
   Liczba produktów: 4
   ⚠️ Produkty do pominięcia: [214962, 215001, 215123, 215200]
   💡 Aby dodać produkty, edytuj plik: web_agent/skip_products_list.py
```

## 🔍 Jak znaleźć ID produktów do pominięcia

### Metoda 1: Z konsoli agenta
Gdy agent uruchomi się, wyświetli ID każdego produktu:
```
🔍 Sprawdzam pierwszy produkt (ID: 214962)
```

### Metoda 2: Z panelu Django Admin
1. Przejdź do listy produktów w panelu admin
2. ID produktu jest w pierwszej kolumnie tabeli
3. Skopiuj ID produktów które chcesz pominąć

### Metoda 3: Z URL produktu
URL szczegółów produktu zawiera ID:
```
http://localhost:8000/admin/matterhorn/products/214962/change/
                                                    ^^^^^^
                                                  ID produktu
```

## ⚠️ Ważne uwagi

1. **Lista jest statyczna** - musisz ręcznie edytować plik aby dodać nowe ID
2. **Restart agenta** - zmiany w liście wymagają restartu agenta
3. **Duplikaty są automatycznie usuwane** - nie martw się o powtarzające się ID
4. **Walidacja ID** - nieprawidłowe ID (tekst, null) są ignorowane

## 🧪 Przykłady testów

```python
from skip_products_list import should_skip_product

# Testy
print(should_skip_product(214962))    # True jeśli ID jest na liście
print(should_skip_product('215001'))  # True - string też działa
print(should_skip_product('abc'))     # False - nieprawidłowe ID
print(should_skip_product(999999))    # False - ID nie na liście
```

## 🔄 Workflow z pomijaniem

1. **Uruchom agenta** - zobaczy status listy pomijanych
2. **Agent sprawdza każdy produkt** - przed kliknięciem
3. **Pomija duplikaty** - automatycznie przechodzi do następnego
4. **Kontynuuje pracę** - aż zabraknie dostępnych produktów
5. **Dodaj nowe ID** - gdy znajdziesz więcej duplikatów

## 💡 Wskazówki

- **Prowadź notatki** - zapisuj powody pomijania produktów jako komentarze
- **Sprawdzaj regularnie** - usuń ID z listy gdy produkt zostanie naprawiony
- **Backup listy** - skopiuj listę przed dużymi zmianami
- **Testuj na małej grupie** - przed dodaniem wielu ID na raz
