"""
Funkcje pomocnicze dla tworzenia wariantów w Sadze
"""
import logging
from typing import Dict, List
from django.db import connections

logger = logging.getLogger(__name__)


def create_mpd_variants(mpd_product_id: int, matterhorn_product_id: int, size_category: str,
                        producer_code: str = None, main_color_id: int = None,
                        producer_color_name: str = None) -> Dict:
    """Utwórz warianty w MPD razem z produktem"""
    logger.info(
        f"🔄 Tworzę warianty w MPD dla produktu {mpd_product_id}, kategoria: {size_category}")
    logger.info(
        f"📋 Parametry: producer_code='{producer_code}', main_color_id={main_color_id}, producer_color_name='{producer_color_name}'")

    try:
        with connections['MPD'].cursor() as mpd_cursor, connections['matterhorn1'].cursor() as mh_cursor:
            # Pobierz kolor i cenę produktu z matterhorn1
            mh_cursor.execute("""
                SELECT color, prices FROM product WHERE id = %s
            """, [matterhorn_product_id])
            color_result = mh_cursor.fetchone()
            if not color_result:
                raise Exception(
                    f"Product {matterhorn_product_id} not found in matterhorn1")

            product_color, product_prices = color_result

            # Wyciągnij cenę PLN z JSON
            if isinstance(product_prices, str):
                import json
                product_prices = json.loads(product_prices)
            product_price = product_prices.get(
                'PLN', 0) if isinstance(product_prices, dict) else 0
            if isinstance(product_price, str):
                product_price = float(product_price)

            logger.info(
                f"Produkt: kolor={product_color}, cena={product_price}")

            # Pobierz ID koloru w MPD
            mpd_cursor.execute(
                "SELECT id FROM colors WHERE name = %s", [product_color])
            color_row = mpd_cursor.fetchone()
            if not color_row:
                raise Exception(f"Color {product_color} not found in MPD")
            color_id = color_row[0]

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

            # Pobierz warianty z matterhorn1
            mh_cursor.execute("""
                SELECT name, stock, ean, variant_uid FROM productvariant WHERE product_id = %s
            """, [matterhorn_product_id])
            variants = mh_cursor.fetchall()

            if not variants:
                logger.warning(
                    f"Brak wariantów dla produktu {matterhorn_product_id}")
                return {"created_variants": 0, "iai_product_id": iai_product_id}

            # Pobierz source_id dla Matterhorn
            mpd_cursor.execute(
                "SELECT id FROM sources WHERE name ILIKE %s LIMIT 1",
                ['%matterhorn%']
            )
            mh_source_row = mpd_cursor.fetchone()
            mh_source_id = mh_source_row[0] if mh_source_row else 2

            created_count = 0
            variant_ids = []

            for size_name, stock, ean, variant_uid in variants:
                # Pobierz ID rozmiaru z wybranej kategorii
                mpd_cursor.execute("SELECT id FROM sizes WHERE UPPER(name) = UPPER(%s) AND category = %s",
                                   [size_name, size_category])
                size_result = mpd_cursor.fetchone()
                if not size_result:
                    logger.warning(
                        f"Rozmiar {size_name} nie znaleziony w kategorii {size_category}")
                    continue
                size_id = size_result[0]

                # Sprawdź czy wariant już istnieje (variant_uid + source)
                mpd_cursor.execute("""
                    SELECT variant_id FROM product_variants_sources 
                    WHERE variant_uid = %s AND source_id = %s
                """, [variant_uid, mh_source_id])
                existing = mpd_cursor.fetchone()
                if existing:
                    logger.info(
                        f"Wariant {variant_uid} już istnieje - pomijam")
                    continue

                # Sprawdź czy istnieje wariant z tym EAN (z innej hurtowni) - dopnij zamiast tworzyć
                variant_id = None
                if ean and str(ean).strip():
                    mpd_cursor.execute("""
                        SELECT pvs.variant_id FROM product_variants_sources pvs
                        JOIN product_variants pv ON pv.variant_id = pvs.variant_id
                        WHERE pvs.ean = %s AND pv.product_id = %s AND pvs.source_id != %s
                    """, [str(ean).strip(), mpd_product_id, mh_source_id])
                    existing_by_ean = mpd_cursor.fetchone()
                    if existing_by_ean:
                        variant_id = existing_by_ean[0]
                        logger.info(
                            f"Znaleziono wariant po EAN {ean} (variant_id={variant_id}) - dopinam Matterhorn"
                        )

                if variant_id is None:
                    # Wygeneruj nowy variant_id
                    mpd_cursor.execute(
                        "SELECT COALESCE(MAX(variant_id), 0) + 1 FROM product_variants")
                    row = mpd_cursor.fetchone()
                    variant_id = row[0] if row else 1

                    # Utwórz wariant
                    logger.info(
                        f"🔧 Tworzę wariant {variant_id}: producer_color_id={producer_color_id}, producer_code='{producer_code}'")
                    if producer_color_id:
                        mpd_cursor.execute("""
                            INSERT INTO product_variants 
                            (variant_id, product_id, color_id, producer_color_id, size_id, producer_code, iai_product_id, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        """, [variant_id, mpd_product_id, color_id, producer_color_id, size_id, producer_code, iai_product_id])
                        logger.info(
                            f"✅ Utworzono wariant z producer_color_id={producer_color_id}")
                    else:
                        mpd_cursor.execute("""
                            INSERT INTO product_variants 
                            (variant_id, product_id, color_id, size_id, producer_code, iai_product_id, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """, [variant_id, mpd_product_id, color_id, size_id, producer_code, iai_product_id])
                        logger.info(f"⚠️ Utworzono wariant BEZ producer_color_id")

                # Dodaj do product_variants_sources (jeśli nie istnieje)
                mpd_cursor.execute("""
                    SELECT 1 FROM product_variants_sources 
                    WHERE variant_id = %s AND source_id = %s
                """, [variant_id, mh_source_id])
                if not mpd_cursor.fetchone():
                    mpd_cursor.execute("""
                        INSERT INTO product_variants_sources (variant_id, ean, variant_uid, source_id)
                        VALUES (%s, %s, %s, %s)
                    """, [variant_id, ean, variant_uid, mh_source_id])

                # Dodaj stock_and_prices (jeśli nie istnieje)
                mpd_cursor.execute("""
                    SELECT 1 FROM stock_and_prices WHERE variant_id = %s AND source_id = %s
                """, [variant_id, mh_source_id])
                if not mpd_cursor.fetchone():
                    mpd_cursor.execute("""
                        INSERT INTO stock_and_prices (variant_id, source_id, stock, price, currency)
                        VALUES (%s, %s, %s, %s, 'PLN')
                    """, [variant_id, mh_source_id, stock, product_price])

                # Zaktualizuj mapped_variant_uid w matterhorn1
                mh_cursor.execute("""
                    UPDATE productvariant 
                    SET mapped_variant_uid = %s, is_mapped = true, updated_at = NOW() 
                    WHERE variant_uid = %s
                """, [variant_id, variant_uid])

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


def delete_mpd_variants(mpd_product_id: int, matterhorn_product_id: int = None,
                        variant_ids: List[int] = None, **kwargs) -> Dict:
    """Usuń warianty z MPD (kompensacja)"""
    logger.info(f"🔄 Usuwam warianty z MPD dla produktu {mpd_product_id}")

    try:
        with connections['MPD'].cursor() as mpd_cursor:
            if variant_ids:
                # Usuń konkretne warianty
                for variant_id in variant_ids:
                    # Usuń z stock_and_prices
                    mpd_cursor.execute(
                        "DELETE FROM stock_and_prices WHERE variant_id = %s", [variant_id])
                    # Usuń z product_variants_sources
                    mpd_cursor.execute(
                        "DELETE FROM product_variants_sources WHERE variant_id = %s", [variant_id])
                    # Usuń z product_variants
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

        # Cofnij mapping w matterhorn1
        if matterhorn_product_id:
            with connections['matterhorn1'].cursor() as mh_cursor:
                mh_cursor.execute("""
                    UPDATE productvariant 
                    SET mapped_variant_uid = NULL, is_mapped = false, updated_at = NOW() 
                    WHERE product_id = %s
                """, [matterhorn_product_id])

    except Exception as e:
        logger.error(f"❌ Błąd podczas usuwania wariantów: {e}")

    return {}
