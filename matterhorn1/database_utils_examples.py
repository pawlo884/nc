"""
Przykłady użycia utility functions dla operacji między bazami danych
"""
from .database_utils import DatabaseUtils, SafeCrossDatabaseOperations


def example_basic_operations():
    """
    Przykład podstawowych operacji używając DatabaseUtils
    """
    # Pobierz dane produktu z matterhorn1
    product_data = DatabaseUtils.get_product_data(123)
    if product_data:
        print(
            f"Produkt: {product_data['name']}, Kolor: {product_data['color']}")

        # Pobierz lub utwórz kolor w MPD
        color_id = DatabaseUtils.get_or_create_color(product_data['color'])
        if color_id:
            print(f"Kolor utworzony/znaleziony: ID {color_id}")

        # Pobierz lub utwórz rozmiar w MPD
        size_id = DatabaseUtils.get_or_create_size("M", "Unisex")
        if size_id:
            print(f"Rozmiar utworzony/znaleziony: ID {size_id}")

    # Pobierz warianty produktu
    variants = DatabaseUtils.get_product_variants(123)
    print(f"Znaleziono {len(variants)} wariantów")


def example_safe_operations():
    """
    Przykład bezpiecznych operacji między bazami
    """
    # Bezpieczne utworzenie produktu z mapowaniem
    mpd_product_data = {
        'name': 'Test Product',
        'description': 'Test Description',
        'short_description': 'Test Short',
        'brand_id': 1
    }

    result = SafeCrossDatabaseOperations.create_product_with_mapping(
        matterhorn_product_id=123,
        mpd_product_data=mpd_product_data
    )

    if result['success']:
        print(
            f"Produkt utworzony pomyślnie: MPD ID {result['mpd_product_id']}")

        # Utwórz warianty dla nowego produktu
        variants_result = SafeCrossDatabaseOperations.create_variants_with_mapping(
            matterhorn_product_id=123,
            mpd_product_id=result['mpd_product_id'],
            size_category='Unisex'
        )

        if variants_result['success']:
            print(f"Utworzono {variants_result['created_variants']} wariantów")
        else:
            print(f"Błąd tworzenia wariantów: {variants_result['error']}")
    else:
        print(f"Błąd tworzenia produktu: {result['error']}")


def example_admin_integration():
    """
    Przykład integracji z admin.py
    """
    # Zamiast ręcznego kodu w admin.py, użyj utility functions

    # Stary sposób (w admin.py):
    # with connections['MPD'].cursor() as cursor:
    #     cursor.execute("SELECT id FROM colors WHERE name = %s", [color_name])
    #     result = cursor.fetchone()
    #     if not result:
    #         cursor.execute("INSERT INTO colors (name) VALUES (%s) RETURNING id", [color_name])
    #         result = cursor.fetchone()
    #     color_id = result[0]

    # Nowy sposób z utility functions:
    color_id = DatabaseUtils.get_or_create_color("Red")
    if color_id:
        print(f"Kolor Red: ID {color_id}")

    # Stary sposób tworzenia produktu:
    # with connections['MPD'].cursor() as cursor:
    #     cursor.execute("INSERT INTO products (...) VALUES (...) RETURNING id", [...])
    #     result = cursor.fetchone()
    #     product_id = result[0]

    # Nowy sposób:
    product_data = {
        'name': 'New Product',
        'description': 'New Description',
        'short_description': 'New Short',
        'brand_id': 1
    }
    product_id = DatabaseUtils.create_mpd_product(product_data)
    if product_id:
        print(f"Produkt utworzony: ID {product_id}")


def example_error_handling():
    """
    Przykład obsługi błędów z utility functions
    """
    try:
        # Próba pobrania nieistniejącego produktu
        product_data = DatabaseUtils.get_product_data(99999)
        if not product_data:
            print("Produkt nie istnieje - obsługa błędu")

        # Próba utworzenia produktu z nieprawidłowymi danymi
        invalid_data = {
            'name': None,  # Nieprawidłowe dane
            'description': 'Test',
            'short_description': 'Test',
            'brand_id': None
        }

        product_id = DatabaseUtils.create_mpd_product(invalid_data)
        if not product_id:
            print("Nie udało się utworzyć produktu - obsługa błędu")

    except Exception as e:
        print(f"Nieoczekiwany błąd: {e}")


def example_complex_workflow():
    """
    Przykład złożonego przepływu pracy używając utility functions
    """
    matterhorn_product_id = 123

    # 1. Pobierz dane produktu
    product_data = DatabaseUtils.get_product_data(matterhorn_product_id)
    if not product_data:
        return {"error": "Product not found"}

    # 2. Utwórz produkt w MPD
    mpd_product_data = {
        'name': product_data['name'],
        'description': product_data['description'],
        'short_description': product_data['short_description'],
        'brand_id': 1  # TODO: Mapowanie marki
    }

    mpd_product_id = DatabaseUtils.create_mpd_product(mpd_product_data)
    if not mpd_product_id:
        return {"error": "Failed to create product in MPD"}

    # 3. Zaktualizuj mapowanie
    mapping_success = DatabaseUtils.update_product_mapping(
        matterhorn_product_id, mpd_product_id)
    if not mapping_success:
        return {"error": "Failed to update mapping"}

    # 4. Dodaj atrybuty (jeśli są)
    attribute_ids = [1, 2, 3]  # Przykładowe ID atrybutów
    for attribute_id in attribute_ids:
        DatabaseUtils.add_product_attribute(mpd_product_id, attribute_id)

    # 5. Dodaj ścieżki (jeśli są)
    path_ids = [1, 2]  # Przykładowe ID ścieżek
    for path_id in path_ids:
        DatabaseUtils.add_product_path(mpd_product_id, path_id)

    # 6. Utwórz warianty
    variants_result = SafeCrossDatabaseOperations.create_variants_with_mapping(
        matterhorn_product_id=matterhorn_product_id,
        mpd_product_id=mpd_product_id,
        size_category='Unisex'
    )

    return {
        "success": True,
        "mpd_product_id": mpd_product_id,
        "variants": variants_result
    }


if __name__ == "__main__":
    print("=== Przykłady użycia DatabaseUtils ===")
    example_basic_operations()

    print("\n=== Przykłady bezpiecznych operacji ===")
    example_safe_operations()

    print("\n=== Przykłady integracji z admin ===")
    example_admin_integration()

    print("\n=== Przykłady obsługi błędów ===")
    example_error_handling()

    print("\n=== Przykład złożonego przepływu ===")
    result = example_complex_workflow()
    print(f"Wynik: {result}")




