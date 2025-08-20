def extract_model_name(text):
    """Wyciąga nazwę modelu dla serii (usuwa kolory, Big/Small, typy produktu)"""
    if "Model " not in text:
        return ""

    # Znajdź część po "Model "
    model_part = text.split("Model ", 1)[1]

    # Usuń końcówkę " - Lupo Line" jeśli istnieje
    if " - Lupo Line" in model_part:
        model_part = model_part.split(" - Lupo Line")[0]

    # Lista wszystkich elementów do usunięcia z nazwy serii
    elements_to_remove = [
        # Kolory angielskie (z wariantami literówek)
        "Multicolor", "Multcolor", "MUlticolor",  # literówka bez "i" i z "MUlticolor"
        "Black", "White", "Red", "Blue", "Green", "Pink", "Coral",
        "Yellow", "Orange", "Purple", "Brown", "Gray", "Grey", "Navy",
        # Kolory polskie
        "Turkus", "Czarny", "Biały", "Czerwony", "Niebieski", "Zielony",
        "Różowy", "Żółty", "Pomarańczowy", "Fioletowy", "Brązowy", "Szary", "Granatowy",
        # Kombinacje kolorów (często występujące)
        "Black/White", "White/Black", "Navy/White", "White/Navy",
        "Red/White", "White/Red", "Blue/White", "White/Blue",
        # Rozmiary (usuwane z serii!)
        "Big", "Small",
        # Typy produktów
        "Kopa", "Bralet", "Push-up", "Push", "up", "Figi", "Biustonosz",
        "Top", "Bikini", "Kostium", "Jednoczęściowy", "Dwuczęściowy", "Szorty"
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
            filtered_words.append(word)

    result = " ".join(filtered_words).strip()

    # Jeśli nie zostało nic, zwróć pusty string
    if not result:
        return ""

    # Trimuj nadmiarowe spacje (usuwaj podwójne spacje)
    result = " ".join(result.split())
    return result


def create_series_name(model_name):
    """Tworzy nazwę serii z nazwy modelu"""
    if not model_name:
        return ""

    return f"strój kąpielowy {model_name} - Lupo Line"


# Testy
test_cases = [
    {
        "input": "Kostium dwuczęściowy Figi 1 Kąpielowe Model Elba MUlticolor - Lupo Line",
        "expected": "strój kąpielowy Elba - Lupo Line"
    },
    {
        "input": "Kostium dwuczęściowy Figi 1 Kąpielowe Model Elba Multicolor - Lupo Line",
        "expected": "strój kąpielowy Elba - Lupo Line"
    },
    {
        "input": "Kostium dwuczęściowy Figi 1 Kąpielowe Model Elba Multcolor - Lupo Line",
        "expected": "strój kąpielowy Elba - Lupo Line"
    },
    {
        "input": "Kostium dwuczęściowy Figi 1 Kąpielowe Model Mirage Big Navy - Lupo Line",
        "expected": "strój kąpielowy Mirage - Lupo Line"
    },
    {
        "input": "Kostium dwuczęściowy Góra Model Fidżi Black/White Big - Lupo Line",
        "expected": "strój kąpielowy Fidżi - Lupo Line"
    }
]

print("🧪 Testowanie usuwania kolorów z nazw serii:")
print("=" * 60)

for i, test_case in enumerate(test_cases, 1):
    print(f"\nTest {i}:")
    print(f"Input: {test_case['input']}")

    model_name = extract_model_name(test_case['input'])
    result = create_series_name(model_name)

    print(f"Model name: {model_name}")
    print(f"Wynik: {result}")
    print(f"Oczekiwany: {test_case['expected']}")

    if result == test_case['expected']:
        print("✅ Poprawny!")
    else:
        print("❌ Błędny!")
        print(f"   Różnica: '{result}' vs '{test_case['expected']}'")
