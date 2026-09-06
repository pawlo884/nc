"""
Unit: `tabu.stock_tracker.track_stock_change` — zapis pojedynczej zmiany
stanu do `StockHistory`.
"""
from __future__ import annotations

import pytest

from tabu.models import StockHistory
from tabu.stock_tracker import track_stock_change

pytestmark = pytest.mark.django_db


def test_zapisuje_wiersz_ze_spadkiem_stanu():
    sh = track_stock_change(
        variant_api_id=111, product_api_id=222, old_stock=5, new_stock=3,
        product_name="Bluzka", variant_symbol="BL-M")

    assert sh is not None
    row = StockHistory.objects.get(pk=sh.pk)
    assert (row.old_stock, row.new_stock, row.stock_change) == (5, 3, -2)
    assert row.change_type == "decrease"
    assert row.product_name == "Bluzka" and row.variant_symbol == "BL-M"


def test_wzrost_i_brak_zmiany():
    up = track_stock_change(variant_api_id=1, product_api_id=1, old_stock=0, new_stock=4)
    same = track_stock_change(variant_api_id=2, product_api_id=1, old_stock=4, new_stock=4)

    assert StockHistory.objects.get(pk=up.pk).change_type == "increase"
    assert StockHistory.objects.get(pk=same.pk).change_type == "no_change"


def test_none_traktowane_jak_zero():
    sh = track_stock_change(variant_api_id=1, product_api_id=1, old_stock=None, new_stock=None)
    row = StockHistory.objects.get(pk=sh.pk)
    assert (row.old_stock, row.new_stock, row.stock_change) == (0, 0, 0)
    assert row.change_type == "no_change"
