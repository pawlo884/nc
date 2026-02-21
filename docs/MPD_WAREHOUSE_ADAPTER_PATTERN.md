# Wzorzec adaptera hurtowni dla MPD (linkowanie po EAN)

Dokument opisuje pełny wzorzec integracji nowej hurtowni z MPD: model w hurtowni, adapter w `MPD/source_adapters/` oraz zachowanie przy linkowaniu. Wzorzec jest zaimplementowany dla **Matterhorn** i **Tabu** – przy dodawaniu kolejnej hurtowni skorzystaj z tego samego schematu.

**Mapowanie produktu (tworzenie w MPD + mapping w hurtowni):** osobny wzorzec w [docs/mapping/PRODUCT_MAPPING_WZOR.md](mapping/PRODUCT_MAPPING_WZOR.md). Kontrakt w kodzie: `MPD/source_adapters/product_mapping_contract.py`.

---

## 1. Mapowanie w MPD (wspólne dla wszystkich hurtowni)

- **product_variants_sources** – dla każdego wariantu MPD i każdego źródła:
  - `variant_id` – wariant MPD
  - `source_id` – hurtownia (Sources)
  - `ean` – EAN (do dopasowania)
  - `variant_uid` – **identyfikator wariantu w danej hurtowni** (np. Matterhorn: `variant_uid`, Tabu: `api_id`)
  - `producer_code` – kod producenta w tej hurtowni (np. symbol w Tabu; tylko gdy jasno podany, inaczej null)

- **Źródło prawdy** dla mapowania wariantu źródło → MPD to zawsze `product_variants_sources` (PVS). Pola w hurtowni (`mapped_variant_uid` itd.) to **denormalizacja** pod sync stanów i wygodę.

---

## 2. Model produktu w hurtowni

W aplikacji hurtowni (np. `matterhorn1`, `tabu`) model **produktu** powinien mieć:

| Pole | Typ | Opis |
|------|-----|------|
| `mapped_product_uid` | IntegerField, null=True | ID produktu w MPD (product_id w tabeli products). |

Przykład: Matterhorn `Product.mapped_product_uid`, Tabu `TabuProduct.mapped_product_uid`.

---

## 3. Model wariantu w hurtowni (wzorzec)

Wariant (rozmiar/kolor) w hurtowni powinien mieć **identyfikator w systemie źródłowym** (np. `variant_uid`, `api_id`) oraz opcjonalnie pola do mapowania na MPD:

| Pole | Typ | Opis |
|------|-----|------|
| Identyfikator w źródle | np. CharField `variant_uid` lub IntegerField `api_id` | Unikalny w ramach hurtowni (używany jako `variant_uid` w PVS). |
| `mapped_variant_uid` | IntegerField, null=True, db_index=True | **ID wariantu w MPD** (variant_id). Ustawiane przy linkowaniu. Używane m.in. w syncu stanów (Matterhorn). |
| `is_mapped` | BooleanField, null=True | Czy wariant jest zmapowany do MPD (opcjonalnie, dla spójności z Matterhorn). |

- **Matterhorn:** `ProductVariant.variant_uid`, `mapped_variant_uid`, `is_mapped`.
- **Tabu:** `TabuProductVariant.api_id`, `mapped_variant_uid`, `is_mapped`.

Bez `mapped_variant_uid` da się obejść (mapowanie da się odtworzyć z PVS), ale z tym polem sync stanów i zapytania są prostsze.

---

## 4. Adapter w MPD (`source_adapters/<nazwa>.py`)

Adapter dziedziczy po `SourceAdapter` (z `base.py`) i musi zaimplementować:

### 4.1. Wymagane

- **`get_variants_by_eans(ean_list, mpd_product_id=None)`**  
  Zwraca listę `VariantMatch` dla podanych EAN (i opcjonalnie produktu MPD).  
  W każdym `VariantMatch`:
  - `ean` – znormalizowany EAN
  - **`variant_uid`** – **string** identyfikatora wariantu w hurtowni (np. `str(v.variant_uid)` lub `str(v.api_id)`) – to trafia do PVS i do `update_source_variant_mapped`
  - `source_product_id` – PK produktu w hurtowni (do `update_source_product_mapped` i `update_source_variant_mapped`)
  - `producer_code` – tylko gdy hurtownia ma takie pole; gdy brak lub puste → przekazać `None` (w PVS będzie null)
  - stock, price, currency, size, color itd. według potrzeb

### 4.2. Opcjonalne (ale zalecane)

- **`get_all_variants_for_product(source_product_id)`**  
  Wszystkie warianty produktu w hurtowni – do dopinania „pozostałych” rozmiarów przy linkowaniu (te same pola co wyżej, w tym `variant_uid` jako string).

- **`update_source_product_mapped(source_product_id, mpd_product_id)`**  
  Ustaw w hurtowni na **produkcie**: `mapped_product_uid = mpd_product_id` (oraz ewentualnie `is_mapped=True` jeśli jest).

- **`update_source_variant_mapped(source_product_id, source_variant_uid, mpd_variant_id)`**  
  Ustaw w hurtowni na **wariancie**: `mapped_variant_uid = mpd_variant_id` (i ewentualnie `is_mapped=True`).  
  - `source_variant_uid` – ten sam string co `VariantMatch.variant_uid` (np. `variant_uid` w MH, `str(api_id)` w Tabu).  
  - Szukanie wariantu: po `(product_id = source_product_id, variant_uid/api_id = source_variant_uid)`.

---

## 5. Rejestracja adaptera

W **`MPD/source_adapters/registry.py`** dodać mapowanie: nazwa źródła (np. z `Sources.name`) → klasa adaptera.  
Linkowanie wywołuje adaptery z tego rejestru.

---

## 6. Przepływ przy linkowaniu (dla Ciebie jako implementatora)

1. Użytkownik lub task dopina warianty do produktu MPD (np. po EAN).
2. Dla każdego dopasowania z hurtowni:
   - Tworzony/jest rekord w **product_variants_sources** (variant_id MPD, source_id, ean, **variant_uid** z `VariantMatch.variant_uid`, producer_code tylko gdy podany).
   - Tworzony/jest **StockAndPrices** (stany/ceny).
   - Wywołanie **`adapter.update_source_product_mapped(source_product_id, mpd_product_id)`** – raz na produkt.
   - Wywołanie **`adapter.update_source_variant_mapped(source_product_id, variant_uid, mpd_variant_id)`** – dla każdego wariantu (ustawia `mapped_variant_uid` / `is_mapped` w hurtowni).

Dzięki temu po stronie hurtowni masz uzupełnione `mapped_product_uid` na produkcie i `mapped_variant_uid` (oraz opcjonalnie `is_mapped`) na wariantach – spójnie z Matterhorn i Tabu.

---

## 7. Podsumowanie checklisty dla nowej hurtowni

- [ ] Model **produktu**: pole `mapped_product_uid` (IntegerField, null=True).
- [ ] Model **wariantu**: unikalny identyfikator w źródle + opcjonalnie `mapped_variant_uid`, `is_mapped`.
- [ ] **Migracje** dla nowych pól.
- [ ] Klasa adaptera w `MPD/source_adapters/<nazwa>.py`:
  - [ ] `get_variants_by_eans` zwracające `VariantMatch` z `variant_uid` (string), `source_product_id`, `producer_code` (lub None).
  - [ ] `get_all_variants_for_product` (zalecane).
  - [ ] `update_source_product_mapped`.
  - [ ] `update_source_variant_mapped` (gdy wariant ma `mapped_variant_uid`).
- [ ] Rejestracja adaptera w `registry.py`.
- [ ] W tabeli **Sources** (MPD) wpis dla nowej hurtowni (nazwa zgodna z `source_name` w adapterze).

Referencja kodu: **Matterhorn** (`matterhorn.py`) i **Tabu** (`tabu.py`).
