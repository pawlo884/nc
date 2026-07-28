"""
Śledzenie zmian stanów magazynowych Mada (analogicznie do matterhorn1/tabu).
"""
import logging

from django.db import router

from .models import StockHistory

logger = logging.getLogger(__name__)


def track_stock_change(
    product_api_id,
    variant_key,
    old_stock,
    new_stock,
    product_name=None,
    variant_label=None,
):
    """Zapisuje zmianę stanu magazynowego do StockHistory (tylko gdy faktycznie się zmienił)."""
    try:
        stock_change = (new_stock or 0) - (old_stock or 0)
        if stock_change == 0:
            return None
        change_type = 'increase' if stock_change > 0 else 'decrease'

        db = router.db_for_write(StockHistory)
        stock_history = StockHistory.objects.using(db).create(
            product_api_id=product_api_id,
            variant_key=variant_key or '',
            product_name=product_name or '',
            variant_label=variant_label or '',
            old_stock=old_stock or 0,
            new_stock=new_stock or 0,
            stock_change=stock_change,
            change_type=change_type,
        )
        return stock_history
    except Exception:
        logger.exception(
            'Błąd zapisu historii stanu Mada: product=%s variant=%s', product_api_id, variant_key,
        )
        return None
