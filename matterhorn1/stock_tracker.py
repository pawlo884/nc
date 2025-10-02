"""
Funkcje pomocnicze do śledzenia zmian stanów magazynowych w matterhorn1
"""
import logging
from django.db import connections, transaction
from django.utils import timezone
from .models import StockHistory, Product, ProductVariant

logger = logging.getLogger(__name__)


def track_stock_change(variant_uid, product_uid, old_stock, new_stock, product_name=None, variant_name=None):
    """
    Śledzi zmianę stanu magazynowego i zapisuje do StockHistory

    Args:
        variant_uid: ID wariantu
        product_uid: ID produktu
        old_stock: Poprzedni stan magazynowy
        new_stock: Nowy stan magazynowy
        product_name: Nazwa produktu (opcjonalne)
        variant_name: Nazwa wariantu (opcjonalne)
    """
    try:
        # Oblicz zmianę stanu
        stock_change = new_stock - old_stock

        # Określ typ zmiany
        if stock_change > 0:
            change_type = 'increase'
        elif stock_change < 0:
            change_type = 'decrease'
        else:
            change_type = 'no_change'

        # Pobierz nazwy jeśli nie podano
        if not product_name or not variant_name:
            try:
                with connections['matterhorn1'].cursor() as cursor:
                    cursor.execute("""
                        SELECT p.name, pv.name 
                        FROM product p 
                        JOIN productvariant pv ON p.id = pv.product_id 
                        WHERE p.product_uid = %s AND pv.variant_uid = %s
                    """, [product_uid, variant_uid])
                    result = cursor.fetchone()
                    if result:
                        product_name = product_name or result[0]
                        variant_name = variant_name or result[1]
            except Exception as e:
                logger.warning(
                    f"Nie udało się pobrać nazw produktu/wariantu: {e}")

        # Zapisz do StockHistory
        stock_history = StockHistory.objects.using('matterhorn1').create(
            variant_uid=variant_uid,
            product_uid=product_uid,
            product_name=product_name,
            variant_name=variant_name,
            old_stock=old_stock,
            new_stock=new_stock,
            stock_change=stock_change,
            change_type=change_type
        )

        logger.info(
            f"Zapisano zmianę stanu: {product_name} - {variant_name}: {old_stock} → {new_stock} ({change_type})")
        return stock_history

    except Exception as e:
        logger.error(f"Błąd podczas śledzenia zmiany stanu: {e}")
        return None


def track_bulk_stock_changes(changes_data):
    """
    Śledzi masowe zmiany stanów magazynowych

    Args:
        changes_data: Lista słowników z danymi zmian
        [
            {
                'variant_uid': '123',
                'product_id': 456,
                'old_stock': 10,
                'new_stock': 5,
                'product_name': 'Produkt A',
                'variant_name': 'M'
            },
            ...
        ]
    """
    try:
        with transaction.atomic(using='matterhorn1'):
            created_records = []

            for change_data in changes_data:
                stock_history = track_stock_change(**change_data)
                if stock_history:
                    created_records.append(stock_history)

            logger.info(
                f"Zapisano {len(created_records)} zmian stanów magazynowych")
            return created_records

    except Exception as e:
        logger.error(f"Błąd podczas śledzenia masowych zmian stanów: {e}")
        return []


def get_stock_trends(product_uid=None, variant_uid=None, days=30):
    """
    Pobiera trendy stanów magazynowych dla konkretnego produktu lub wariantu

    Args:
        product_uid: ID produktu (opcjonalne)
        variant_uid: ID wariantu (opcjonalne)
        days: Liczba dni wstecz
    """
    try:
        with connections['matterhorn1'].cursor() as cursor:
            cutoff_date = timezone.now() - timezone.timedelta(days=days)

            if product_uid:
                query = """
                    SELECT 
                        sh.variant_uid,
                        sh.variant_name,
                        sh.old_stock,
                        sh.new_stock,
                        sh.stock_change,
                        sh.change_type,
                        sh.timestamp
                    FROM stock_history sh
                    WHERE sh.product_uid = %s
                        AND sh.timestamp >= %s
                    ORDER BY sh.timestamp DESC
                """
                cursor.execute(query, [product_uid, cutoff_date])
            elif variant_uid:
                query = """
                    SELECT 
                        sh.variant_uid,
                        sh.variant_name,
                        sh.old_stock,
                        sh.new_stock,
                        sh.stock_change,
                        sh.change_type,
                        sh.timestamp
                    FROM stock_history sh
                    WHERE sh.variant_uid = %s
                        AND sh.timestamp >= %s
                    ORDER BY sh.timestamp DESC
                """
                cursor.execute(query, [variant_uid, cutoff_date])
            else:
                return []

            results = cursor.fetchall()

            trends = []
            for row in results:
                trends.append({
                    'variant_uid': row[0],
                    'variant_name': row[1],
                    'old_stock': row[2],
                    'new_stock': row[3],
                    'stock_change': row[4],
                    'change_type': row[5],
                    'timestamp': row[6]
                })

            return trends

    except Exception as e:
        logger.error(
            f"Błąd podczas pobierania trendów stanów magazynowych: {e}")
        return []


def get_popular_products(days=30, limit=20):
    """
    Pobiera najbardziej popularne produkty na podstawie spadków stanów magazynowych

    Args:
        days: Liczba dni wstecz
        limit: Maksymalna liczba produktów
    """
    try:
        with connections['matterhorn1'].cursor() as cursor:
            cutoff_date = timezone.now() - timezone.timedelta(days=days)

            query = """
                SELECT 
                    sh.product_uid,
                    sh.product_name,
                    COUNT(*) as total_decreases,
                    SUM(ABS(sh.stock_change)) as total_stock_sold,
                    AVG(ABS(sh.stock_change)) as avg_stock_sold_per_change,
                    MAX(sh.timestamp) as last_activity
                FROM stock_history sh
                WHERE sh.change_type = 'decrease'
                    AND sh.timestamp >= %s
                GROUP BY sh.product_uid, sh.product_name
                ORDER BY total_stock_sold DESC, total_decreases DESC
                LIMIT %s
            """

            cursor.execute(query, [cutoff_date, limit])
            results = cursor.fetchall()

            popular_products = []
            for row in results:
                popular_products.append({
                    'product_uid': row[0],
                    'product_name': row[1],
                    'total_decreases': row[2],
                    'total_stock_sold': row[3],
                    'avg_stock_sold_per_change': float(row[4]) if row[4] else 0,
                    'last_activity': row[5]
                })

            return popular_products

    except Exception as e:
        logger.error(f"Błąd podczas pobierania popularnych produktów: {e}")
        return []


def get_stock_statistics(days=30):
    """
    Pobiera ogólne statystyki stanów magazynowych

    Args:
        days: Liczba dni wstecz
    """
    try:
        with connections['matterhorn1'].cursor() as cursor:
            cutoff_date = timezone.now() - timezone.timedelta(days=days)

            query = """
                SELECT 
                    COUNT(*) as total_changes,
                    COUNT(CASE WHEN change_type = 'increase' THEN 1 END) as increases,
                    COUNT(CASE WHEN change_type = 'decrease' THEN 1 END) as decreases,
                    COUNT(CASE WHEN change_type = 'no_change' THEN 1 END) as no_changes,
                    SUM(CASE WHEN change_type = 'decrease' THEN ABS(stock_change) ELSE 0 END) as total_sold,
                    SUM(CASE WHEN change_type = 'increase' THEN stock_change ELSE 0 END) as total_added,
                    AVG(CASE WHEN change_type = 'decrease' THEN ABS(stock_change) ELSE NULL END) as avg_sold_per_decrease,
                    COUNT(DISTINCT product_uid) as unique_products,
                    COUNT(DISTINCT variant_uid) as unique_variants
                FROM stock_history
                WHERE timestamp >= %s
            """

            cursor.execute(query, [cutoff_date])
            result = cursor.fetchone()

            if result:
                stats = {
                    'total_changes': result[0],
                    'increases': result[1],
                    'decreases': result[2],
                    'no_changes': result[3],
                    'total_sold': result[4] or 0,
                    'total_added': result[5] or 0,
                    'avg_sold_per_decrease': float(result[6]) if result[6] else 0,
                    'unique_products': result[7],
                    'unique_variants': result[8]
                }
            else:
                stats = {}

            return stats

    except Exception as e:
        logger.error(
            f"Błąd podczas pobierania statystyk stanów magazynowych: {e}")
        return {}


def clean_old_stock_history(days_to_keep=90):
    """
    Usuwa stare rekordy z historii stanów magazynowych

    Args:
        days_to_keep: Liczba dni do zachowania
    """
    try:
        with connections['matterhorn1'].cursor() as cursor:
            cutoff_date = timezone.now() - timezone.timedelta(days=days_to_keep)

            delete_query = """
                DELETE FROM stock_history
                WHERE timestamp < %s
            """

            cursor.execute(delete_query, [cutoff_date])
            deleted_count = cursor.rowcount

            logger.info(
                f"Usunięto {deleted_count} starych rekordów z historii stanów magazynowych")
            return f"Usunięto {deleted_count} starych rekordów z historii stanów magazynowych"

    except Exception as e:
        logger.error(
            f"Błąd podczas czyszczenia historii stanów magazynowych: {e}")
        return f"Błąd podczas czyszczenia historii: {e}"


def sync_stock_changes_from_api():
    """
    Synchronizuje zmiany stanów z API i śledzi je w StockHistory
    Ta funkcja może być wywoływana przez Celery task
    """
    try:
        # Pobierz wszystkie warianty z ostatnimi zmianami
        variants = ProductVariant.objects.using(
            'matterhorn1').select_related('product').all()

        changes_data = []
        for variant in variants:
            # Sprawdź czy wariant ma mapped_variant_uid (jest zmapowany do MPD)
            if variant.mapped_variant_uid:
                # Pobierz aktualny stan z MPD
                with connections['MPD'].cursor() as cursor:
                    cursor.execute("""
                        SELECT stock FROM stock_and_prices 
                        WHERE variant_id = %s AND source_id = %s
                    """, [variant.mapped_variant_uid, 2])
                    result = cursor.fetchone()

                    if result:
                        mpd_stock = result[0]
                        # Jeśli stan się zmienił, śledź zmianę
                        if variant.stock != mpd_stock:
                            changes_data.append({
                                'variant_uid': variant.variant_uid,
                                'product_uid': variant.product.product_uid,
                                'old_stock': variant.stock,
                                'new_stock': mpd_stock,
                                'product_name': variant.product.name,
                                'variant_name': variant.name
                            })

                            # Aktualizuj stan w matterhorn1
                            variant.stock = mpd_stock
                            variant.save(using='matterhorn1')

        # Śledź wszystkie zmiany
        if changes_data:
            track_bulk_stock_changes(changes_data)
            logger.info(
                f"Zsynchronizowano {len(changes_data)} zmian stanów z API")

        return len(changes_data)

    except Exception as e:
        logger.error(f"Błąd podczas synchronizacji stanów z API: {e}")
        return 0
