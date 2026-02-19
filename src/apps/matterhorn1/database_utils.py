"""
Utility functions dla bezpiecznych operacji między bazami danych

Ten moduł zawiera gotowe funkcje do najczęstszych operacji między bazami
matterhorn1 i MPD z automatycznym logowaniem i obsługą błędów.
"""
import logging
from typing import Dict, List, Any, Optional
from django.db import connections
from .transaction_logger import logged_transaction


logger = logging.getLogger(__name__)


class DatabaseUtils:
    """
    Utility class dla operacji między bazami danych
    """

    @staticmethod
    def get_or_create_color(color_name: str, parent_color_id: int = None) -> Optional[int]:
        """
        Pobierz lub utwórz kolor w MPD

        Args:
            color_name: Nazwa koloru
            parent_color_id: ID koloru nadrzędnego (dla kolorów producenta)

        Returns:
            ID koloru lub None jeśli nie udało się utworzyć
        """
        with logged_transaction("get_or_create_color", "db_utils.colors") as tx_logger:
            try:
                with connections['MPD'].cursor() as cursor:
                    # Sprawdź czy kolor już istnieje
                    if parent_color_id:
                        tx_logger.log_operation("SELECT", "MPD", "colors", "check_producer_color",
                                                {"color_name": color_name, "parent_id": parent_color_id})
                        cursor.execute(
                            "SELECT id FROM colors WHERE name = %s AND parent_id = %s",
                            [color_name, parent_color_id]
                        )
                    else:
                        tx_logger.log_operation("SELECT", "MPD", "colors", "check_main_color",
                                                {"color_name": color_name})
                        cursor.execute(
                            "SELECT id FROM colors WHERE name = %s AND parent_id IS NULL",
                            [color_name]
                        )

                    result = cursor.fetchone()
                    if result:
                        color_id = result[0]
                        tx_logger.log_operation("SELECT", "MPD", "colors", "color_found",
                                                {"color_id": color_id, "color_name": color_name})
                        return color_id

                    # Utwórz nowy kolor
                    tx_logger.log_operation("INSERT", "MPD", "colors", "create_color",
                                            {"color_name": color_name, "parent_id": parent_color_id})
                    cursor.execute(
                        "INSERT INTO colors (name, parent_id) VALUES (%s, %s) RETURNING id",
                        [color_name, parent_color_id]
                    )

                    result = cursor.fetchone()
                    if result:
                        color_id = result[0]
                        tx_logger.log_operation("INSERT", "MPD", "colors", "color_created",
                                                {"color_id": color_id, "color_name": color_name})
                        return color_id

            except Exception as e:
                tx_logger.log_operation("INSERT", "MPD", "colors", "create_color_failed",
                                        {"color_name": color_name}, success=False, error=str(e))
                logger.error(
                    f"Błąd podczas tworzenia koloru {color_name}: {e}")

        return None

    @staticmethod
    def get_or_create_size(size_name: str, category: str = None) -> Optional[int]:
        """
        Pobierz lub utwórz rozmiar w MPD

        Args:
            size_name: Nazwa rozmiaru
            category: Kategoria rozmiaru

        Returns:
            ID rozmiaru lub None jeśli nie udało się utworzyć
        """
        with logged_transaction("get_or_create_size", "db_utils.sizes") as tx_logger:
            try:
                with connections['MPD'].cursor() as cursor:
                    # Sprawdź czy rozmiar już istnieje
                    tx_logger.log_operation("SELECT", "MPD", "sizes", "check_size",
                                            {"size_name": size_name, "category": category})
                    cursor.execute(
                        "SELECT id FROM sizes WHERE UPPER(name) = UPPER(%s)",
                        [size_name]
                    )

                    result = cursor.fetchone()
                    if result:
                        size_id = result[0]
                        tx_logger.log_operation("SELECT", "MPD", "sizes", "size_found",
                                                {"size_id": size_id, "size_name": size_name})
                        return size_id

                    # Utwórz nowy rozmiar
                    tx_logger.log_operation("INSERT", "MPD", "sizes", "create_size",
                                            {"size_name": size_name, "category": category})
                    cursor.execute("""
                        INSERT INTO sizes (name, category, name_lower)
                        VALUES (%s, %s, LOWER(%s)) RETURNING id
                    """, [size_name, category, size_name])

                    result = cursor.fetchone()
                    if result:
                        size_id = result[0]
                        tx_logger.log_operation("INSERT", "MPD", "sizes", "size_created",
                                                {"size_id": size_id, "size_name": size_name})
                        return size_id

            except Exception as e:
                tx_logger.log_operation("INSERT", "MPD", "sizes", "create_size_failed",
                                        {"size_name": size_name}, success=False, error=str(e))
                logger.error(
                    f"Błąd podczas tworzenia rozmiaru {size_name}: {e}")

        return None

    @staticmethod
    def get_product_data(product_id: int) -> Optional[Dict[str, Any]]:
        """
        Pobierz dane produktu z matterhorn1

        Args:
            product_id: ID produktu w matterhorn1

        Returns:
            Słownik z danymi produktu lub None
        """
        with logged_transaction("get_product_data", "db_utils.products") as tx_logger:
            try:
                with connections['matterhorn1'].cursor() as cursor:
                    tx_logger.log_operation("SELECT", "matterhorn1", "product", "get_product",
                                            {"product_id": product_id})
                    cursor.execute("""
                        SELECT name, color, prices, description, short_description
                        FROM product WHERE id = %s
                    """, [product_id])

                    result = cursor.fetchone()
                    if result:
                        product_data = {
                            'name': result[0],
                            'color': result[1],
                            'prices': result[2],
                            'description': result[3],
                            'short_description': result[4]
                        }
                        tx_logger.log_operation("SELECT", "matterhorn1", "product", "product_found",
                                                {"product_id": product_id, "name": product_data['name']})
                        return product_data
                    else:
                        tx_logger.log_operation("SELECT", "matterhorn1", "product", "product_not_found",
                                                {"product_id": product_id}, success=False, error="Product not found")

            except Exception as e:
                tx_logger.log_operation("SELECT", "matterhorn1", "product", "get_product_failed",
                                        {"product_id": product_id}, success=False, error=str(e))
                logger.error(
                    f"Błąd podczas pobierania produktu {product_id}: {e}")

        return None

    @staticmethod
    def get_product_variants(product_id: int) -> List[Dict[str, Any]]:
        """
        Pobierz warianty produktu z matterhorn1

        Args:
            product_id: ID produktu w matterhorn1

        Returns:
            Lista wariantów produktu
        """
        with logged_transaction("get_product_variants", "db_utils.variants") as tx_logger:
            variants = []
            try:
                with connections['matterhorn1'].cursor() as cursor:
                    tx_logger.log_operation("SELECT", "matterhorn1", "productvariant", "get_variants",
                                            {"product_id": product_id})
                    cursor.execute("""
                        SELECT name, stock, ean, variant_uid
                        FROM productvariant WHERE product_id = %s
                    """, [product_id])

                    results = cursor.fetchall()
                    for result in results:
                        variant = {
                            'name': result[0],
                            'stock': result[1],
                            'ean': result[2],
                            'variant_uid': result[3]
                        }
                        variants.append(variant)

                    tx_logger.log_operation("SELECT", "matterhorn1", "productvariant", "variants_found",
                                            {"product_id": product_id, "count": len(variants)})

            except Exception as e:
                tx_logger.log_operation("SELECT", "matterhorn1", "productvariant", "get_variants_failed",
                                        {"product_id": product_id}, success=False, error=str(e))
                logger.error(
                    f"Błąd podczas pobierania wariantów produktu {product_id}: {e}")

        return variants

    @staticmethod
    def create_mpd_product(product_data: Dict[str, Any]) -> Optional[int]:
        """
        Utwórz produkt w MPD

        Args:
            product_data: Dane produktu

        Returns:
            ID utworzonego produktu lub None
        """
        with logged_transaction("create_mpd_product", "db_utils.products") as tx_logger:
            try:
                with connections['MPD'].cursor() as cursor:
                    tx_logger.log_operation(
                        "INSERT", "MPD", "products", "create_product", product_data)
                    cursor.execute("""
                        INSERT INTO products (name, description, short_description, brand_id, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, NOW(), NOW()) RETURNING id
                    """, [
                        product_data.get('name'),
                        product_data.get('description'),
                        product_data.get('short_description'),
                        product_data.get('brand_id')
                    ])

                    result = cursor.fetchone()
                    if result:
                        product_id = result[0]
                        tx_logger.log_operation("INSERT", "MPD", "products", "product_created",
                                                {"product_id": product_id, "name": product_data.get('name')})
                        return product_id

            except Exception as e:
                tx_logger.log_operation("INSERT", "MPD", "products", "create_product_failed",
                                        product_data, success=False, error=str(e))
                logger.error(f"Błąd podczas tworzenia produktu w MPD: {e}")

        return None

    @staticmethod
    def create_mpd_variant(variant_data: Dict[str, Any]) -> Optional[int]:
        """
        Utwórz wariant produktu w MPD

        Args:
            variant_data: Dane wariantu

        Returns:
            ID utworzonego wariantu lub None
        """
        with logged_transaction("create_mpd_variant", "db_utils.variants") as tx_logger:
            try:
                with connections['MPD'].cursor() as cursor:
                    tx_logger.log_operation(
                        "INSERT", "MPD", "product_variants", "create_variant", variant_data)

                    # Pobierz następny variant_id
                    cursor.execute(
                        "SELECT COALESCE(MAX(variant_id), 0) + 1 FROM product_variants")
                    variant_id_result = cursor.fetchone()
                    variant_id = variant_id_result[0] if variant_id_result else 1

                    cursor.execute("""
                        INSERT INTO product_variants (
                            variant_id, product_id, color_id, size_id,
                            iai_product_id, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, NOW())
                    """, [
                        variant_id,
                        variant_data.get('product_id'),
                        variant_data.get('color_id'),
                        variant_data.get('size_id'),
                        variant_data.get('iai_product_id')
                    ])

                    tx_logger.log_operation("INSERT", "MPD", "product_variants", "variant_created",
                                            {"variant_id": variant_id, "product_id": variant_data.get('product_id')})
                    return variant_id

            except Exception as e:
                tx_logger.log_operation("INSERT", "MPD", "product_variants", "create_variant_failed",
                                        variant_data, success=False, error=str(e))
                logger.error(f"Błąd podczas tworzenia wariantu w MPD: {e}")

        return None

    @staticmethod
    def update_product_mapping(product_id: int, mapped_product_uid: int) -> bool:
        """
        Zaktualizuj mapowanie produktu w matterhorn1

        Args:
            product_id: ID produktu w matterhorn1
            mapped_product_uid: UID produktu w MPD

        Returns:
            True jeśli operacja się powiodła
        """
        with logged_transaction("update_product_mapping", "db_utils.mapping") as tx_logger:
            try:
                with connections['matterhorn1'].cursor() as cursor:
                    tx_logger.log_operation("UPDATE", "matterhorn1", "product", "update_mapping",
                                            {"product_id": product_id, "mapped_product_uid": mapped_product_uid})
                    cursor.execute(
                        "UPDATE product SET mapped_product_uid = %s WHERE id = %s",
                        [mapped_product_uid, product_id]
                    )

                    tx_logger.log_operation("UPDATE", "matterhorn1", "product", "mapping_updated",
                                            {"product_id": product_id, "mapped_product_uid": mapped_product_uid,
                                             "rows_affected": cursor.rowcount})
                    return cursor.rowcount > 0

            except Exception as e:
                tx_logger.log_operation("UPDATE", "matterhorn1", "product", "update_mapping_failed",
                                        {"product_id": product_id,
                                            "mapped_product_uid": mapped_product_uid},
                                        success=False, error=str(e))
                logger.error(
                    f"Błąd podczas aktualizacji mapowania produktu {product_id}: {e}")

        return False

    @staticmethod
    def add_product_attribute(product_id: int, attribute_id: int) -> bool:
        """
        Dodaj atrybut do produktu w MPD

        Args:
            product_id: ID produktu w MPD
            attribute_id: ID atrybutu

        Returns:
            True jeśli operacja się powiodła
        """
        with logged_transaction("add_product_attribute", "db_utils.attributes") as tx_logger:
            try:
                with connections['MPD'].cursor() as cursor:
                    tx_logger.log_operation("INSERT", "MPD", "product_attributes", "add_attribute",
                                            {"product_id": product_id, "attribute_id": attribute_id})
                    cursor.execute(
                        "INSERT INTO product_attributes (product_id, attribute_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [product_id, attribute_id]
                    )

                    tx_logger.log_operation("INSERT", "MPD", "product_attributes", "attribute_added",
                                            {"product_id": product_id, "attribute_id": attribute_id,
                                             "rows_affected": cursor.rowcount})
                    return True

            except Exception as e:
                tx_logger.log_operation("INSERT", "MPD", "product_attributes", "add_attribute_failed",
                                        {"product_id": product_id,
                                            "attribute_id": attribute_id},
                                        success=False, error=str(e))
                logger.error(
                    f"Błąd podczas dodawania atrybutu {attribute_id} do produktu {product_id}: {e}")

        return False

    @staticmethod
    def add_product_path(product_id: int, path_id: int) -> bool:
        """
        Dodaj ścieżkę do produktu w MPD

        Args:
            product_id: ID produktu w MPD
            path_id: ID ścieżki

        Returns:
            True jeśli operacja się powiodła
        """
        with logged_transaction("add_product_path", "db_utils.paths") as tx_logger:
            try:
                with connections['MPD'].cursor() as cursor:
                    tx_logger.log_operation("INSERT", "MPD", "product_path", "add_path",
                                            {"product_id": product_id, "path_id": path_id})
                    cursor.execute(
                        "INSERT INTO product_path (product_id, path_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [product_id, path_id]
                    )

                    tx_logger.log_operation("INSERT", "MPD", "product_path", "path_added",
                                            {"product_id": product_id, "path_id": path_id,
                                             "rows_affected": cursor.rowcount})
                    return True

            except Exception as e:
                tx_logger.log_operation("INSERT", "MPD", "product_path", "add_path_failed",
                                        {"product_id": product_id,
                                            "path_id": path_id},
                                        success=False, error=str(e))
                logger.error(
                    f"Błąd podczas dodawania ścieżki {path_id} do produktu {product_id}: {e}")

        return False


class SafeCrossDatabaseOperations:
    """
    Klasa z bezpiecznymi operacjami między bazami danych
    """

    @staticmethod
    def create_product_with_mapping(matterhorn_product_id: int, mpd_product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bezpieczne utworzenie produktu w MPD z mapowaniem w matterhorn1

        Args:
            matterhorn_product_id: ID produktu w matterhorn1
            mpd_product_data: Dane produktu do utworzenia w MPD

        Returns:
            Słownik z wynikiem operacji
        """
        with logged_transaction("create_product_with_mapping", "safe_operations") as tx_logger:
            tx_logger.log_cross_database_operation(
                "matterhorn1", "MPD",
                "create_product_with_mapping",
                {"matterhorn_product_id": matterhorn_product_id}
            )

            try:
                # 1. Pobierz dane produktu z matterhorn1
                product_data = DatabaseUtils.get_product_data(
                    matterhorn_product_id)
                if not product_data:
                    return {"success": False, "error": "Product not found in matterhorn1"}

                # 2. Utwórz produkt w MPD
                mpd_product_id = DatabaseUtils.create_mpd_product(
                    mpd_product_data)
                if not mpd_product_id:
                    return {"success": False, "error": "Failed to create product in MPD"}

                # 3. Zaktualizuj mapowanie w matterhorn1
                mapping_success = DatabaseUtils.update_product_mapping(
                    matterhorn_product_id, mpd_product_id)
                if not mapping_success:
                    # TODO: Kompensacja - usunąć produkt z MPD
                    return {"success": False, "error": "Failed to update mapping in matterhorn1"}

                tx_logger.log_cross_database_operation(
                    "matterhorn1", "MPD",
                    "create_product_with_mapping",
                    {
                        "matterhorn_product_id": matterhorn_product_id,
                        "mpd_product_id": mpd_product_id,
                        "status": "completed"
                    }
                )

                return {
                    "success": True,
                    "mpd_product_id": mpd_product_id,
                    "message": "Product created and mapped successfully"
                }

            except Exception as e:
                tx_logger.log_cross_database_operation(
                    "matterhorn1", "MPD",
                    "create_product_with_mapping",
                    {"matterhorn_product_id": matterhorn_product_id},
                    success=False,
                    error=str(e)
                )
                return {"success": False, "error": str(e)}

    @staticmethod
    def create_variants_with_mapping(matterhorn_product_id: int, mpd_product_id: int,
                                     size_category: str, producer_color_id: int = None) -> Dict[str, Any]:
        """
        Bezpieczne utworzenie wariantów w MPD z mapowaniem w matterhorn1

        Args:
            matterhorn_product_id: ID produktu w matterhorn1
            mpd_product_id: ID produktu w MPD
            size_category: Kategoria rozmiarów
            producer_color_id: ID koloru producenta

        Returns:
            Słownik z wynikiem operacji
        """
        with logged_transaction("create_variants_with_mapping", "safe_operations") as tx_logger:
            tx_logger.log_cross_database_operation(
                "matterhorn1", "MPD",
                "create_variants_with_mapping",
                {
                    "matterhorn_product_id": matterhorn_product_id,
                    "mpd_product_id": mpd_product_id,
                    "size_category": size_category
                }
            )

            try:
                # 1. Pobierz dane produktu
                product_data = DatabaseUtils.get_product_data(
                    matterhorn_product_id)
                if not product_data:
                    return {"success": False, "error": "Product not found in matterhorn1"}

                # 2. Pobierz warianty
                variants = DatabaseUtils.get_product_variants(
                    matterhorn_product_id)
                if not variants:
                    return {"success": False, "error": "No variants found in matterhorn1"}

                # 3. Pobierz kolor w MPD
                color_id = DatabaseUtils.get_or_create_color(
                    product_data['color'])
                if not color_id:
                    return {"success": False, "error": f"Color {product_data['color']} not found in MPD"}

                created_variants = []
                failed_variants = []

                # 4. Utwórz warianty w MPD
                for variant in variants:
                    size_id = DatabaseUtils.get_or_create_size(
                        variant['name'], size_category)
                    if not size_id:
                        failed_variants.append(variant['name'])
                        continue

                    variant_data = {
                        'product_id': mpd_product_id,
                        'color_id': color_id,
                        'size_id': size_id,
                        'producer_code': variant.get('ean'),
                        'iai_product_id': 1  # TODO: Implement proper counter
                    }

                    variant_id = DatabaseUtils.create_mpd_variant(variant_data)
                    if variant_id:
                        created_variants.append(variant_id)

                tx_logger.log_cross_database_operation(
                    "matterhorn1", "MPD",
                    "create_variants_with_mapping",
                    {
                        "matterhorn_product_id": matterhorn_product_id,
                        "mpd_product_id": mpd_product_id,
                        "created_variants": len(created_variants),
                        "failed_variants": len(failed_variants),
                        "status": "completed"
                    }
                )

                return {
                    "success": True,
                    "created_variants": len(created_variants),
                    "failed_variants": failed_variants,
                    "message": f"Created {len(created_variants)} variants successfully"
                }

            except Exception as e:
                tx_logger.log_cross_database_operation(
                    "matterhorn1", "MPD",
                    "create_variants_with_mapping",
                    {
                        "matterhorn_product_id": matterhorn_product_id,
                        "mpd_product_id": mpd_product_id
                    },
                    success=False,
                    error=str(e)
                )
                return {"success": False, "error": str(e)}
