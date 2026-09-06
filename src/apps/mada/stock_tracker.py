"""
Śledzenie zmian stanów magazynowych Mada (analogicznie do matterhorn1/tabu).
"""
import logging

from django.db import router

from .models import StockHistory

logger = logging.getLogger(__name__)


def build_stock_history_row(
    product_api_id,
    variant_key,
    old_stock,
    new_stock,
    product_name=None,
    variant_label=None,
):
    """Zwraca niezapisany obiekt StockHistory gotowy do bulk_create.
    None, gdy stan się nie zmienił (nic do zapisania)."""
    old = old_stock or 0
    new = new_stock or 0
    stock_change = new - old
    if stock_change == 0:
        return None
    return StockHistory(
        product_api_id=product_api_id,
        variant_key=variant_key or '',
        product_name=product_name or '',
        variant_label=variant_label or '',
        old_stock=old,
        new_stock=new,
        stock_change=stock_change,
        change_type='increase' if stock_change > 0 else 'decrease',
    )


def track_stock_change(
    product_api_id,
    variant_key,
    old_stock,
    new_stock,
    product_name=None,
    variant_label=None,
):
    """Zapisuje pojedynczą zmianę stanu do StockHistory (tylko gdy faktycznie się
    zmienił). Import masowy używa `build_stock_history_row` + `bulk_create`;
    ten helper zostaje dla użycia ad-hoc (np. z shella / sagi)."""
    try:
        row = build_stock_history_row(
            product_api_id, variant_key, old_stock, new_stock, product_name, variant_label,
        )
        if row is None:
            return None
        db = router.db_for_write(StockHistory)
        row.save(using=db)
        return row
    except Exception:
        logger.exception(
            'Błąd zapisu historii stanu Mada: product=%s variant=%s', product_api_id, variant_key,
        )
        return None
