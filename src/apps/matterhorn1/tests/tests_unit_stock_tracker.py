"""
Unit: `matterhorn1.stock_tracker` — zapis zmian stanu do `StockHistory`.

Woła je `matterhorn1.tasks._bulk_update_inventory` przy każdej realnej zmianie
stanu wariantu.
"""
from __future__ import annotations

import pytest

from matterhorn1.models import Brand, Category, Product, ProductVariant, StockHistory
from matterhorn1.stock_tracker import track_bulk_stock_changes, track_stock_change

pytestmark = [pytest.mark.unit, pytest.mark.django_db(databases=["default", "matterhorn1"])]

DB = "matterhorn1"


@pytest.fixture
def variant():
    brand = Brand.objects.using(DB).create(brand_id="B1", name="Marko")
    cat = Category.objects.using(DB).create(category_id="C1", name="Bikini")
    product = Product.objects.using(DB).create(
        product_uid=4242, name="Kostium X", brand=brand, category=cat)
    return ProductVariant.objects.using(DB).create(
        product=product, variant_uid=999, name="M", stock=10)


class TestTrackStockChange:
    def test_spadek_stanu(self, variant):
        row = track_stock_change(
            variant_uid=999, product_uid=4242, old_stock=10, new_stock=3,
            product_name="Kostium X", variant_name="M")
        assert row.stock_change == -7
        assert row.change_type == "decrease"
        assert row.new_stock == 3

    def test_wzrost_stanu(self, variant):
        row = track_stock_change(
            variant_uid=999, product_uid=4242, old_stock=3, new_stock=12,
            product_name="X", variant_name="M")
        assert row.stock_change == 9
        assert row.change_type == "increase"

    def test_brak_zmiany(self, variant):
        row = track_stock_change(
            variant_uid=999, product_uid=4242, old_stock=5, new_stock=5,
            product_name="X", variant_name="M")
        assert row.stock_change == 0
        assert row.change_type == "no_change"

    def test_nazwy_dociagane_z_bazy_gdy_nie_podane(self, variant):
        # variant_uid jako string — raw SQL fallback porównuje z kolumną
        # varchar `productvariant.variant_uid` (int rzuca "varchar = integer").
        row = track_stock_change(
            variant_uid="999", product_uid=4242, old_stock=10, new_stock=0)
        assert row.product_name == "Kostium X"
        assert row.variant_name == "M"

    def test_brak_nazw_i_brak_wpisu_w_bazie_nie_wywala(self, db):
        row = track_stock_change(
            variant_uid="404", product_uid=404, old_stock=1, new_stock=0)
        assert row is not None
        assert row.product_name is None

    def test_zapisuje_wiersz_do_stock_history(self, variant):
        track_stock_change(
            variant_uid=999, product_uid=4242, old_stock=10, new_stock=1,
            product_name="X", variant_name="M")
        assert StockHistory.objects.using(DB).filter(variant_uid="999").count() == 1

    def test_blad_zwraca_none_nie_rzuca(self, db):
        # old_stock/new_stock jako string -> new_stock - old_stock rzuca TypeError
        assert track_stock_change(
            variant_uid=1, product_uid=1, old_stock="a", new_stock="b") is None

    def test_int_variant_uid_w_fallbacku_jest_fail_open(self, db):
        # `productvariant.variant_uid` to varchar; int w raw SQL fallbacku psuje
        # zapytanie ("varchar = integer"), ale funkcja jest fail-open — nie
        # rzuca. (Poprawne wywołanie: variant_uid jako string.)
        assert track_stock_change(
            variant_uid=999, product_uid=999, old_stock=1, new_stock=0) is None


class TestTrackBulkStockChanges:
    def test_zapisuje_wszystkie_zmiany(self, variant):
        created = track_bulk_stock_changes([
            {"variant_uid": 999, "product_uid": 4242, "old_stock": 10, "new_stock": 8,
             "product_name": "X", "variant_name": "M"},
            {"variant_uid": 999, "product_uid": 4242, "old_stock": 8, "new_stock": 2,
             "product_name": "X", "variant_name": "M"},
        ])
        assert len(created) == 2
        assert StockHistory.objects.using(DB).count() == 2
