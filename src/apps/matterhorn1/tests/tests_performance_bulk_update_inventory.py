"""
Regresja wydajności: `_bulk_update_inventory` musi skalować się w stałej
(małej) liczbie zapytań SQL na stronę, nie liniowo z liczbą produktów/
wariantów (ten sam N+1 wzorzec co #223, tu w kroku INVENTORY).

Przed fixem: query per produkt (`Product.objects.get`), query per wariant
(`ProductVariant.objects.get`) i `StockHistory.objects.create()` per zmieniony
wariant - strona 1000 pozycji = do ~3000 zapytań. Ten test aktualizuje stan
20 wariantów (z czego połowa faktycznie się zmienia) i pilnuje że liczba
zapytań zostaje płasko-mała, niezależna od N.
"""
from __future__ import annotations

import pytest
from django.db import connections
from django.test.utils import CaptureQueriesContext

from matterhorn1.models import Brand, Category, Product, ProductVariant, StockHistory
from matterhorn1.tasks import _bulk_update_inventory

from .factories import inventory_record

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases=["default", "matterhorn1"])]
DB = "matterhorn1"

N_PRODUCTS = 20
# Płaski budżet: pre-fetch produktów + wariantów (2 SELECT-y) + bulk_update
# wariantów + bulk_create historii + BEGIN/COMMIT. Rośnie z liczbą modeli
# dotkniętych, nie z N.
MAX_QUERIES = 15


@pytest.fixture
def products_with_variants():
    brand = Brand.objects.using(DB).create(brand_id="PERF", name="Perf Brand")
    cat = Category.objects.using(DB).create(category_id="PERFCAT", name="Perf Category")
    variants = []
    for i in range(N_PRODUCTS):
        product = Product.objects.using(DB).create(
            product_uid=40000 + i, name=f"P{i}", brand=brand, category=cat)
        variants.append(ProductVariant.objects.using(DB).create(
            product=product, variant_uid=str(50000 + i), name="M", stock=10))
    return variants


def _make_inventory(variants):
    # Co drugi wariant zmienia stan (10 -> 3), reszta bez zmiany (10 -> 10).
    return [
        inventory_record(
            item_id=v.product.product_uid,
            variants=[{"variant_uid": v.variant_uid, "stock": 3 if i % 2 == 0 else 10}],
        )
        for i, v in enumerate(variants)
    ]


def test_zapytania_nie_rosna_liniowo_z_liczba_wariantow(products_with_variants):
    inventory_data = _make_inventory(products_with_variants)

    with CaptureQueriesContext(connections[DB]) as ctx:
        updated_count = _bulk_update_inventory(inventory_data)

    assert updated_count == N_PRODUCTS // 2
    assert len(ctx.captured_queries) < MAX_QUERIES, (
        f"{len(ctx.captured_queries)} zapytań dla {N_PRODUCTS} wariantów — "
        f"podejrzenie N+1 (query/create per element zamiast batcha)"
    )
    assert StockHistory.objects.using(DB).count() == N_PRODUCTS // 2


def test_zapytania_przy_ponownej_aktualizacji_tez_plaskie(products_with_variants):
    inventory_data = _make_inventory(products_with_variants)
    _bulk_update_inventory(inventory_data)

    with CaptureQueriesContext(connections[DB]) as ctx:
        updated_count = _bulk_update_inventory(inventory_data)

    # Drugi przebieg z tymi samymi danymi: stan już zaktualizowany, więc
    # nic się nie zmienia, ale pre-fetch nadal leci (2 SELECT-y + brak
    # bulk_update/bulk_create bo nic do zapisania).
    assert updated_count == 0
    assert len(ctx.captured_queries) < MAX_QUERIES
