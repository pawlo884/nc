from celery import shared_task
from django.db import connections
from datetime import datetime, timedelta


@shared_task
def track_recent_stock_changes():
    now = datetime.now()
    seven_minutes_ago = now - timedelta(minutes=7)
    with connections['MPD'].cursor() as cursor:
        cursor.execute("""
            SELECT id, stock, source_id, last_updated
            FROM stock_and_prices
            WHERE last_updated >= %s
        """, [seven_minutes_ago])
        updated_products = cursor.fetchall()
        print(f"Znaleziono {len(updated_products)} rekordów do sprawdzenia")

        for stock_id, current_stock, source_id, last_updated in updated_products:
            cursor.execute("""
                SELECT new_stock
                FROM stock_history
                WHERE stock_id = %s
                ORDER BY change_date DESC
                LIMIT 1
            """, [stock_id])
            row = cursor.fetchone()
            last_stock = row[0] if row else None

            if last_stock is None:
                print(f"Nowy produkt {stock_id}, dodaję do historii")
                cursor.execute("""
                    INSERT INTO stock_history (stock_id, source_id, previous_stock, new_stock, change_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, [stock_id, source_id, None, current_stock, now])
            elif last_stock != current_stock:
                print(
                    f"Zmiana stanu dla {stock_id}: {last_stock} -> {current_stock}")
                cursor.execute("""
                    INSERT INTO stock_history (stock_id, source_id, previous_stock, new_stock, change_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, [stock_id, source_id, last_stock, current_stock, now])
