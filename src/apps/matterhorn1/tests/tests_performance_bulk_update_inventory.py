"""
`_bulk_update_inventory`:
- pre-fetch produktów/wariantów batchem (nie query per element - wzorzec N+1
  jak #223), więc liczba SELECT-ów nie rośnie z liczbą wariantów w danych,
  tylko warunkowy UPDATE per FAKTYCZNIE zmieniony wariant (w praktyce garstka);
- idempotencja: drugi run z tymi samymi danymi nie powiela wpisów StockHistory
  (regresja na duplikaty przy nakładających się runach importu).
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


def _inventory(variants, changed_idx):
    """INVENTORY dla wszystkich wariantów; te z `changed_idx` dostają stock=3,
    reszta zostaje na 10 (bez zmiany)."""
    return [
        inventory_record(
            item_id=v.product.product_uid,
            variants=[{"variant_uid": v.variant_uid, "stock": 3 if i in changed_idx else 10}],
        )
        for i, v in enumerate(variants)
    ]


def test_liczba_zapytan_skaluje_sie_ze_zmienionymi_nie_z_wszystkimi(products_with_variants):
    # 20 wariantów w danych, ale tylko 2 faktycznie się zmieniają.
    data = _inventory(products_with_variants, changed_idx={0, 1})

    with CaptureQueriesContext(connections[DB]) as ctx:
        updated = _bulk_update_inventory(data)

    assert updated == 2
    assert StockHistory.objects.using(DB).count() == 2
    # 2 SELECT-y pre-fetch + 2 warunkowe UPDATE-y + 1 bulk_create.
    # Kluczowe: NIE ~20 (query per wariant w danych).
    assert len(ctx.captured_queries) <= 8, (
        f"{len(ctx.captured_queries)} zapytań dla 20 wariantów w danych (2 zmienione) — "
        f"podejrzenie query per element"
    )


def test_drugi_run_z_tymi_samymi_danymi_nie_powiela_historii(products_with_variants):
    data = _inventory(products_with_variants, changed_idx={0, 1, 2})
    assert _bulk_update_inventory(data) == 3
    assert StockHistory.objects.using(DB).count() == 3

    with CaptureQueriesContext(connections[DB]) as ctx:
        updated = _bulk_update_inventory(data)

    # Stany już zaktualizowane -> nic do zrobienia, żadnego nowego wpisu.
    assert updated == 0
    assert StockHistory.objects.using(DB).count() == 3
    # Same pre-fetch SELECT-y, bez UPDATE-ów i bez bulk_create.
    assert len(ctx.captured_queries) <= 4


def test_stan_juz_docelowy_w_dbie_nie_zapisuje_historii(products_with_variants):
    """Inny run zdążył już zastosować tę zmianę - pre-fetch widzi stan
    docelowy, więc nic nie robimy i nie ma wpisu (idempotencja)."""
    variants = products_with_variants
    data = _inventory(variants, changed_idx={0})

    ProductVariant.objects.using(DB).filter(pk=variants[0].pk).update(stock=3)

    updated = _bulk_update_inventory(data)

    assert updated == 0
    assert StockHistory.objects.using(DB).count() == 0
