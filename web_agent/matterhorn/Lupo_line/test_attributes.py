#!/usr/bin/env python3
"""
Test poprawionej logiki wykluczania atrybutów ramiączek
"""

from products_navigator import ProductEditor


def test_attributes_exclusion():
    """Testuje czy atrybuty ramiączek są poprawnie wykluczane"""
    
    # Tworzymy instancję edytora (bez nawigatora)
    editor = ProductEditor()
    
    test_cases = [
        {
            "name": "Tylko odpinane ramiączka",
            "description": "Biustonosz z odpinane ramiączka, bardzo wygodny",
            "expected_attributes": [12],  # Tylko odpinane ramiączka
            "excluded_attributes": [23]   # Nie powinno być nieodpinane
        },
        {
            "name": "Tylko nieodpinane ramiączka", 
            "description": "Biustonosz z nieodpinane ramiączka, stałe ramiączka",
            "expected_attributes": [23],  # Tylko nieodpinane ramiączka
            "excluded_attributes": [12]   # Nie powinno być odpinane
        },
        {
            "name": "Oba atrybuty w opisie - powinno wybrać nieodpinane",
            "description": "Biustonosz z odpinane ramiączka i nieodpinane ramiączka",
            "expected_attributes": [23],  # Powinno wybrać nieodpinane (bardziej specyficzne)
            "excluded_attributes": [12]   # Powinno usunąć odpinane
        },
        {
            "name": "Regulowane ramiączka + nieodpinane",
            "description": "Biustonosz z regulowane ramiączka, nieodpinane ramiączka",
            "expected_attributes": [15, 23],  # Regulowane + nieodpinane ramiączka
            "excluded_attributes": [12]       # Nie powinno być odpinane
        }
    ]
    
    print("🧪 Testowanie poprawionej logiki wykluczania atrybutów ramiączek")
    print("=" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        print(f"📝 Opis: {test_case['description']}")
        
        # Wywołaj funkcję wykrywania atrybutów
        detected_attributes = editor.extract_mpd_attributes_from_description(test_case['description'])
        
        print(f"🔍 Wykryte atrybuty: {detected_attributes}")
        
        # Sprawdź czy oczekiwane atrybuty są obecne
        missing_expected = set(test_case['expected_attributes']) - set(detected_attributes)
        if missing_expected:
            print(f"❌ Brakuje oczekiwanych atrybutów: {missing_expected}")
        else:
            print(f"✅ Wszystkie oczekiwane atrybuty obecne")
        
        # Sprawdź czy wykluczone atrybuty nie są obecne
        found_excluded = set(test_case['excluded_attributes']) & set(detected_attributes)
        if found_excluded:
            print(f"❌ Znaleziono wykluczone atrybuty: {found_excluded}")
        else:
            print(f"✅ Wszystkie wykluczone atrybuty nieobecne")
        
        # Sprawdź czy nie ma jednocześnie odpinane i nieodpinane
        has_conflict = 12 in detected_attributes and 23 in detected_attributes
        if has_conflict:
            print(f"🚨 BŁĄD: Jednocześnie obecne odpinane (ID 12) i nieodpinane (ID 23) ramiączka!")
        else:
            print(f"✅ Brak konfliktu między odpinane i nieodpinane ramiączka")
        
        print("-" * 50)
    
    print("\n🎯 Test zakończony!")

if __name__ == "__main__":
    test_attributes_exclusion()
