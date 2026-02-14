"""
Śledzenie zmian stanów magazynowych Tabu (analogicznie do matterhorn1).
"""
import logging
from django.db import router, transaction

from .models import StockHistory, TabuProduct, TabuProductVariant

logger = logging.getLogger(__name__)


def track_stock_change(
    variant_api_id,
    product_api_id,
    old_stock,
    new_stock,
    product_name=None,
    variant_symbol=None,
):
    """
    Zapisuje zmianę stanu magazynowego do StockHistory.

    Args:
        variant_api_id: ID wariantu z API Tabu
        product_api_id: ID produktu z API Tabu
        old_stock: Poprzedni stan
        new_stock: Nowy stan
        product_name: Nazwa produktu (opcjonalne)
        variant_symbol: Symbol wariantu (opcjonalne)
    """
    try:
        stock_change = (new_stock or 0) - (old_stock or 0)
        change_type = 'increase' if stock_change > 0 else ('decrease' if stock_change < 0 else 'no_change')

        db = router.db_for_write(StockHistory)
        stock_history = StockHistory.objects.using(db).create(
            variant_api_id=variant_api_id,
            product_api_id=product_api_id,
            product_name=product_name or '',
            variant_symbol=variant_symbol or '',
            old_stock=old_stock or 0,
            new_stock=new_stock or 0,
            stock_change=stock_change,
            change_type=change_type,
        )
        logger.info(
            f"Tabu stock history: {product_name} - {variant_symbol}: {old_stock} → {new_stock} ({change_type})"
        )
        return stock_history
    except Exception as e:
        logger.error(f"Błąd zapisu historii stanu Tabu: {e}")
        return None
