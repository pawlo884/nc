"""
Integration: `sync_tabu_products._save_product` — zapis produktu + gallery +
wariantów z pełnej odpowiedzi `GET products/{id}` (mappery
`map_api_product_to_model` / `map_api_variant_to_model`).

Używane przez `sync_tabu_new_products` (import nowo znalezionych produktów).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tabu.models import Brand, Category, TabuProduct, TabuProductImage, TabuProductVariant
from tabu.management.commands.sync_tabu_products import Command

from . import factories

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def cmd():
    return Command()


def test_tworzy_produkt_warianty_gallery_i_store_total(cmd):
    api = factories.api_product_detail(
        api_id=5001,
        variants=[
            factories.api_variant_detail(api_id=6001, store=4, color="czarny", size="M"),
            factories.api_variant_detail(api_id=6002, store=6, color="czarny", size="L"),
        ],
        gallery=[
            {"id": 1, "image": "https://tabu.example/1.jpg", "main": True},
            {"id": 2, "image": "https://tabu.example/2.jpg"},
        ],
    )

    cmd._save_product(api)

    p = TabuProduct.objects.get(api_id=5001)
    assert p.name == "Produkt 5001"
    assert p.store_total == 10  # 4 + 6
    assert p.brand.name == "Marko" and p.category is not None
    vs = TabuProductVariant.objects.filter(product=p).order_by("api_id")
    assert [v.api_id for v in vs] == [6001, 6002]
    assert vs[0].color == "czarny" and vs[0].size == "M" and vs[0].store == 4
    assert TabuProductImage.objects.filter(product=p).count() == 2
    assert TabuProductImage.objects.get(product=p, api_image_id=1).is_main is True


def test_ponowny_import_aktualizuje_bez_duplikatow(cmd):
    api = factories.api_product_detail(api_id=5002, variants=[
        factories.api_variant_detail(api_id=6100, store=5)])
    cmd._save_product(api)

    api["name"] = "Nowa nazwa"
    api["variants"][0]["store"] = 2
    api["gallery"] = [{"id": 9, "image": "https://tabu.example/nowe.jpg"}]
    cmd._save_product(api)

    assert TabuProduct.objects.filter(api_id=5002).count() == 1
    p = TabuProduct.objects.get(api_id=5002)
    assert p.name == "Nowa nazwa"
    assert p.store_total == 2
    assert TabuProductVariant.objects.filter(product=p).count() == 1
    assert TabuProductVariant.objects.get(api_id=6100).store == 2
    # gallery podmieniona (delete + recreate)
    imgs = list(TabuProductImage.objects.filter(product=p).values_list("api_image_id", flat=True))
    assert imgs == [9]


def test_reuzywa_istniejacej_marki_i_kategorii(cmd):
    b = Brand.objects.create(brand_id="7", name="Stara nazwa marki")
    c = Category.objects.create(category_id="42", name="Stara kat", path="x")

    cmd._save_product(factories.api_product_detail(api_id=5003))

    assert Brand.objects.count() == 1
    assert Category.objects.count() == 1
    p = TabuProduct.objects.get(api_id=5003)
    assert p.brand_id == b.id and p.category_id == c.id


def test_ceny_wariantu_z_decimal(cmd):
    cmd._save_product(factories.api_product_detail(
        api_id=5004,
        variants=[factories.api_variant_detail(
            api_id=6200, price_net="19.99", price_gross="24.59")]))

    v = TabuProductVariant.objects.get(api_id=6200)
    assert v.price_net == Decimal("19.99") and v.price_gross == Decimal("24.59")
