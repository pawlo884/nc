"""
Unit/integration: funkcje raportowe i sprzątające `matterhorn1.stock_tracker`
czytające `matterhorn1_stock_history`.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from matterhorn1.models import StockHistory
from matterhorn1.stock_tracker import (
    clean_old_stock_history,
    get_popular_products,
    get_stock_statistics,
    get_stock_trends,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases=["default", "matterhorn1"])]
DB = "matterhorn1"


def _hist(days_ago=1, **fields):
    defaults = dict(variant_uid="1", product_uid=1, old_stock=10, new_stock=5,
                    stock_change=-5, change_type="decrease")
    defaults.update(fields)
    row = StockHistory.objects.using(DB).create(**defaults)
    StockHistory.objects.using(DB).filter(pk=row.pk).update(
        timestamp=timezone.now() - timedelta(days=days_ago))
    return row


class TestGetStockTrends:
    def test_bez_argumentow_zwraca_pusto(self):
        _hist()
        assert get_stock_trends() == []

    def test_po_product_uid(self):
        _hist(product_uid=42, variant_uid="A")
        _hist(product_uid=42, variant_uid="B")
        _hist(product_uid=99, variant_uid="C")

        trends = get_stock_trends(product_uid=42)
        assert {t["variant_uid"] for t in trends} == {"A", "B"}

    def test_respektuje_okno_dni(self):
        _hist(product_uid=42, days_ago=5)
        _hist(product_uid=42, days_ago=40)   # poza oknem 30 dni

        assert len(get_stock_trends(product_uid=42, days=30)) == 1


class TestGetPopularProducts:
    def test_ranking_po_sumie_spadkow(self):
        for _ in range(3):
            _hist(product_uid=1, product_name="Hit", stock_change=-4, change_type="decrease")
        _hist(product_uid=2, product_name="Slaby", stock_change=-1, change_type="decrease")
        _hist(product_uid=3, product_name="Wzrost", stock_change=5, change_type="increase")

        popular = get_popular_products(days=30, limit=10)

        assert popular[0]["product_uid"] == 1
        assert popular[0]["total_decreases"] == 3
        assert all(p["product_uid"] != 3 for p in popular)  # tylko 'decrease'


class TestGetStockStatistics:
    def test_agreguje_typy_zmian(self):
        _hist(change_type="decrease", stock_change=-3)
        _hist(change_type="decrease", stock_change=-2)
        _hist(change_type="increase", stock_change=7)
        _hist(change_type="no_change", stock_change=0)

        stats = get_stock_statistics(days=30)

        assert stats["total_changes"] == 4
        assert stats["decreases"] == 2
        assert stats["increases"] == 1
        assert stats["total_sold"] == 5
        assert stats["total_added"] == 7

    def test_pusto_gdy_brak_danych(self):
        stats = get_stock_statistics(days=30)
        assert stats["total_changes"] == 0


class TestCleanOldStockHistory:
    def test_usuwa_tylko_starsze_niz_prog(self):
        _hist(days_ago=200)
        _hist(days_ago=200)
        _hist(days_ago=10)

        msg = clean_old_stock_history(days_to_keep=90)

        assert "Usunięto 2" in msg
        assert StockHistory.objects.using(DB).count() == 1
