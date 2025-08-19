"""
Lista ID produktów do pominięcia przez agenta MPD

Produkty na tej liście będą pomijane podczas automatycznego przetwarzania.
Dodaj tutaj ID produktów które są duplikatami lub nie powinny być przetwarzane.

Format: lista liczb (ID produktów)
"""

# Lista ID produktów do pominięcia
SKIP_PRODUCT_IDS = [
    198050,  # duplikat
    212321,  # duplikat

]


def should_skip_product(product_id):
    """
    Sprawdza czy produkt o danym ID powinien zostać pominięty

    Args:
        product_id (int lub str): ID produktu do sprawdzenia

    Returns:
        bool: True jeśli produkt powinien zostać pominięty
    """
    try:
        product_id = int(product_id)
        return product_id in SKIP_PRODUCT_IDS
    except (ValueError, TypeError):
        return False


def add_product_to_skip_list(product_id, reason=""):
    """
    Dodaje produkt do listy pomijanych (tylko w pamięci, nie zapisuje do pliku)

    Args:
        product_id (int lub str): ID produktu do dodania
        reason (str): Opcjonalny powód pomijania
    """
    try:
        product_id = int(product_id)
        if product_id not in SKIP_PRODUCT_IDS:
            SKIP_PRODUCT_IDS.append(product_id)
            print(
                f"➕ Dodano produkt {product_id} do listy pomijanych. Powód: {reason}")
            return True
    except (ValueError, TypeError):
        print(f"❌ Nieprawidłowe ID produktu: {product_id}")
    return False


def get_skip_list_info():
    """
    Zwraca informacje o liście pomijanych produktów

    Returns:
        dict: Informacje o liście
    """
    return {
        "count": len(SKIP_PRODUCT_IDS),
        "product_ids": sorted(SKIP_PRODUCT_IDS),
        "is_empty": len(SKIP_PRODUCT_IDS) == 0
    }


def print_skip_list_status():
    """Wyświetla status listy pomijanych produktów"""
    info = get_skip_list_info()

    print(f"\n📋 Status listy pomijanych produktów:")
    print(f"   Liczba produktów: {info['count']}")

    if info['is_empty']:
        print(f"   ✅ Lista jest pusta - wszystkie produkty będą przetwarzane")
    else:
        print(f"   ⚠️ Produkty do pominięcia: {info['product_ids']}")
        print(f"   💡 Aby dodać produkty, edytuj plik: web_agent/skip_products_list.py")


if __name__ == "__main__":
    print("🔧 Narzędzie do zarządzania listą pomijanych produktów")
    print_skip_list_status()

    # Przykłady użycia:
    print(f"\n🧪 Przykłady testów:")
    print(f"   should_skip_product(214962): {should_skip_product(214962)}")
    print(f"   should_skip_product('215001'): {should_skip_product('215001')}")
    print(f"   should_skip_product('abc'): {should_skip_product('abc')}")
