"""
Integration: `matterhorn1.tasks._bulk_import_products` / `_bulk_update_inventory`
— zapis batcha produktów z ITEMS i aktualizacja stanów z INVENTORY.

Serce pojedynczej strony importu (e2e testuje cały pipeline, tu izolujemy
zachowania brzegowe: brak `creation_date`, ponowny import, nieznany wariant).
"""
from __future__ import annotations

import pytest

from matterhorn1.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
    StockHistory,
)
from matterhorn1.tasks import _bulk_import_products, _bulk_update_inventory

from .factories import api_item, api_variant

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases=["default", "matterhorn1"])]
DB = "matterhorn1"


class TestBulkImportProducts:
    def test_tworzy_produkty_marke_kategorie_warianty_obrazy(self):
        res = _bulk_import_products([
            api_item(id=1, brand="Marko", brand_id="MARKO"),
            api_item(id=2, brand="Self", brand_id="SELF"),
        ])
        assert res["status"] == "success"
        assert res["imported_count"] == 2
        assert Product.objects.using(DB).count() == 2
        assert Brand.objects.using(DB).count() == 2
        assert Category.objects.using(DB).count() >= 1
        assert ProductVariant.objects.using(DB).count() == 2
        assert ProductImage.objects.using(DB).count() == 2

    def test_pomija_element_bez_creation_date(self):
        item = api_item(id=10)
        item["creation_date"] = None
        res = _bulk_import_products([item, api_item(id=11)])
        assert res["imported_count"] == 1
        assert set(Product.objects.using(DB).values_list("product_uid", flat=True)) == {11}

    def test_pomija_element_bez_id(self):
        item = api_item()
        del item["id"]
        res = _bulk_import_products([item])
        assert res["imported_count"] == 0
        assert Product.objects.using(DB).count() == 0

    def test_ponowny_import_aktualizuje_bez_duplikatu(self):
        _bulk_import_products([api_item(id=42, name="Stara")])
        res = _bulk_import_products([api_item(id=42, name="Nowa")])

        assert res["status"] == "success"
        assert Product.objects.using(DB).filter(product_uid=42).count() == 1
        assert Product.objects.using(DB).get(product_uid=42).name == "Nowa"


class TestBulkUpdateInventory:
    @pytest.fixture
    def variant(self):
        brand = Brand.objects.using(DB).create(brand_id="B", name="B")
        cat = Category.objects.using(DB).create(category_id="C", name="C")
        product = Product.objects.using(DB).create(
            product_uid=500, name="P", brand=brand, category=cat)
        return ProductVariant.objects.using(DB).create(
            product=product, variant_uid="8001", name="M", stock=10)

    def test_aktualizuje_stan_i_pisze_historie(self, variant):
        _bulk_update_inventory([
            {"id": 500, "inventory": [{"variant_uid": "8001", "stock": "3"}]},
        ])
        variant.refresh_from_db()
        assert variant.stock == 3
        assert StockHistory.objects.using(DB).filter(variant_uid="8001").count() == 1

    def test_brak_zmiany_stanu_nie_pisze_historii(self, variant):
        _bulk_update_inventory([
            {"id": 500, "inventory": [{"variant_uid": "8001", "stock": "10"}]},
        ])
        variant.refresh_from_db()
        assert variant.stock == 10
        assert StockHistory.objects.using(DB).count() == 0

    def test_nieznany_wariant_jest_pomijany(self, variant):
        _bulk_update_inventory([
            {"id": 500, "inventory": [{"variant_uid": "99999", "stock": "0"}]},
        ])
        variant.refresh_from_db()
        assert variant.stock == 10

    def test_nieznany_produkt_jest_pomijany(self, db):
        # nie rzuca mimo braku produktu 12345
        _bulk_update_inventory([
            {"id": 12345, "inventory": [{"variant_uid": "1", "stock": "5"}]},
        ])
