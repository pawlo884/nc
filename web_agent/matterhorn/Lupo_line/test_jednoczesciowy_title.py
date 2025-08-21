#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test optymalizacji tytułów jednoczęściowych strojów kąpielowych
"""

from products_navigator import ProductsNavigator
import sys
import os

# Dodaj ścieżkę do modułu products_navigator
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_jednoczesciowy_title_optimization():
    """Testuje optymalizację tytułów jednoczęściowych strojów kąpielowych"""

    # Inicjalizuj nawigator (bez logowania do bazy danych)
    navigator = ProductsNavigator()

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
        optimized_title = navigator._optimize_jednoczesciowy_title(main_part)

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

    navigator = ProductsNavigator()

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
            optimized = navigator._optimize_jednoczesciowy_title(
                test_case['input'])
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

