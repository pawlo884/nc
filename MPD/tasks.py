from celery import shared_task
from django.db import connections
from datetime import timedelta
from django.utils import timezone
from django.utils.timezone import localtime
import logging
from celery.signals import worker_ready

logger = logging.getLogger(__name__)


# @worker_ready.connect
# def at_start(sender, **kwargs):
#     sender.app.send_task('MPD.tasks.track_recent_stock_changes')


@shared_task
def track_recent_stock_changes():
    start_time = timezone.now()
    logger.info(
        f"Rozpoczęcie zadania track_recent_stock_changes: {localtime(start_time)}")

    now = timezone.now()
    seven_minutes_ago = now - timedelta(minutes=7)
    logger.info(f"Sprawdzanie zmian od: {seven_minutes_ago}")

    with connections['MPD'].cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM stock_and_prices")
        count_row = cursor.fetchone()
        count = count_row[0] if count_row else 0
        logger.info(f"Liczba wszystkich rekordów w stock_and_prices: {count}")

        cursor.execute("SELECT current_database(), current_user")
        logger.info(f"Baza: {cursor.fetchone()}")

        cursor.execute("SELECT current_schema()")
        logger.info(f"Schemat: {cursor.fetchone()}")

        cursor.execute("""
            SELECT id, last_updated FROM stock_and_prices
            ORDER BY last_updated DESC
            LIMIT 10
        """)
        logger.info(f"TOP 10 rekordów w stock_and_prices: {cursor.fetchall()}")

        cursor.execute("""
            SELECT id, stock, price, source_id, last_updated
            FROM stock_and_prices
            WHERE last_updated >= %s
        """, [seven_minutes_ago])
        updated_products = cursor.fetchall()
        logger.info(
            f"Znaleziono {len(updated_products)} rekordów do sprawdzenia")

        for stock_id, current_stock, current_price, source_id, last_updated in updated_products:
            logger.info(
                f"Przetwarzanie produktu {stock_id}, ostatnia aktualizacja: {last_updated}")
            cursor.execute("""
                SELECT new_stock, new_price
                FROM stock_history
                WHERE stock_id = %s
                ORDER BY change_date DESC
                LIMIT 1
            """, [stock_id])
            row = cursor.fetchone()
            last_stock = row[0] if row else None
            last_price = row[1] if row else None

            if last_stock is None:
                logger.info(
                    f"Nowy produkt {stock_id}, dodaję do historii od zera")
                # Najpierw wpis 0 -> 0 dla stock i price
                cursor.execute("""
                    INSERT INTO stock_history (stock_id, source_id, previous_stock, new_stock, previous_price, new_price, change_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [stock_id, source_id, 0, 0, 0, 0, now])
                # Następnie wpis 0 -> current_stock/price (jeśli current_stock > 0 lub current_price > 0)
                if current_stock != 0 or current_price != 0:
                    cursor.execute("""
                        INSERT INTO stock_history (stock_id, source_id, previous_stock, new_stock, previous_price, new_price, change_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, [stock_id, source_id, 0, current_stock, 0, current_price, now])
            elif last_stock != current_stock or last_price != current_price:
                logger.info(
                    f"Zmiana stanu dla {stock_id}: stock {last_stock} -> {current_stock}, price {last_price} -> {current_price}")
                cursor.execute("""
                    INSERT INTO stock_history (stock_id, source_id, previous_stock, new_stock, previous_price, new_price, change_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [stock_id, source_id, last_stock, current_stock, last_price, current_price, now])

    end_time = timezone.now()
    execution_time = end_time - start_time
    logger.info(
        f"Zakończenie zadania track_recent_stock_changes: {localtime(end_time)}")
    logger.info(f"Czas wykonania zadania: {execution_time}")
