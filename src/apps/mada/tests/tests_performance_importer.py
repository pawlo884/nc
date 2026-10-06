"""
`importer` — brak N+1 przy imporcie masowym:
- `brand_cache` (load_brand_cache) zdejmuje zapytanie o markę per produkt;
- historia stanów leci jednym `bulk_create`, nie INSERT per zmieniony wariant.
"""
from __future__ import annotations

import pytest
from django.db import connections
from django.test.utils import CaptureQueriesContext

from mada.importer import import_product_dict, load_brand_cache, upsert_variants
from mada.models import StockHistory

from .factories import brand, mada_product, product_dict, variant_dict

pytestmark = pytest.mark.django_db
DB = "default"


def _count(ctx, needle):
    return sum(1 for q in ctx.captured_queries if needle in q["sql"])


def test_brand_cache_zdejmuje_zapytanie_o_marke_per_produkt():
    brand(producer_id="110", name="Gatta")
    cache = load_brand_cache(DB)
    cat_cache = {}

    with CaptureQueriesContext(connections[DB]) as ctx:
        for i in range(10):
            import_product_dict(DB, product_dict(api_id=5000 + i, producer_id="110"),
                                cat_cache, cache)

    # z brand_cache: zero SELECT-ów po mada_brand w pętli importu
    assert _count(ctx, 'FROM "mada_brand"') == 0


def test_bez_brand_cache_jest_nplus1():
    brand(producer_id="110", name="Gatta")
    cat_cache = {}

    with CaptureQueriesContext(connections[DB]) as ctx:
        for i in range(10):
            import_product_dict(DB, product_dict(api_id=6000 + i, producer_id="110"), cat_cache)

    assert _count(ctx, 'FROM "mada_brand"') >= 10


def test_historia_stanow_zapisywana_batchem():
    product = mada_product(api_id=161)
    variants = [variant_dict(ean=f"E{i}", stock=i + 1) for i in range(15)]

    with CaptureQueriesContext(connections[DB]) as ctx:
        changed = upsert_variants(DB, product, variants)

    assert changed == 15
    assert StockHistory.objects.count() == 15
    # jeden INSERT zbiorczy do historii, nie 15
    assert _count(ctx, 'INSERT INTO "mada_stock_history"') == 1
