def clean_model_name_from_colors(model_name):
    """Usuwa kolory z nazwy modelu (pozostawia główną nazwę)"""
    # Lista kolorów do usunięcia (pojedyncze i kombinacje)
    colors_to_remove = [
        # Kolory angielskie
        "Multicolor", "Multcolor", "MUlticolor",  # literówka bez "i"
        "Black", "White", "Red", "Blue", "Green", "Pink", "Coral",
        "Yellow", "Orange", "Purple", "Brown", "Gray", "Grey", "Navy",
        # Kolory polskie
        "Turkus", "Czarny", "Biały", "Czerwony", "Niebieski", "Zielony",
        "Różowy", "Żółty", "Pomarańczowy", "Fioletowy", "Brązowy", "Szary", "Granatowy",
        # Kombinacje kolorów (często występujące)
        "Black/White", "White/Black", "Navy/White", "White/Navy",
        "Red/White", "White/Red", "Blue/White", "White/Blue"
    ]

    # Podziel na słowa
    words = model_name.split()
    filtered_words = []

    for word in words:
        # Sprawdź czy to nie jest kolor do usunięcia
        is_color = False
        for color in colors_to_remove:
            if word == color:
                is_color = True
                break

        if not is_color:
            filtered_words.append(word)

    result = " ".join(filtered_words).strip()
    return result


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


def optimize_top_title(main_part):
    """Optymalizuje tytuły biustonoszy kąpielowych"""
    model_name = extract_model_name_for_title(main_part)
    if model_name:
        # Sprawdź typ biustonosza na podstawie nazwy modelu lub opisu
        if "Bralet" in model_name:
            # Usuń kolory i "Bralet" z nazwy modelu, dodaj "Bralet" jako typ
            clean_model = clean_model_name_from_colors(model_name)
            clean_model = clean_model.replace("Bralet", "").strip()
            # Trimuj nadmiarowe spacje
            clean_model = " ".join(clean_model.split())
            return f"Biustonosz kąpielowy {clean_model} Bralet"
        elif "Kopa" in model_name:
            # Usuń kolory i "Kopa" z nazwy modelu, dodaj "Kopa" jako typ
            clean_model = clean_model_name_from_colors(model_name)
            clean_model = clean_model.replace("Kopa", "").strip()
            # Trimuj nadmiarowe spacje
            clean_model = " ".join(clean_model.split())
            return f"Biustonosz kąpielowy {clean_model} Kopa"
        elif "Big" in model_name:
            # Specjalna logika dla słowa "Big" - usuń kolory i przenieś "Big" na koniec
            clean_model = clean_model_name_from_colors(model_name)

            # Przenieś "Big" na koniec jeśli nie jest już na końcu
            words = clean_model.split()
            if "Big" in words and not clean_model.endswith("Big"):
                words_without_big = [word for word in words if word != "Big"]
                words_without_big.append("Big")
                clean_model = " ".join(words_without_big)

            # Trimuj nadmiarowe spacje
            clean_model = " ".join(clean_model.split())
            return f"Biustonosz kąpielowy {clean_model}"
        else:
            # Usuń kolory z nazwy modelu
            clean_model_name = clean_model_name_from_colors(model_name)
            # Trimuj nadmiarowe spacje
            clean_model_name = " ".join(clean_model_name.split())
            return f"Biustonosz kąpielowy {clean_model_name}"
    return None


# Testy
test_cases = [
    {
        "input": "Kostium dwuczęściowy Góra Model Fidżi Black/White Big - Lupo Line",
        "expected": "Biustonosz kąpielowy Fidżi Big"
    },
    {
        "input": "Kostium dwuczęściowy Góra Model Big Fidżi Black/White - Lupo Line",
        "expected": "Biustonosz kąpielowy Fidżi Big"
    },
    {
        "input": "Kostium dwuczęściowy Góra Model Elena Navy Bralet - Lupo Line",
        "expected": "Biustonosz kąpielowy Elena Bralet"
    },
    {
        "input": "Kostium dwuczęściowy Góra Model Paradise White/Blue Kopa - Lupo Line",
        "expected": "Biustonosz kąpielowy Paradise Kopa"
    },
    {
        "input": "Kostium dwuczęściowy Góra Model Ocean Red/White - Lupo Line",
        "expected": "Biustonosz kąpielowy Ocean"
    }
]

print("🧪 Testowanie usuwania kolorów z biustonoszy:")
print("=" * 60)

for i, test_case in enumerate(test_cases, 1):
    print(f"\nTest {i}:")
    print(f"Input: {test_case['input']}")
    result = optimize_top_title(test_case['input'])
    print(f"Wynik: {result}")
    print(f"Oczekiwany: {test_case['expected']}")

    if result == test_case['expected']:
        print("✅ Poprawny!")
    else:
        print("❌ Błędny!")
        print(f"   Różnica: '{result}' vs '{test_case['expected']}'")
