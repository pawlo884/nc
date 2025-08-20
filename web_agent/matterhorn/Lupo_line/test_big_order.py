def extract_model_name_for_title(text):
    """Wyciąga nazwę modelu dla tytułu produktu (zachowuje cechy, usuwa kolory)"""
    if "Model " not in text:
        return ""

    # Sprawdź czy GDZIEKOLWIEK w tytule są słowa "Bralet" lub "Kopa"
    product_types_to_move = []
    types_to_check = ["Bralet", "Kopa"]

    for product_type in types_to_check:
        if product_type in text:
            product_types_to_move.append(product_type)

    # Znajdź część po "Model "
    model_part = text.split("Model ", 1)[1]

    # Usuń końcówkę " - Lupo Line" jeśli istnieje
    if " - Lupo Line" in model_part:
        model_part = model_part.split(" - Lupo Line")[0]

    # Lista elementów do usunięcia z nazwy produktu (kolory, typy produktów, itp.)
    elements_to_remove = [
        # Kolory angielskie
        "Multicolor", "Multcolor", "MUlticolor",  # literówka bez "i"
        "Black", "White", "Red", "Blue", "Green", "Pink", "Coral",
        "Yellow", "Orange", "Purple", "Brown", "Gray", "Grey", "Navy",
        # Kolory polskie
        "Turkus", "Czarny", "Biały", "Czerwony", "Niebieski", "Zielony",
        "Różowy", "Żółty", "Pomarańczowy", "Fioletowy", "Brązowy", "Szary", "Granatowy",
        # Typy produktów do usunięcia
        "Kostium", "Bikini", "Strój", "Jednoczęściowy", "Dwuczęściowy",
        "Kąpielowy", "Kąpielowe", "Kąpielowa"
    ]

    # Podziel na słowa i usuń niepotrzebne elementy
    words = model_part.split()
    filtered_words = []

    for i, word in enumerate(words):
        # WYJĄTEK: Jeśli "Coral" jest pierwszym słowem po "Model", to jest nazwa modelu, nie kolor!
        if word == "Coral" and i == 0:
            # Zachowaj "Coral" jako nazwę modelu
            filtered_words.append(word)
        elif word not in elements_to_remove:
            # Jeśli to typ produktu który ma być przeniesiony na koniec, nie dodawaj go tutaj
            if word in product_types_to_move:
                continue  # Pomiń - zostanie dodany na końcu
            else:
                filtered_words.append(word)

    # Dodaj typy produktów na końcu (jeśli były przed "Model")
    if product_types_to_move:
        filtered_words.extend(product_types_to_move)

    result = " ".join(filtered_words).strip()
    # Trimuj nadmiarowe spacje (usuwaj podwójne spacje)
    result = " ".join(result.split())
    return result


def optimize_figi_title(main_part):
    """Optymalizuje tytuły figów kąpielowych"""
    model_name = extract_model_name_for_title(main_part)
    if model_name:
        # Trimuj nadmiarowe spacje
        clean_model_name = " ".join(model_name.split())

        # Specjalna logika dla słowa "Big" - powinno być na końcu
        words = clean_model_name.split()
        if "Big" in words and not clean_model_name.endswith("Big"):
            # Przenieś "Big" na koniec
            words_without_big = [word for word in words if word != "Big"]
            words_without_big.append("Big")
            clean_model_name = " ".join(words_without_big)

        return f"Figi kąpielowe {clean_model_name}"
    return None


# Testy
test_cases = [
    {
        "input": "Kostium dwuczęściowy Figi 1 Kąpielowe Model Big Elba - Lupo Line",
        "expected": "Figi kąpielowe Elba Big"
    },
    {
        "input": "Kostium dwuczęściowy Figi 1 Kąpielowe Model Elba Big - Lupo Line",
        "expected": "Figi kąpielowe Elba Big"
    },
    {
        "input": "Kostium dwuczęściowy Figi 1 Kąpielowe Model Mirage Big - Lupo Line",
        "expected": "Figi kąpielowe Mirage Big"
    },
    {
        "input": "Kostium dwuczęściowy Figi 1 Kąpielowe Model Big Mirage - Lupo Line",
        "expected": "Figi kąpielowe Mirage Big"
    },
    {
        "input": "Kostium dwuczęściowy Figi 1 Kąpielowe Model Ocean Wave - Lupo Line",
        "expected": "Figi kąpielowe Ocean Wave"
    }
]

print("🧪 Testowanie logiki przenoszenia 'Big' na koniec:")
print("=" * 60)

for i, test_case in enumerate(test_cases, 1):
    print(f"\nTest {i}:")
    print(f"Input: {test_case['input']}")
    result = optimize_figi_title(test_case['input'])
    print(f"Wynik: {result}")
    print(f"Oczekiwany: {test_case['expected']}")

    if result == test_case['expected']:
        print("✅ Poprawny!")
    else:
        print("❌ Błędny!")
        print(f"   Różnica: '{result}' vs '{test_case['expected']}'")
