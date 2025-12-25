# TODO: Zgodność modeli Django z IOF 3.0 (XSD)

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

## Najważniejsze TODO do zgodności z IOF 3.0 (XSD)

- [ ] Dodać modele: `Units`, `Parameters`, `ParameterValues`, `Sections`, `Warranties`.
- [ ] Ustawić wymagane pola (`blank=False, null=False`) tam, gdzie XSD wymaga.
- [ ] Dodać relacje ForeignKey zamiast samych ID tam, gdzie to logiczne (np. kategorie, jednostki).
- [ ] Rozważyć typy pól `id` (jeśli eksportujesz do XML, zadbać o konwersję liczba <-> string).
- [ ] Uzupełnić powiązania produktów z kategorią, jednostką, gwarancją, parametrami.
- [ ] Poprawić modele tak, by były zgodne z wymaganiami XSD IOF 3.0.

---

Jeśli chcesz, mogę przygotować szkice brakujących modeli lub poprawki do istniejących – daj znać, które elementy chcesz uzupełnić w pierwszej kolejności! 