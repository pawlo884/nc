# Adaptery hurtowni dla MPD (linkowanie po EAN)

Katalog zawiera adaptery do łączenia wariantów z zewnętrznych hurtowni z produktami MPD (dopasowanie po EAN).

## Adaptery

- **matterhorn.py** – Matterhorn (productvariant: variant_uid, mapped_variant_uid).
- **tabu.py** – Tabu API (tabu_product_variant: api_id, mapped_variant_uid).

## Wzorzec przy dodawaniu nowej hurtowni

Pełny opis: **docs/MPD_WAREHOUSE_ADAPTER_PATTERN.md**.

Skrót:

1. W hurtowni: model produktu z `mapped_product_uid`, model wariantu z identyfikatorem + opcjonalnie `mapped_variant_uid` i `is_mapped`.
2. Nowa klasa dziedzicząca po `SourceAdapter`: `get_variants_by_eans`, `get_all_variants_for_product`, `update_source_product_mapped`, `update_source_variant_mapped`.
3. W `VariantMatch`: `variant_uid` jako **string** (identyfikator wariantu w hurtowni), `source_product_id`, `producer_code` (lub None).
4. Rejestracja w `registry.py` i wpis w Sources.

## Pliki

- **base.py** – `SourceAdapter`, `VariantMatch`, `normalize_ean`.
- **linking.py** – logika linkowania (wywołuje adaptery, zapisuje PVS i wywołuje `update_source_*`).
- **registry.py** – mapowanie źródło → adapter.
