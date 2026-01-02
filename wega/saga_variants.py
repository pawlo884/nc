"""
Funkcje pomocnicze dla tworzenia wariantów w Sadze - WEGA
"""
import logging
from typing import Dict, List
from django.db import connections

logger = logging.getLogger(__name__)


def create_mpd_variants(mpd_product_id: int, wega_product_id: int, size_category: str,
                        producer_code: str = None, main_color_id: int = None,
                        producer_color_name: str = None) -> Dict:
    """Utwórz warianty w MPD razem z produktem z wega"""
    logger.info(
        f"🔄 Tworzę warianty w MPD dla produktu {mpd_product_id}, kategoria: {size_category}")
    logger.info(
        f"📋 Parametry: producer_code='{producer_code}', main_color_id={main_color_id}, producer_color_name='{producer_color_name}'")

    try:
        with connections['MPD'].cursor() as mpd_cursor, connections['wega'].cursor() as wega_cursor:
            # Pobierz cenę produktu z wega
            wega_cursor.execute("""
                SELECT price, gross_price FROM wega_product WHERE id = %s
            """, [wega_product_id])
            price_result = wega_cursor.fetchone()
            if not price_result:
                raise Exception(
                    f"Product {wega_product_id} not found in wega")

            product_price, product_gross_price = price_result
            # Użyj ceny netto jako podstawowej
            product_price = float(product_price) if product_price else 0

            logger.info(f"Produkt: cena={product_price}")

            # Pobierz ID koloru w MPD (jeśli produkt ma kolor w atrybutach)
            color_id = None
            if main_color_id:
                color_id = main_color_id
            else:
                # Spróbuj znaleźć kolor z pierwszego atrybutu
                wega_cursor.execute("""
                    SELECT color FROM wega_productattribute WHERE product_id = %s AND color IS NOT NULL LIMIT 1
                """, [wega_product_id])
                color_result = wega_cursor.fetchone()
                if color_result and color_result[0]:
                    mpd_cursor.execute(
                        "SELECT id FROM colors WHERE name = %s", [color_result[0]])
                    color_row = mpd_cursor.fetchone()
                    if color_row:
                        color_id = color_row[0]

            if not color_id:
                logger.warning("Brak koloru dla produktu - używam None")
                color_id = None

            # Pobierz lub utwórz producer_color_id
            producer_color_id = None
            logger.info(
                f"🔍 Sprawdzam producer_color_name='{producer_color_name}', main_color_id={main_color_id}")
            if producer_color_name and main_color_id:
                mpd_cursor.execute("SELECT id FROM colors WHERE name = %s AND parent_id = %s",
                                   [producer_color_name, main_color_id])
                pc_row = mpd_cursor.fetchone()
                if pc_row:
                    producer_color_id = pc_row[0]
                    logger.info(
                        f"✅ Znaleziono istniejący kolor producenta: {producer_color_name} (ID: {producer_color_id})")
                else:
                    mpd_cursor.execute("INSERT INTO colors (name, parent_id) VALUES (%s, %s) RETURNING id",
                                       [producer_color_name, main_color_id])
                    row = mpd_cursor.fetchone()
                    if row:
                        producer_color_id = row[0]
                        logger.info(
                            f"✅ Utworzono kolor producenta: {producer_color_name} (ID: {producer_color_id})")
            else:
                logger.warning(
                    f"⚠️ Brak producer_color_name lub main_color_id - producer_color_id będzie None")

            # Generuj iai_product_id
            mpd_cursor.execute("""
                INSERT INTO iai_product_counter (counter_value) 
                VALUES (1) 
                ON CONFLICT (id) 
                DO UPDATE SET counter_value = iai_product_counter.counter_value + 1 
                RETURNING counter_value
            """)
            iai_product_id_result = mpd_cursor.fetchone()
            iai_product_id = iai_product_id_result[0] if iai_product_id_result else 1
            logger.info(f"Wygenerowano iai_product_id: {iai_product_id}")

            # Pobierz atrybuty (warianty) z wega
            wega_cursor.execute("""
                SELECT size, available, ean, id FROM wega_productattribute WHERE product_id = %s
            """, [wega_product_id])
            attributes = wega_cursor.fetchall()

            if not attributes:
                logger.warning(
                    f"Brak atrybutów dla produktu {wega_product_id}")
                return {"created_variants": 0, "iai_product_id": iai_product_id}

            created_count = 0
            variant_ids = []

            for size_name, stock, ean, attribute_id in attributes:
                if not size_name:
                    logger.warning(f"Atrybut {attribute_id} nie ma rozmiaru - pomijam")
                    continue

                # Pobierz ID rozmiaru z wybranej kategorii
                mpd_cursor.execute("SELECT id FROM sizes WHERE UPPER(name) = UPPER(%s) AND category = %s",
                                   [size_name, size_category])
                size_result = mpd_cursor.fetchone()
                if not size_result:
                    logger.warning(
                        f"Rozmiar {size_name} nie znaleziony w kategorii {size_category}")
                    continue
                size_id = size_result[0]

                # Sprawdź czy wariant już istnieje (używamy attribute_id jako variant_uid)
                variant_uid = f"wega_{attribute_id}"
                mpd_cursor.execute("""
                    SELECT variant_id FROM product_variants_sources 
                    WHERE variant_uid = %s AND source_id = %s
                """, [variant_uid, 2])
                existing = mpd_cursor.fetchone()
                if existing:
                    logger.info(
                        f"Wariant {variant_uid} już istnieje - pomijam")
                    continue

                # Wygeneruj nowy variant_id
                mpd_cursor.execute(
                    "SELECT COALESCE(MAX(variant_id), 0) + 1 FROM product_variants")
                row = mpd_cursor.fetchone()
                variant_id = row[0] if row else 1

                # Utwórz wariant
                logger.info(
                    f"🔧 Tworzę wariant {variant_id}: producer_color_id={producer_color_id}, producer_code='{producer_code}'")
                if producer_color_id and color_id:
                    mpd_cursor.execute("""
                        INSERT INTO product_variants 
                        (variant_id, product_id, color_id, producer_color_id, size_id, producer_code, iai_product_id, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """, [variant_id, mpd_product_id, color_id, producer_color_id, size_id, producer_code, iai_product_id])
                    logger.info(
                        f"✅ Utworzono wariant z producer_color_id={producer_color_id}")
                elif color_id:
                    mpd_cursor.execute("""
                        INSERT INTO product_variants 
                        (variant_id, product_id, color_id, size_id, producer_code, iai_product_id, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, [variant_id, mpd_product_id, color_id, size_id, producer_code, iai_product_id])
                    logger.info(f"✅ Utworzono wariant z color_id={color_id}")
                else:
                    mpd_cursor.execute("""
                        INSERT INTO product_variants 
                        (variant_id, product_id, size_id, producer_code, iai_product_id, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, [variant_id, mpd_product_id, size_id, producer_code, iai_product_id])
                    logger.info(f"⚠️ Utworzono wariant BEZ color_id")

                # Dodaj do product_variants_sources
                mpd_cursor.execute("""
                    INSERT INTO product_variants_sources (variant_id, ean, variant_uid, source_id)
                    VALUES (%s, %s, %s, %s)
                """, [variant_id, ean, variant_uid, 2])

                # Dodaj stock_and_prices
                mpd_cursor.execute("""
                    INSERT INTO stock_and_prices (variant_id, source_id, stock, price, currency)
                    VALUES (%s, %s, %s, %s, 'PLN')
                """, [variant_id, 2, stock or 0, product_price])

                # Zaktualizuj mapped_variant_uid w wega
                wega_cursor.execute("""
                    UPDATE wega_productattribute 
                    SET mapped_variant_uid = %s, is_mapped = true, updated_at = NOW() 
                    WHERE id = %s
                """, [variant_id, attribute_id])

                variant_ids.append(variant_id)
                created_count += 1
                logger.info(f"Utworzono wariant {variant_uid} -> {variant_id}")

            logger.info(f"✅ Utworzono {created_count} wariantów w MPD")
            return {
                "created_variants": created_count,
                "iai_product_id": iai_product_id,
                "variant_ids": variant_ids
            }

    except Exception as e:
        raise Exception(f"Failed to create MPD variants: {e}")


def delete_mpd_variants(mpd_product_id: int, wega_product_id: int = None,
                        variant_ids: List[int] = None, **kwargs) -> Dict:
    """Usuń warianty z MPD (kompensacja)"""
    logger.info(f"🔄 Usuwam warianty z MPD dla produktu {mpd_product_id}")

    try:
        with connections['MPD'].cursor() as mpd_cursor:
            if variant_ids:
                # Usuń konkretne warianty
                for variant_id in variant_ids:
                    mpd_cursor.execute(
                        "DELETE FROM stock_and_prices WHERE variant_id = %s", [variant_id])
                    mpd_cursor.execute(
                        "DELETE FROM product_variants_sources WHERE variant_id = %s", [variant_id])
                    mpd_cursor.execute(
                        "DELETE FROM product_variants WHERE variant_id = %s", [variant_id])
                logger.info(f"✅ Usunięto {len(variant_ids)} wariantów")
            else:
                # Usuń wszystkie warianty produktu
                mpd_cursor.execute(
                    "SELECT variant_id FROM product_variants WHERE product_id = %s", [mpd_product_id])
                variant_ids = [row[0] for row in mpd_cursor.fetchall()]

                for variant_id in variant_ids:
                    mpd_cursor.execute(
                        "DELETE FROM stock_and_prices WHERE variant_id = %s", [variant_id])
                    mpd_cursor.execute(
                        "DELETE FROM product_variants_sources WHERE variant_id = %s", [variant_id])
                    mpd_cursor.execute(
                        "DELETE FROM product_variants WHERE variant_id = %s", [variant_id])
                logger.info(
                    f"✅ Usunięto wszystkie warianty produktu {mpd_product_id}")

        # Cofnij mapping w wega
        if wega_product_id:
            with connections['wega'].cursor() as wega_cursor:
                wega_cursor.execute("""
                    UPDATE wega_productattribute 
                    SET mapped_variant_uid = NULL, is_mapped = false, updated_at = NOW() 
                    WHERE product_id = %s
                """, [wega_product_id])

    except Exception as e:
        logger.error(f"❌ Błąd podczas usuwania wariantów: {e}")

    return {}

