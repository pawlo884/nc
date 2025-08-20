#!/usr/bin/env python3
"""
Narzędzie do zarządzania listą pomijanych produktów

Użycie:
    python manage_skip_list.py status                    # Pokaż status listy
    python manage_skip_list.py add 214962               # Dodaj jeden ID
    python manage_skip_list.py add 214962,215001,215123 # Dodaj wiele ID
    python manage_skip_list.py remove 214962            # Usuń ID z listy
    python manage_skip_list.py clear                    # Wyczyść całą listę
    python manage_skip_list.py check 214962             # Sprawdź czy ID jest na liście
"""

import sys
import re
from matterhorn.Lupo_line.skip_products_list import SKIP_PRODUCT_IDS, should_skip_product, get_skip_list_info, print_skip_list_status


def add_products(ids_input):
    """Dodaje produkty do listy pomijanych"""
    # Parsuj input - może być pojedyncze ID lub lista rozdzielona przecinkami
    if ',' in ids_input:
        id_strings = [id_str.strip() for id_str in ids_input.split(',')]
    else:
        id_strings = [ids_input.strip()]

    added_count = 0
    errors = []

    for id_str in id_strings:
        try:
            product_id = int(id_str)
            if product_id not in SKIP_PRODUCT_IDS:
                SKIP_PRODUCT_IDS.append(product_id)
                print(f"✅ Dodano ID {product_id} do listy pomijanych")
                added_count += 1
            else:
                print(f"⚠️ ID {product_id} już jest na liście pomijanych")
        except ValueError:
            errors.append(id_str)

    if errors:
        print(f"❌ Nieprawidłowe ID: {', '.join(errors)}")

    if added_count > 0:
        print(f"\n🎯 Dodano {added_count} produktów do listy")
        print("💡 UWAGA: Zmiany są tylko w pamięci. Aby je zapisać, edytuj plik matterhorn/Lupo_line/skip_products_list.py")
        print_current_list()

    return added_count > 0


def remove_products(ids_input):
    """Usuwa produkty z listy pomijanych"""
    if ',' in ids_input:
        id_strings = [id_str.strip() for id_str in ids_input.split(',')]
    else:
        id_strings = [ids_input.strip()]

    removed_count = 0
    errors = []

    for id_str in id_strings:
        try:
            product_id = int(id_str)
            if product_id in SKIP_PRODUCT_IDS:
                SKIP_PRODUCT_IDS.remove(product_id)
                print(f"✅ Usunięto ID {product_id} z listy pomijanych")
                removed_count += 1
            else:
                print(f"⚠️ ID {product_id} nie było na liście pomijanych")
        except ValueError:
            errors.append(id_str)

    if errors:
        print(f"❌ Nieprawidłowe ID: {', '.join(errors)}")

    if removed_count > 0:
        print(f"\n🎯 Usunięto {removed_count} produktów z listy")
        print("💡 UWAGA: Zmiany są tylko w pamięci. Aby je zapisać, edytuj plik matterhorn/Lupo_line/skip_products_list.py")
        print_current_list()

    return removed_count > 0


def clear_list():
    """Czyści całą listę pomijanych produktów"""
    original_count = len(SKIP_PRODUCT_IDS)
    SKIP_PRODUCT_IDS.clear()
    print(
        f"🧹 Wyczyszczono listę pomijanych produktów ({original_count} produktów)")
    print("💡 UWAGA: Zmiany są tylko w pamięci. Aby je zapisać, edytuj plik matterhorn/Lupo_line/skip_products_list.py")
    print_current_list()
    return True


def check_product(product_id_str):
    """Sprawdza czy produkt jest na liście pomijanych"""
    try:
        product_id = int(product_id_str)
        is_skipped = should_skip_product(product_id)

        if is_skipped:
            print(f"✅ Produkt ID {product_id} JEST na liście pomijanych")
        else:
            print(f"❌ Produkt ID {product_id} NIE JEST na liście pomijanych")

        return is_skipped
    except ValueError:
        print(f"❌ Nieprawidłowe ID produktu: {product_id_str}")
        return False


def print_current_list():
    """Wyświetla aktualną listę w formacie do skopiowania"""
    info = get_skip_list_info()

    if info['is_empty']:
        print("\n📋 Lista pomijanych produktów:")
        print("SKIP_PRODUCT_IDS = []")
    else:
        print("\n📋 Lista pomijanych produktów do skopiowania:")
        print("SKIP_PRODUCT_IDS = [")
        for product_id in sorted(info['product_ids']):
            print(f"    {product_id},")
        print("]")


def show_help():
    """Wyświetla pomoc"""
    print("🔧 Narzędzie do zarządzania listą pomijanych produktów")
    print("\nKomendy:")
    print("  status                     - Pokaż status listy")
    print("  add <ID>                   - Dodaj jeden ID")
    print("  add <ID1>,<ID2>,<ID3>      - Dodaj wiele ID (oddzielone przecinkami)")
    print("  remove <ID>                - Usuń ID z listy")
    print("  remove <ID1>,<ID2>         - Usuń wiele ID")
    print("  clear                      - Wyczyść całą listę")
    print("  check <ID>                 - Sprawdź czy ID jest na liście")
    print("  help                       - Pokaż tę pomoc")
    print("\nPrzykłady:")
    print("  python manage_skip_list.py add 214962")
    print("  python manage_skip_list.py add 214962,215001,215123")
    print("  python manage_skip_list.py remove 214962")
    print("  python manage_skip_list.py check 214962")


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == 'status':
        print_skip_list_status()
        print_current_list()

    elif command == 'add':
        if len(sys.argv) < 3:
            print("❌ Brak ID produktów do dodania")
            print("Użycie: python manage_skip_list.py add <ID1>,<ID2>,...")
            return
        add_products(sys.argv[2])

    elif command == 'remove':
        if len(sys.argv) < 3:
            print("❌ Brak ID produktów do usunięcia")
            print("Użycie: python manage_skip_list.py remove <ID1>,<ID2>,...")
            return
        remove_products(sys.argv[2])

    elif command == 'clear':
        confirm = input(
            "⚠️ Czy na pewno chcesz wyczyścić całą listę? (tak/nie): ")
        if confirm.lower() in ['tak', 'yes', 'y', 't']:
            clear_list()
        else:
            print("❌ Anulowano")

    elif command == 'check':
        if len(sys.argv) < 3:
            print("❌ Brak ID produktu do sprawdzenia")
            print("Użycie: python manage_skip_list.py check <ID>")
            return
        check_product(sys.argv[2])

    elif command == 'help':
        show_help()

    else:
        print(f"❌ Nieznana komenda: {command}")
        show_help()


if __name__ == "__main__":
    main()
