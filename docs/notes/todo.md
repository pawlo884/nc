# Zgodność modeli Django z IOF 3.0 (XSD)

> **Zadania przeniesione do GitHub Issues** — tracking: [#183](https://github.com/pawlo884/nc/issues/183)
> ([#177](https://github.com/pawlo884/nc/issues/177), [#178](https://github.com/pawlo884/nc/issues/178),
> [#179](https://github.com/pawlo884/nc/issues/179), [#180](https://github.com/pawlo884/nc/issues/180),
> [#181](https://github.com/pawlo884/nc/issues/181)). Wspólne produkty po EAN: [#182](https://github.com/pawlo884/nc/issues/182).
> Poniżej zostaje sama analiza jako materiał referencyjny.

## Analiza zgodności modeli z plikami XSD

### 1. Kategorie (`categories.xsd` / model: `Categories`)

- Brakuje relacji ForeignKey do siebie (parent-child), jest tylko pole `parent_id`.
- Typy i opcjonalność OK.
- W XSD `id` może być stringiem, tu jest liczba – eksport do XML wymaga konwersji.

### 2. Producenci (`producers.xsd` / model: `Brands`)

- `name` powinno być wymagane (`blank=False, null=False`), a jest opcjonalne.
- `id` liczbowy, w XSD string – do eksportu trzeba konwertować.

### 3. Produkty (`full.xsd`/`light.xsd`/model: `Products`)

- `name` powinno być wymagane.
- Relacje do producenta i serii są OK.
- Brakuje powiązania z kategorią (w XSD produkt ma kategorię).
- Brakuje powiązania z jednostką, parametrami, gwarancją (jeśli są wymagane przez XSD).

### 4. Rozmiary (`sizes.xsd` / model: `Sizes`)

- `name` powinno być wymagane.
- Typy OK.
- Brakuje relacji do jednostki (jeśli jednostki są osobną tabelą).

### 5. Serie (`series.xsd` / model: `ProductSeries`)

- `name` powinno być wymagane.

### 6. Jednostki (`units.xsd` / model: brak)

- Brak modelu jednostek (`Units`).

### 7. Warianty produktów (`product_variants`)

- Zgodność OK, relacje są.

### 8. Stany magazynowe (`stocks.xsd` / model: `StockAndPrices`)

- Model przechowuje stany i ceny, powiązania OK.
- Brakuje modelu magazynów jako słownika (jeśli potrzebny).

### 9. Parametry (`parameters.xsd` / model: brak)

- Brak modelu parametrów.

### 10. Gwarancje (`warranties.xsd` / model: brak)

- Brak modelu gwarancji.

### 11. Źródła (`Sources`)

- Model zgodny, pola meta są.

### 12. Obrazy, zestawy, historia, inne

- Modele obrazów, zestawów, historii są, zgodność z XSD zależy od szczegółów eksportu.

---

## Najważniejsze do zgodności z IOF 3.0 (XSD)

Przeniesione do Issues — patrz nagłówek pliku:

| Issue                                             | Zakres                                                                     |
| ------------------------------------------------- | -------------------------------------------------------------------------- |
| [#177](https://github.com/pawlo884/nc/issues/177) | Modele: `Units`, `Parameters`, `ParameterValues`, `Sections`, `Warranties` |
| [#178](https://github.com/pawlo884/nc/issues/178) | Wymagane pola (`blank=False, null=False`) tam, gdzie XSD wymaga            |
| [#179](https://github.com/pawlo884/nc/issues/179) | FK zamiast samych `*_id` (kategorie, jednostki)                            |
| [#180](https://github.com/pawlo884/nc/issues/180) | Konwersja typów `id` liczba ↔ string przy eksporcie do XML                 |
| [#181](https://github.com/pawlo884/nc/issues/181) | Powiązania produktów z kategorią, jednostką, gwarancją, parametrami        |

---

## Wspólne produkty w Mada/Matterhorn/Tabu

[#182](https://github.com/pawlo884/nc/issues/182) — produkty wspólne po EAN we wszystkich trzech hurtowniach
(Mada, Matterhorn, Tabu), `common_products_ean.csv` w root repo, 5453 dopasowań.
