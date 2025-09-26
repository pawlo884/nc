#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prosty test logiki optymalizacji tytułów jednoczęściowych strojów kąpielowych
"""


def extract_model_name_for_title(text):
    """Symuluje funkcję _extract_model_name_for_title"""
    print(f"🔍 DEBUG: extract_model_name_for_title otrzymał: '{text}'")

    if "Model " not in text:
        print(f"❌ DEBUG: Brak 'Model ' w tekście, zwracam pusty string")
        return ""

    # Sprawdź czy GDZIEKOLWIEK w tytule są słowa "Bralet" lub "Kopa"
    product_types_to_move = []
    types_to_check = ["Bralet", "Kopa"]

    for product_type in types_to_check:
        if product_type in text:
            product_types_to_move.append(product_type)

    # Znajdź część po "Model "
    model_part = text.split("Model ", 1)[1]
    print(f"🔍 DEBUG: Część po 'Model ': '{model_part}'")

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
            # Jeśli to typ produktu który ma być przeniesiony na końcu, nie dodawaj go tutaj
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
    print(f"🔍 DEBUG: Wynik: '{result}'")
    return result


def optimize_jednoczesciowy_title(main_part):
    """Symuluje funkcję _optimize_jednoczesciowy_title"""
    # Sprawdź czy jest "Big" przed "Model" - jeśli tak, zachowaj go do późniejszego przetworzenia
    big_before_model = ""
    if "Big" in main_part and "Model " in main_part:
        # Znajdź pozycję "Model" i sprawdź czy "Big" jest przed nim
        model_index = main_part.find("Model ")
        before_model = main_part[:model_index]
        if "Big" in before_model:
            big_before_model = "Big"

    # Usuń "Kostium jednoczęściowy" z tytułu jeśli występuje przed "Model"
    if "Kostium jednoczęściowy" in main_part and "Model " in main_part:
        # Znajdź pozycję "Model " i usuń wszystko przed nim
        model_index = main_part.find("Model ")
        main_part = main_part[model_index:]

    # Sprawdź czy jest "Model" w tytule
    if "Model " in main_part:
        # Standardowa ścieżka - użyj extract_model_name_for_title
        model_name = extract_model_name_for_title(main_part)
    else:
        # Specjalna ścieżka - bezpośrednio wyczyść tytuł bez "Model"
        model_name = clean_title_directly(main_part)

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

        # Jeśli było "Big" przed "Model", dodaj je na koniec
        if big_before_model and big_before_model not in clean_model_name:
            clean_model_name = f"{clean_model_name} {big_before_model}"

        return f"Jednoczęściowy strój kąpielowy {clean_model_name}"
    return None


def clean_title_directly(title):
    """Czyści tytuł bezpośrednio (gdy nie ma 'Model') - usuwa kolory i typy produktów"""
    # Lista elementów do usunięcia
    elements_to_remove = [
        # Kolory angielskie
        "Multicolor", "Multcolor", "MUlticolor",
        "Black", "White", "Red", "Blue", "Green", "Pink", "Coral",
        "Yellow", "Orange", "Purple", "Brown", "Gray", "Grey", "Navy",
        # Kolory polskie
        "Turkus", "Czarny", "Biały", "Czerwony", "Niebieski", "Zielony",
        "Różowy", "Żółty", "Pomarańczowy", "Fioletowy", "Brązowy", "Szary", "Granatowy",
        # Typy produktów do usunięcia
        "Kostium", "Bikini", "Strój", "Jednoczęściowy", "Dwuczęściowy",
        "Kąpielowy", "Kąpielowe", "Kąpielowa", "jednoczęściowy"
    ]

    # Usuń końcówkę " - Lupo Line" jeśli istnieje
    if " - Lupo Line" in title:
        title = title.split(" - Lupo Line")[0]

    # Podziel na słowa i usuń niepotrzebne elementy
    words = title.split()
    filtered_words = []

    for word in words:
        if word not in elements_to_remove:
            filtered_words.append(word)

    result = " ".join(filtered_words).strip()
    # Trimuj nadmiarowe spacje
    result = " ".join(result.split())
    return result


def test_jednoczesciowy_title_optimization():
    """Testuje optymalizację tytułów jednoczęściowych strojów kąpielowych"""

    # Test case z użytkownika
    test_title = "Jednoczęściowy strój kąpielowy Kostium jednoczęściowy Big Parrot Multicolor - Lupo Line"
    expected_result = "Jednoczęściowy strój kąpielowy Parrot Big"

    print("🧪 Test optymalizacji tytułu jednoczęściowego stroju kąpielowego:")
    print("=" * 80)

    print(f"📝 Tytuł wejściowy:")
    print(f"   {test_title}")
    print()

    # Wywołaj funkcję optymalizacji
    try:
        # Symuluj wywołanie funkcji optymalizacji
        # Najpierw wyciągnij główną część tytułu (bez "Jednoczęściowy strój kąpielowy")
        if test_title.startswith("Jednoczęściowy strój kąpielowy "):
            main_part = test_title[len("Jednoczęściowy strój kąpielowy "):]
        else:
            main_part = test_title

        print(f"🔍 Główna część tytułu (main_part):")
        print(f"   {main_part}")
        print()

        # Wywołaj funkcję optymalizacji
        optimized_title = optimize_jednoczesciowy_title(main_part)

        print(f"🤖 Tytuł zoptymalizowany:")
        print(f"   {optimized_title}")
        print()

        print(f"✅ Oczekiwany wynik:")
        print(f"   {expected_result}")
        print()

        # Sprawdź czy wynik jest poprawny
        if optimized_title == expected_result:
            print("🎉 TEST PRZESZŁ! Tytuł został poprawnie zoptymalizowany.")
        else:
            print("❌ TEST NIE PRZESZŁ! Tytuł nie został poprawnie zoptymalizowany.")
            print(f"   Otrzymano: {optimized_title}")
            print(f"   Oczekiwano: {expected_result}")

    except Exception as e:
        print(f"❌ Błąd podczas testowania: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 80)


def test_additional_jednoczesciowy_cases():
    """Testuje dodatkowe przypadki jednoczęściowych strojów kąpielowych"""

    test_cases = [
        {
            "input": "Kostium jednoczęściowy Model Parrot Big Multicolor - Lupo Line",
            "expected": "Jednoczęściowy strój kąpielowy Parrot Big"
        },
        {
            "input": "Kostium jednoczęściowy Big Model Ocean Wave - Lupo Line",
            "expected": "Jednoczęściowy strój kąpielowy Ocean Wave Big"
        },
        {
            "input": "Model Coral Big Navy - Lupo Line",
            "expected": "Jednoczęściowy strój kąpielowy Coral Big"
        }
    ]

    print("\n🧪 Test dodatkowych przypadków jednoczęściowych strojów:")
    print("=" * 80)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}:")
        print(f"   Wejście: {test_case['input']}")

        try:
            optimized = optimize_jednoczesciowy_title(test_case['input'])
            print(f"   Wynik: {optimized}")
            print(f"   Oczekiwany: {test_case['expected']}")

            if optimized == test_case['expected']:
                print("   ✅ OK")
            else:
                print("   ❌ BŁĄD")

        except Exception as e:
            print(f"   ❌ Błąd: {e}")

    print("=" * 80)


if __name__ == "__main__":
    print("🚀 Uruchamianie testów optymalizacji tytułów jednoczęściowych strojów kąpielowych...")
    print()

    # Test głównego przypadku
    test_jednoczesciowy_title_optimization()

    # Test dodatkowych przypadków
    test_additional_jednoczesciowy_cases()

    print("\n🏁 Testy zakończone!")
