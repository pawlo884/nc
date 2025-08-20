#!/usr/bin/env python3
"""
Test systemu kategorii Lupo Line
"""

from category_manager import category_manager

def test_categories():
    """Test funkcjonalności kategorii"""
    print("🧪 === TEST SYSTEMU KATEGORII LUPO LINE ===\n")
    
    # Test 1: Wyświetl menu kategorii
    print("1. Menu kategorii:")
    category_manager.show_category_menu()
    
    # Test 2: Sprawdź konfiguracje kategorii
    print("\n2. Konfiguracje kategorii:")
    for key, category in category_manager.available_categories.items():
        print(f"   {key}. {category['display_name']}")
        print(f"      URL: {category['url']}")
        print()
    
    # Test 3: Sprawdź konfigurację przetwarzania
    print("3. Konfiguracje przetwarzania:")
    for category_name in ["stroj_dwuczesciowy", "stroj_jednoczesciowy"]:
        config = category_manager.get_processing_config(category_name)
        if config:
            print(f"   {category_name}: batch_size={config['batch_size']}, url={config['url'][:50]}...")
    
    print("\n✅ Test zakończony!")

if __name__ == "__main__":
    test_categories()
