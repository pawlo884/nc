# Wzorzec mapowania produktu hurtownia → MPD

**Wyznacznik** oparty na implementacji Matterhorn1. Przy każdej nowej hurtowni stosuj ten sam schemat – nie opisuj i nie dorabiaj logiki od zera.

Dokument uzupełnia `MPD_WAREHOUSE_ADAPTER_PATTERN.md` (linkowanie wariantów po EAN). Tu opisujemy **pełny flow**: utworzenie produktu w MPD z danych hurtowni, zapis mapowania w hurtowni, warianty, opcjonalnie zdjęcia/ścieżki/atrybuty.

---

## 1. Przepływ kroków (wzór Matterhorn1)

Kolejność operacji przy „mapowaniu produktu z hurtowni do MPD”:

| Krok | Opis | Odpowiedzialność |
|------|------|------------------|
| 1 | **Utwórz produkt w MPD** | Products (name, description, short_description, brand_id, series_id, unit_id, visibility). Marka/seria: get_or_create po nazwie. |
| 2 | **Zapisz mapping w hurtowni** | W modelu produktu hurtowni: `mapped_product_uid = mpd_product_id` (oraz ewent. `is_mapped = True`). |
| 3 | **Ścieżki / atrybuty / skład** (opcjonalnie) | ProductPaths, ProductAttribute, ProductFabric w MPD – jeśli formularz/admin je podaje. |
| 4 | **Utwórz warianty w MPD** | Dla każdego wariantu źródłowego: ProductVariants (product_id, color_id, producer_color_id, size, iai_product_id), ProductvariantsSources (variant, source, ean, variant_uid, producer_code), StockAndPrices (variant, source, stock, price). Źródło (Sources) w MPD: get_or_create po nazwie hurtowni (np. „Tabu API”, „Matterhorn”). |
| 5 | **Zapisz mapping wariantów w hurtowni** | W modelu wariantu hurtowni: `mapped_variant_uid = mpd_variant_id` (oraz ewent. `is_mapped = True`). |
| 6 | **Task linkowania po EAN** | Jedno wywołanie `link_variants_from_other_sources_task(mpd_product_id, source_id)` na koniec – łączy warianty z innych hurtowni po EAN. |
| 7 | **Zdjęcia** (opcjonalnie) | Upload URLi/plików do ProductImage i bucket – jeśli hurtownia ma galerię. |

Kompensacja (np. Saga): przy błędzie w dowolnym kroku cofnij poprzednie (np. usuń produkt z MPD i wyzeruj `mapped_product_uid` w hurtowni). Matterhorn1 używa Saga; Tabu może działać bez Sagi z prostym rollbackiem w transakcji.

---

## 2. Wymagane dane po stronie hurtowni

### 2.1. Model produktu (tabela hurtowni)

| Pole | Typ | Wymagane | Opis |
|------|-----|----------|------|
| `mapped_product_uid` | IntegerField, null=True | tak | ID produktu w MPD (products.id). Gdy null – produkt „niezmapowany”. |
| `is_mapped` | BooleanField (opcjonalnie) | nie | Wygodne do filtrów w adminie (np. „pokaż niezmapowane”). |

Pola do **odczytu** (do wypełnienia MPD): nazwa, opis, short_description, marka (nazwa lub FK), kolor (nazwa), cena (np. w prices/JSON), zdjęcia (URL lub FK do galerii). Konkretna struktura zależy od API hurtowni – ważne, żeby adapter mógł z nich zbudować słownik „dane do MPD”.

### 2.2. Model wariantu (tabela hurtowni)

| Pole | Typ | Wymagane | Opis |
|------|-----|----------|------|
| Identyfikator w źródle | np. `variant_uid` / `api_id` | tak | Unikalny w ramach hurtowni → trafia do ProductvariantsSources.variant_uid. |
| `mapped_variant_uid` | IntegerField, null=True | zalecane | ID wariantu w MPD (product_variants.variant_id). |
| `ean` | CharField (opcjonalnie) | nie | Do PVS i do linkowania po EAN. |
| rozmiar / kolor / stock / cena | – | tak | Do utworzenia ProductVariants, StockAndPrices w MPD. |

---

## 3. Wymagane elementy w MPD (wspólne)

- **Sources** – jeden wpis na hurtownię (np. name zawiera „Tabu API” / „Matterhorn”). Używany w ProductvariantsSources i StockAndPrices.
- **Products** – name, description, short_description, brand_id, series_id, unit_id, visibility.
- **ProductVariants** – product_id, color_id, producer_color_id (opcjonalnie), size (Sizes), iai_product_id.
- **ProductvariantsSources** – variant (MPD), source, ean, variant_uid (string z hurtowni), producer_code (opcjonalnie).
- **StockAndPrices** – variant, source, stock, price, currency, last_updated.
- **Colors / Sizes** – get_or_create po nazwie; Sizes wg kategorii rozmiarów (size_category).

Kolor główny produktu: z pierwszego wariantu lub z produktu; kolor producenta (producer_color): opcjonalnie z formularza (main_color_id + producer_color_name).

---

## 4. Kontrakt w kodzie (MPD.source_adapters.product_mapping_contract)

Aby nowa hurtownia była „jak Matterhorn1”, zaimplementuj:

- **Dane wejściowe do produktu MPD**: name, description, short_description, brand_name, (series_name, unit_id, visibility) – z modelu hurtowni lub form_data.
- **Dane wejściowe do wariantów**: dla każdego wariantu: ean, size (nazwa), stock, price, variant_uid (string), producer_code (opcjonalnie), color (nazwa).
- **Jedna funkcja lub serwis** typu: `create_mpd_product_from_<hurtownia>(source_product_id, form_data=None)` → `{ success, mpd_product_id, error_message }`.
- W środku: utwórz Products, ustaw w hurtowni `mapped_product_uid`, utwórz warianty (ProductVariants + PVS + StockAndPrices), ustaw w hurtowni `mapped_variant_uid`, wywołaj task linkowania po EAN (jeśli tworzono warianty).
- **Opcjonalnie**: ścieżki, atrybuty, skład, zdjęcia – według tego samego wzoru co Matterhorn1 (paths, attributes, fabric, upload_product_images).

Szczegóły interfejsu (klasa bazowa / Protocol) w `src/apps/MPD/source_adapters/product_mapping_contract.py`.

---

## 5. Checklista dla nowej hurtowni (mapowanie produktu)

- [ ] **Model produktu** w hurtowni: `mapped_product_uid` (IntegerField, null=True), ewent. `is_mapped`.
- [ ] **Model wariantu** w hurtowni: unikalny identyfikator (variant_uid/api_id), `mapped_variant_uid` (null=True), ean, rozmiar, stock, cena.
- [ ] **Źródło w MPD**: wpis w Sources (nazwa rozpoznawalna przez adapter).
- [ ] **Serwis/funkcja** `create_mpd_product_from_<hurtownia>(source_product_id, form_data=None)`:
  - [ ] Pobranie produktu i wariantów z hurtowni.
  - [ ] Utworzenie produktu w MPD (Products + Brands/Series po nazwie).
  - [ ] Zapis `mapped_product_uid` w hurtowni.
  - [ ] Ścieżki/atrybuty/skład – jeśli używane (jak we wzorze).
  - [ ] Utworzenie wariantów w MPD (Colors, Sizes, ProductVariants, ProductvariantsSources, StockAndPrices).
  - [ ] Zapis `mapped_variant_uid` w hurtowni dla każdego wariantu.
  - [ ] Wywołanie `link_variants_from_other_sources_task(mpd_product_id, source_id)` (gdy tworzono warianty).
  - [ ] Zdjęcia – jeśli hurtownia ma galerię (jak we wzorze).
- [ ] **Admin** (opcjonalnie): widok produktu z przyciskiem „Utwórz w MPD” / „Przypisz do MPD” i formularzem (nazwa, kategoria rozmiarów, kolor główny, kolor producenta, ścieżki, atrybuty) – wzór: matterhorn1 admin, tabu admin.
- [ ] **Linkowanie po EAN**: adapter w `MPD/source_adapters/<nazwa>.py` (SourceAdapter) – patrz `MPD_WAREHOUSE_ADAPTER_PATTERN.md`; rejestracja w `registry.py`.

Referencja implementacji: **matterhorn1** (`saga.py`, `saga_variants.py`, `database_utils.py`, admin), **tabu** (`services.py`, admin).

---

## 6. Gdzie co leży (referencje Matterhorn1)

| Element | Plik / moduł |
|--------|------------------|
| Tworzenie produktu MPD + mapping w MH | matterhorn1/saga.py – SagaService.create_product_with_mapping, _create_mpd_product, _create_matterhorn_product_with_mapping |
| Tworzenie wariantów MPD + mapping w MH | matterhorn1/saga_variants.py – create_mpd_variants; saga.py – _create_mpd_product_variants |
| Źródło Matterhorn w MPD | Sources (name zawiera „matterhorn”) |
| Admin: „Utwórz w MPD”, „Przypisz”, bulk | matterhorn1/admin.py – assign_mapping, bulk_create_mpd, _get_mpd_product_data |
| Task linkowania po EAN | MPD/tasks.py – link_variants_from_other_sources_task |
| Adapter do linkowania (EAN) | MPD/source_adapters/matterhorn.py – MatterhornAdapter |

Nowa hurtownia: powiel ten układ (serwis tworzenia + mapping, admin z przyciskami, adapter do EAN) i trzymaj się tej samej kolejności kroków oraz pól w tabelach.
