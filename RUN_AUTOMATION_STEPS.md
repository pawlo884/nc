# Kroki wykonywane przez run_automation

## 1. INICJALIZACJA I WALIDACJA

1. **Załaduj zmienne środowiskowe** z `.env.dev`
2. **Ustaw Django settings** na `nc.settings.dev`
3. **Inicjalizuj Django** (`django.setup()`)
4. **Pobierz parametry**:
   - `--brand` - nazwa marki (opcjonalne)
   - `--category` - nazwa kategorii (opcjonalne)
   - `--active` - filtr active (true/false, opcjonalne)
   - `--is_mapped` - filtr is_mapped (true/false, opcjonalne)
   - `--max` - maksymalna liczba produktów (domyślnie: 1)

## 2. WYSZUKIWANIE MARKI I KATEGORII

5. **Wyszukaj markę w bazie** `matterhorn1` (jeśli podano `--brand`)
   - Szuka po `name__iexact` (case-insensitive)
   - Pobiera `brand_id` z `brand.brand_id`
6. **Sprawdź konfigurację marki** (`BrandConfig`)
   - Jeśli istnieje, używa domyślnych filtrów z konfiguracji
7. **Wyszukaj kategorię w bazie** (jeśli podano `--category`)
   - Szuka po `name__icontains` (case-insensitive, częściowe dopasowanie)
   - Pobiera `category_id` z `category.category_id`

## 3. PRZYGOTOWANIE FILTRÓW

8. **Utwórz filtry** dla produktów:
   - `active`: z parametru `--active` LUB z konfiguracji marki LUB domyślnie `True`
   - `is_mapped`: z parametru `--is_mapped` LUB z konfiguracji marki LUB domyślnie `False`
   - `brand_id`: jeśli znaleziono markę
   - `category_id`: jeśli znaleziono kategorię

## 4. UTWORZENIE REKORDU AUTOMATYZACJI

9. **Utwórz `AutomationRun`** w bazie `web_agent`:
   - `status='running'`
   - `brand_id` (jeśli znaleziono)
   - `category_id` (jeśli znaleziono)
   - `filters` - słownik z filtrami

## 5. KONFIGURACJA PRZEGLĄDARKI

10. **Pobierz konfigurację** z zmiennych środowiskowych:
    - `WEB_AGENT_BASE_URL` (domyślnie: `http://localhost:8080/admin/`)
    - `DJANGO_ADMIN_USERNAME` (domyślnie: `admin`)
    - `DJANGO_ADMIN_PASSWORD` (wymagane)
11. **Sprawdź czy hasło jest ustawione** - jeśli nie, kończy z błędem
12. **Inicjalizuj `BrowserAutomation`**:
    - `base_url`
    - `admin_username`
    - `admin_password`
    - `headless=False` (widoczna przeglądarka)

## 6. URUCHOMIENIE PRZEGLĄDARKI I LOGOWANIE

13. **Uruchom przeglądarkę Chrome** (`browser.start_browser()`)
14. **Zaloguj się do Django Admin** (`browser.login_to_admin()`)
    - Przechodzi do strony logowania
    - Wypełnia username i password
    - Klika przycisk logowania
    - Czeka na przekierowanie do panelu admin

## 7. NAWIGACJA DO LISTY PRODUKTÓW

15. **Przygotuj filtry automatyzacji**:
    - `brand_id` i `brand_name` (jeśli znaleziono markę)
    - `category_id` i `category_name` (jeśli znaleziono kategorię)
    - `active` i `is_mapped` z przygotowanych filtrów
16. **Przejdź do listy produktów** (`browser.navigate_to_product_list()`)
    - URL: `/admin/matterhorn1/product/`
    - Stosuje filtry w URL (query parameters)
    - Czeka na załadowanie listy

## 8. OBSŁUGA PRODUKTÓW (dla każdego produktu do `--max`)

### 8.1. OTWARCIE PRODUKTU

17. **Otwórz pierwszy produkt z listy** (`browser.open_first_product_from_list()`)
    - Klika na pierwszy link produktu w tabeli
    - Czeka na załadowanie strony edycji produktu

### 8.2. KROK 1: EDYCJA NAZWY PRODUKTU

18. **Zaktualizuj nazwę produktu** (`browser.update_product_name()`)
    - Pobiera oryginalną nazwę produktu
    - Zapisuje ją w `browser._original_product_name`
    - Używa AI do ulepszenia nazwy (jeśli dostępne)
    - Wypełnia pole nazwy w formularzu

### 8.3. KROK 2: EDYCJA OPISU PRODUKTU

19. **Zaktualizuj opis produktu** (`browser.update_product_description()`)
    - Pobiera oryginalny opis z formularza
    - Używa AI do ulepszenia opisu (jeśli dostępne)
    - Wypełnia pole "Opis" w formularzu
    - Zwraca ulepszony opis dla dalszego użycia

### 8.4. KROK 3: EDYCJA KRÓTKIEGO OPISU

20. **Zaktualizuj krótki opis** (`browser.update_product_short_description()`)
    - Używa ulepszonego opisu z poprzedniego kroku
    - Generuje krótki opis (skrócona wersja)
    - Wypełnia pole "Krótki opis" w formularzu

### 8.5. KROK 4: WYCIĄGANIE I ZAZNACZANIE ATRYBUTÓW

21. **Pobierz dostępne atrybuty** z formularza (`browser.get_available_attributes()`)
22. **Wyciągnij atrybuty z opisu** używając AI (`ai_processor.extract_attributes_from_description()`)
    - Analizuje ulepszony opis produktu
    - Znajduje atrybuty pasujące do dostępnych w formularzu
    - Zwraca listę ID atrybutów do zaznaczenia
23. **Zaznacz atrybuty w formularzu** (`browser.select_attributes()`)
    - Zaznacza checkboxy dla znalezionych atrybutów

### 8.6. KROK 5: ZAZNACZENIE MARKI W DROPDOWN

24. **Zaznacz markę w dropdown** (`browser.fill_mpd_brand()`)
    - Pobiera markę z formularza Django (pole `id_brand`)
    - Normalizuje nazwę marki (usuwa część w nawiasach, np. "Marko (174)" -> "Marko")
    - Znajduje odpowiednią opcję w dropdownie `mpd_brand`
    - Zaznacza markę w dropdownie (próbuje `select_by_value`, `select_by_visible_text` lub JavaScript)
    - Weryfikuje czy marka została poprawnie zaznaczona

### 8.7. KROK 6: WYBÓR GRUPY ROZMIAROWEJ

25. **Wybierz grupę rozmiarową** (`browser.select_size_category()`)
    - Na podstawie nazwy kategorii wybiera odpowiednią grupę rozmiarową
    - Wypełnia pole "Grupa rozmiarowa" w formularzu

### 8.8. KROK 7: WYBÓR GŁÓWNEGO KOLORU (main_color_id)

26. **Wybierz główny kolor** (`browser.fill_main_color_from_product_color()`)
    - Pobiera wartość koloru z pola `<input type="text" name="color" id="id_color">`
    - Normalizuje nazwę koloru (porównuje case-insensitive)
    - Znajduje odpowiednią opcję w dropdownie `main_color_id` na podstawie nazwy
    - Zaznacza kolor w dropdownie (próbuje `select_by_value`, `select_by_visible_text` lub JavaScript)
    - Weryfikuje czy kolor został poprawnie zaznaczony

### 8.9. KROK 8: WYODRĘBNIANIE I WYPEŁNIANIE KOLORU PRODUCENTA

27. **Wyodrębnij kolor producenta** (`browser.update_producer_color()`)
    - Używa zapisanej oryginalnej nazwy produktu
    - Wyodrębnia kolor z nazwy (np. "czarny", "biały")
    - Mapuje kolor zgodnie z konfiguracją marki (jeśli istnieje)
    - Wypełnia pole "Kolor producenta" w formularzu

### 8.10. KROK 9: WYODRĘBNIANIE I WYPEŁNIANIE KODU PRODUCENTA

28. **Wyodrębnij kod producenta** (`browser.update_producer_code()`)
    - Używa zapisanej oryginalnej nazwy produktu
    - Wyodrębnia kod producenta z nazwy (np. "MK-1234")
    - Wypełnia pole "Kod producenta" w formularzu

### 8.11. KROK 10: USTAWIENIE PLACEHOLDER W POLU SERII (series_name)

29. **Ustaw placeholder w polu series_name** (`browser.fill_series_name_placeholder()`)
    - Znajduje pole `<input type="text" id="series_name">`
    - Czyści pole (zostawia puste jako placeholder)
    - **UWAGA**: Nie wypełniamy faktycznej wartości - pole pozostaje puste

### 8.12. KROK 11: WYBÓR ŚCIEŻKI PRODUKTU

30. **Wybierz ścieżkę produktu** (`browser.select_product_path()`)
    - Dla "Kostiumy Dwuczęciowe" wybiera `value="5"` (Dwuczęściowe)
    - Wypełnia pole "Ścieżka produktu" w formularzu

### 8.13. WYPEŁNIANIE MATERIAŁÓW (SKŁADU)

31. **Wyodrębnij i wypełnij materiały** (`browser.fill_fabric_materials()`)
    - Wyodrębnia informacje o składzie z szczegółów produktu
    - Wypełnia pole "Materiały" lub "Skład" w formularzu

### 8.14. WYBÓR JEDNOSTKI PRODUKTU

33. **Wybierz jednostkę produktu** (`browser.select_unit()`)
    - Wybiera `value="0"` (szt.)
    - Wypełnia pole "Jednostka" w formularzu

### 8.15. TWORZENIE PRODUKTU W MPD

34. **Utwórz produkt w MPD** (`browser.create_mpd_product()`)
    - Szuka przycisku "Utwórz nowy produkt w MPD"
    - Jeśli przycisk istnieje (produkt nie jest zmapowany):
      - Klika przycisk
      - Czeka na utworzenie produktu w MPD
    - Jeśli przycisk nie istnieje (produkt już zmapowany):
      - Pomija ten krok

## 9. ZAKOŃCZENIE

36. **Zostaw przeglądarkę otwartą**
    - Przeglądarka pozostaje otwarta dla ręcznego przetwarzania
    - Wyświetla informacje o `AutomationRun ID`
    - Wyświetla link do wyników w admin panelu

## 10. OBSŁUGA BŁĘDÓW

37. **W przypadku błędów**:
    - Aktualizuje `AutomationRun.status = 'failed'`
    - Zapisuje `error_message` z opisem błędu
    - Zamyka przeglądarkę (jeśli była otwarta)
    - Wyświetla szczegóły błędu w konsoli

## UWAGI

- **Przeglądarka pozostaje otwarta** - użytkownik może ręcznie kontynuować przetwarzanie produktów
- **Domyślne filtry**: `active=True`, `is_mapped=False` (jeśli nie podano innych)
- **Konfiguracja marki**: Jeśli istnieje `BrandConfig` dla marki, używa domyślnych filtrów z konfiguracji
- **AI Processing**: Używane do ulepszania nazwy i opisu produktu (jeśli dostępne)
- **Mapowanie kolorów**: Kolory są mapowane zgodnie z konfiguracją marki (jeśli istnieje)
