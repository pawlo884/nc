"""
Unit: `matterhorn1.tasks._prepare_product_create` / `_prepare_product_update`
— budowa obiektu `Product` z elementu B2BAPI/ITEMS (marka/kategoria przez
get_or_create, konwersje typów, doczepienie wariantów/obrazów/szczegółów).

DB potrzebne bo get_or_create marki i kategorii zapisuje wiersze.
"""
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

import pytest

from matterhorn1.models import Brand, Category, Product
from matterhorn1.tasks import _prepare_product_create, _prepare_product_update

from .factories import api_item, api_variant

pytestmark = [pytest.mark.unit, pytest.mark.django_db(databases=["default", "matterhorn1"])]
DB = "matterhorn1"


class TestPrepareProductCreate:
    def test_mapuje_podstawowe_pola(self):
        p = _prepare_product_create(api_item(id=7001, name="Kostium Ada", color="czarny"))
        assert p.product_uid == 7001
        assert p.name == "Kostium Ada"
        assert p.color == "czarny"
        assert p.pk is None  # nie zapisany

    def test_zaklada_marke_i_kategorie(self):
        _prepare_product_create(api_item(brand_id="MARKO", brand="Marko",
                                         category_id="100", category_name="Bikini"))
        assert Brand.objects.using(DB).filter(brand_id="MARKO", name="Marko").exists()
        assert Category.objects.using(DB).filter(category_id="100", name="Bikini").exists()

    def test_reuzywa_istniejacej_marki(self):
        Brand.objects.using(DB).create(brand_id="MARKO", name="Marko")
        _prepare_product_create(api_item(brand_id="MARKO", brand="Inna Nazwa"))
        # get_or_create po brand_id — nazwa z defaults nie nadpisuje istniejącej
        assert Brand.objects.using(DB).filter(brand_id="MARKO").count() == 1
        assert Brand.objects.using(DB).get(brand_id="MARKO").name == "Marko"

    @pytest.mark.parametrize("raw,expected", [
        ("true", True), ("false", False), ("1", True), ("yes", True),
        (True, True), (False, False),
    ])
    def test_konwersja_active(self, raw, expected):
        assert _prepare_product_create(api_item(active=raw)).active is expected

    @pytest.mark.parametrize("raw,expected", [
        ("Y", True), ("YES", True), ("N", False), ("", False), (False, False),
    ])
    def test_konwersja_new_collection(self, raw, expected):
        assert _prepare_product_create(api_item(new_collection=raw)).new_collection is expected

    def test_parsuje_creation_date(self):
        p = _prepare_product_create(api_item(creation_date="2026-01-15T10:00:00"))
        assert p.creation_date == datetime(2026, 1, 15, 10, 0, tzinfo=dt_timezone.utc)

    def test_warianty_konwersja_stock(self):
        item = api_item(variants=[
            api_variant(variant_uid=1, stock="5"),
            api_variant(variant_uid=2, stock="abc"),   # niepoprawny -> 0
            api_variant(variant_uid=3, stock=None),    # brak -> 0
        ])
        vs = _prepare_product_create(item)._variants_to_create
        assert [v["stock"] for v in vs] == [5, 0, 0]

    def test_obrazy_dostaja_order(self):
        item = api_item(images=["https://a.jpg", "https://b.jpg", "https://c.jpg"])
        imgs = _prepare_product_create(item)._images_to_create
        assert [i["order"] for i in imgs] == [0, 1, 2]
        assert imgs[1]["image_url"] == "https://b.jpg"

    def test_szczegoly_tylko_gdy_sa_pola(self):
        bez = _prepare_product_create(api_item())
        assert not hasattr(bez, "_details_to_create")

        z = _prepare_product_create(api_item(weight="0.25", size_table="tabela"))
        assert z._details_to_create["weight"] == "0.25"
        assert z._details_to_create["size_table"] == "tabela"


class TestPrepareProductUpdate:
    def test_aktualizuje_istniejacy_produkt(self):
        brand = Brand.objects.using(DB).create(brand_id="B", name="B")
        cat = Category.objects.using(DB).create(category_id="C", name="C")
        product = Product.objects.using(DB).create(
            product_uid=8001, name="Stara nazwa", brand=brand, category=cat, active=True)

        _prepare_product_update(product, api_item(id=8001, name="Nowa nazwa", active="false"))

        assert product.name == "Nowa nazwa"
        assert product.active is False

    def test_brak_name_w_evencie_zachowuje_stara(self):
        brand = Brand.objects.using(DB).create(brand_id="B", name="B")
        cat = Category.objects.using(DB).create(category_id="C", name="C")
        product = Product.objects.using(DB).create(
            product_uid=8002, name="Zostaje", brand=brand, category=cat)

        item = api_item(id=8002)
        del item["name"]
        _prepare_product_update(product, item)

        assert product.name == "Zostaje"
