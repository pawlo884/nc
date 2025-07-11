# nc_project – dokumentacja

## 1. Opis projektu
Aplikacja Django służąca do zarządzania produktami, wariantami, stanami magazynowymi i cenami detalicznymi, z integracją z zewnętrznymi źródłami (baza MPD). Umożliwia import, eksport, edycję i analizę danych produktowych.

## 2. Struktura katalogów
- `main/` – podstawowa aplikacja, ogólne widoki i modele
- `matterhorn/` – logika importu/eksportu, integracje, szablony admina
- `MPD/` – modele i logika powiązana z bazą MPD (produkty, warianty, ceny, stany)
- `nc/` – konfiguracja projektu, ustawienia, routingi
- `logs/`, `static/`, `staticfiles/` – logi i pliki statyczne

## 3. Modele danych (MPD, matterhorn)
- **MPD**:
  - **Products** – główny model produktu
  - **ProductVariants** – warianty produktu (kolor, rozmiar)
  - **ProductvariantsSources** – powiązania wariantów z dostawcami i EAN
  - **ProductVariantsRetailPrice** – ceny detaliczne wariantów
  - **StockAndPrices** – stany magazynowe i ceny zakupu
  - **Brands, Sizes, Colors, Sources** – słowniki
- **matterhorn**:
  - **Products** – produkty z importów (osobna tabela niż w MPD)
  - **Variants** – warianty produktów (osobna tabela niż w MPD)
  - **Images** – obrazy produktów
  - **OtherColors** – powiązania kolorów między produktami
  - **ProductInSet** – powiązania produktów w zestawach/seriach
  - **UpdateLog** – logi aktualizacji
  - **StockHistory** – historia stanów magazynowych

## 4. Bazy danych
- `default` – domyślna baza Django (np. użytkownicy, sesje)
- `MPD` – główna baza produktowa (produkty, warianty, stany, ceny)
  - Modele MPD korzystają z routera baz danych (`db_routers.py`)
- `matterhorn` – baza importowa (produkty, warianty, obrazy, powiązania, logi)
  - Modele matterhorn korzystają z routera baz danych (`db_routers.py`)

## 5. Widoki i logika
- **Admin Django** – główne zarządzanie produktami, wariantami, cenami
  - Pola readonly: `show_variants`, `edit_retail_prices`, `show_images`, `show_related_products`
- **Import/Eksport** – logika w `matterhorn/defs_import.py`, `MPD/export_to_xml.py` itd.
- **Szablony** – w `templates/`, dedykowane dla admina i użytkownika

## 6. Zależności
- Python 3.8+
- Django 3.x/4.x
- PostgreSQL
- rapidfuzz
- psycopg2

## 7. Uruchamianie projektu
1. Skonfiguruj bazy danych w `nc/settings/`
2. Zainstaluj zależności: `pip install -r requirements.txt`
3. Uruchom serwer: `python manage.py runserver`
4. Panel admina: `/admin/`

## 8. Najczęstsze problemy i rozwiązania
- **ProgrammingError: relation ... does not exist** – sprawdź, czy zapytanie jest wykonywane na właściwej bazie (np. `connections['MPD']`)
- **Błędy importu** – sprawdź, czy wszystkie zależności są zainstalowane
- **Problemy z migracjami** – nie wykonuj migracji na bazie MPD, jeśli nie jest to wymagane

## 9. Kontakt/autorzy
- Główny programista: [Paweł Sowa]
- Zgłaszanie błędów: [pawlo884@gmail.com] 