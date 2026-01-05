"""
Funkcje pomocnicze dla tworzenia wariantów w Sadze - WEGA
"""
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from django.db import connections

logger = logging.getLogger(__name__)


def get_source_id(source_name: str = 'wega') -> Optional[int]:
    """Pobierz source_id z bazy MPD na podstawie nazwy źródła"""
    try:
        with connections['MPD'].cursor() as cursor:
            cursor.execute("SELECT id FROM sources WHERE LOWER(name) = LOWER(%s)", [source_name])
            result = cursor.fetchone()
            if result:
                source_id = result[0]
                logger.info(f"✅ Znaleziono source_id={source_id} dla źródła '{source_name}'")
                return source_id
            else:
                logger.error(f"❌ Nie znaleziono źródła '{source_name}' w tabeli sources")
                return None
    except Exception as e:
        logger.error(f"❌ Błąd podczas pobierania source_id dla '{source_name}': {e}")
        return None


def create_mpd_variants(mpd_product_id: int, wega_product_id: int, size_category: str,
                        producer_code: str = None, main_color_id: int = None,
                        producer_color_name: str = None) -> Dict:
    """Utwórz warianty w MPD razem z produktem z wega"""
    logger.info(
        f"🔄 Tworzę warianty w MPD dla produktu {mpd_product_id}, kategoria: {size_category}")
    logger.info(
        f"📋 Parametry: producer_code='{producer_code}', main_color_id={main_color_id}, producer_color_name='{producer_color_name}'")

    # Pobierz source_id dla wega
    source_id = get_source_id('wega')
    if not source_id:
        raise Exception("Nie można pobrać source_id dla wega z bazy MPD")
    logger.info(f"📌 Używam source_id={source_id} dla wega")

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
            # Użyj ceny netto jako podstawowej, konwertuj na Decimal dla zgodności z bazą
            if product_price:
                product_price = Decimal(str(product_price))
            else:
                product_price = Decimal('0.00')

            logger.info(f"Produkt: cena={product_price}, cena_brutto={product_gross_price}")

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
                SELECT size, COALESCE(available, 0) as available, ean, id 
                FROM wega_productattribute 
                WHERE product_id = %s
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

                # Sprawdź czy wariant już istnieje dla wega
                # variant_uid w MPD jest IntegerField, więc używamy attribute_id bezpośrednio
                # Upewnij się, że attribute_id jest integerem
                try:
                    variant_uid = int(attribute_id)
                except (ValueError, TypeError):
                    logger.error(f"Nieprawidłowy attribute_id: {attribute_id} (typ: {type(attribute_id)})")
                    continue
                
                mpd_cursor.execute("""
                    SELECT variant_id FROM product_variants_sources 
                    WHERE variant_uid = %s AND source_id = %s
                """, [variant_uid, source_id])
                existing_wega = mpd_cursor.fetchone()
                
                if existing_wega:
                    # Wariant już istnieje dla wega - zaktualizuj stock_and_prices
                    variant_id = existing_wega[0]
                    logger.info(f"Wariant {variant_uid} już istnieje dla wega (variant_id={variant_id}) - aktualizuję stock_and_prices")
                    
                    # Sprawdź czy stock_and_prices już istnieje
                    mpd_cursor.execute("""
                        SELECT variant_id FROM stock_and_prices 
                        WHERE variant_id = %s AND source_id = %s
                    """, [variant_id, source_id])
                    existing_stock = mpd_cursor.fetchone()
                    
                    # Upewnij się, że stock i price są poprawnych typów
                    stock_value = int(stock) if stock is not None else 0
                    if isinstance(product_price, Decimal):
                        price_value = product_price
                    else:
                        price_value = Decimal(str(product_price)) if product_price else Decimal('0.00')
                    
                    if existing_stock:
                        # Aktualizuj istniejący stock_and_prices
                        mpd_cursor.execute("""
                            UPDATE stock_and_prices 
                            SET stock = %s, price = %s, last_updated = NOW()
                            WHERE variant_id = %s AND source_id = %s
                        """, [stock_value, price_value, variant_id, source_id])
                        logger.info(f"📦 Zaktualizowano stock_and_prices: variant_id={variant_id}, stock={stock_value}, price={price_value}")
                    else:
                        # Dodaj nowy stock_and_prices
                        mpd_cursor.execute("""
                            INSERT INTO stock_and_prices (variant_id, source_id, stock, price, currency, last_updated)
                            VALUES (%s, %s, %s, %s, 'PLN', NOW())
                        """, [variant_id, source_id, stock_value, price_value])
                        logger.info(f"📦 Dodano stock_and_prices: variant_id={variant_id}, stock={stock_value}, price={price_value}")
                    
                    # Zaktualizuj mapped_variant_uid w wega
                    wega_cursor.execute("""
                        UPDATE wega_productattribute 
                        SET mapped_variant_uid = %s, is_mapped = true, updated_at = NOW() 
                        WHERE id = %s
                    """, [variant_id, attribute_id])
                    
                    variant_ids.append(variant_id)
                    created_count += 1
                    continue

                # Sprawdź czy wariant istnieje w product_variants z tym samym kolorem
                # Szukamy wariantu z tym samym product_id, size_id, color_id i producer_color_id
                if producer_color_id and color_id:
                    mpd_cursor.execute("""
                        SELECT pv.variant_id 
                        FROM product_variants pv
                        WHERE pv.product_id = %s AND pv.size_id = %s AND pv.color_id = %s AND pv.producer_color_id = %s
                    """, [mpd_product_id, size_id, color_id, producer_color_id])
                elif color_id:
                    mpd_cursor.execute("""
                        SELECT pv.variant_id 
                        FROM product_variants pv
                        WHERE pv.product_id = %s AND pv.size_id = %s AND pv.color_id = %s AND (pv.producer_color_id IS NULL OR pv.producer_color_id IS NULL)
                    """, [mpd_product_id, size_id, color_id])
                else:
                    mpd_cursor.execute("""
                        SELECT pv.variant_id 
                        FROM product_variants pv
                        WHERE pv.product_id = %s AND pv.size_id = %s AND pv.color_id IS NULL
                    """, [mpd_product_id, size_id])
                existing_variant = mpd_cursor.fetchone()
                
                if existing_variant:
                    # Wariant już istnieje w product_variants z tym samym kolorem - użyj jego variant_id
                    variant_id = existing_variant[0]
                    logger.info(f"Wariant już istnieje w product_variants z tym samym kolorem (variant_id={variant_id}, color_id={color_id}, producer_color_id={producer_color_id}) - dodaję source dla wega")
                    
                    # Dodaj do product_variants_sources dla wega (sprawdź czy już istnieje)
                    mpd_cursor.execute("""
                        SELECT id FROM product_variants_sources 
                        WHERE variant_id = %s AND source_id = %s
                    """, [variant_id, source_id])
                    existing_source = mpd_cursor.fetchone()
                    
                    if not existing_source:
                        mpd_cursor.execute("""
                            INSERT INTO product_variants_sources (variant_id, ean, variant_uid, source_id)
                            VALUES (%s, %s, %s, %s)
                        """, [variant_id, ean, variant_uid, source_id])
                        logger.info(f"✅ Dodano product_variants_sources dla wega: variant_id={variant_id}")
                    else:
                        logger.info(f"ℹ️ product_variants_sources już istnieje dla wega: variant_id={variant_id}")
                else:
                    # Wygeneruj nowy variant_id i utwórz wariant
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
                    """, [variant_id, ean, variant_uid, source_id])

                # Dodaj lub zaktualizuj stock_and_prices
                # Upewnij się, że stock i price są poprawnych typów
                stock_value = int(stock) if stock is not None else 0
                if isinstance(product_price, Decimal):
                    price_value = product_price
                else:
                    price_value = Decimal(str(product_price)) if product_price else Decimal('0.00')
                
                # Sprawdź czy stock_and_prices już istnieje
                mpd_cursor.execute("""
                    SELECT variant_id FROM stock_and_prices 
                    WHERE variant_id = %s AND source_id = %s
                """, [variant_id, source_id])
                existing_stock = mpd_cursor.fetchone()
                
                if existing_stock:
                    # Aktualizuj istniejący stock_and_prices
                    mpd_cursor.execute("""
                        UPDATE stock_and_prices 
                        SET stock = %s, price = %s, last_updated = NOW()
                        WHERE variant_id = %s AND source_id = %s
                    """, [stock_value, price_value, variant_id, source_id])
                    logger.info(f"📦 Zaktualizowano stock_and_prices: variant_id={variant_id}, stock={stock_value}, price={price_value}")
                else:
                    # Dodaj nowy stock_and_prices
                    mpd_cursor.execute("""
                        INSERT INTO stock_and_prices (variant_id, source_id, stock, price, currency, last_updated)
                        VALUES (%s, %s, %s, %s, 'PLN', NOW())
                    """, [variant_id, source_id, stock_value, price_value])
                    logger.info(f"📦 Dodano stock_and_prices: variant_id={variant_id}, stock={stock_value}, price={price_value}")

                # Zaktualizuj mapped_variant_uid w wega
                wega_cursor.execute("""
                    UPDATE wega_productattribute 
                    SET mapped_variant_uid = %s, is_mapped = true, updated_at = NOW() 
                    WHERE id = %s
                """, [variant_id, attribute_id])

                variant_ids.append(variant_id)
                created_count += 1
                logger.info(f"Utworzono/zaktualizowano wariant {variant_uid} -> {variant_id}")

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
    """Usuń dane wega z MPD (kompensacja) - usuwa tylko dla source_id wega, nie usuwa wariantów"""
    logger.info(f"🔄 Usuwam dane wega z MPD dla produktu {mpd_product_id}")

    # Pobierz source_id dla wega
    source_id = get_source_id('wega')
    if not source_id:
        logger.error("❌ Nie można pobrać source_id dla wega z bazy MPD")
        return {}

    try:
        with connections['MPD'].cursor() as mpd_cursor:
            if variant_ids:
                # Usuń dane wega dla konkretnych wariantów
                for variant_id in variant_ids:
                    # Usuń stock_and_prices dla source_id wega
                    mpd_cursor.execute(
                        "DELETE FROM stock_and_prices WHERE variant_id = %s AND source_id = %s", 
                        [variant_id, source_id])
                    # Usuń product_variants_sources dla source_id wega
                    mpd_cursor.execute(
                        "DELETE FROM product_variants_sources WHERE variant_id = %s AND source_id = %s", 
                        [variant_id, source_id])
                    logger.info(f"✅ Usunięto dane wega dla wariantu {variant_id}")
                logger.info(f"✅ Usunięto dane wega dla {len(variant_ids)} wariantów")
            else:
                # Usuń wszystkie dane wega dla produktu
                # Znajdź wszystkie warianty produktu, które mają source_id wega
                mpd_cursor.execute("""
                    SELECT DISTINCT pvs.variant_id 
                    FROM product_variants_sources pvs
                    JOIN product_variants pv ON pvs.variant_id = pv.variant_id
                    WHERE pv.product_id = %s AND pvs.source_id = %s
                """, [mpd_product_id, source_id])
                variant_ids = [row[0] for row in mpd_cursor.fetchall()]

                for variant_id in variant_ids:
                    # Usuń stock_and_prices dla source_id wega
                    mpd_cursor.execute(
                        "DELETE FROM stock_and_prices WHERE variant_id = %s AND source_id = %s", 
                        [variant_id, source_id])
                    # Usuń product_variants_sources dla source_id wega
                    mpd_cursor.execute(
                        "DELETE FROM product_variants_sources WHERE variant_id = %s AND source_id = %s", 
                        [variant_id, source_id])
                logger.info(
                    f"✅ Usunięto wszystkie dane wega (source_id={source_id}) dla produktu {mpd_product_id}")

        # Cofnij mapping w wega
        if wega_product_id:
            with connections['wega'].cursor() as wega_cursor:
                wega_cursor.execute("""
                    UPDATE wega_productattribute 
                    SET mapped_variant_uid = NULL, is_mapped = false, updated_at = NOW() 
                    WHERE product_id = %s
                """, [wega_product_id])

    except Exception as e:
        logger.error(f"❌ Błąd podczas usuwania danych wega: {e}")

    return {}

