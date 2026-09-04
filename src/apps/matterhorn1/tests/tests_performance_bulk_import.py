"""
Regresja wydajności: `_bulk_import_products` musi skalować się w stałej
(małej) liczbie zapytań SQL na stronę, nie liniowo z liczbą produktów/
wariantów/obrazów.

Przed fixem (patrz docs/TESTING.md / issue o wolnym items_import):
6 miejsc robiło query per element (produkt/marka/kategoria/wariant/
szczegóły/obraz) - strona 1000 pozycji = ~8500 zapytań. Na dev (baza za
tunelem SSH, ~30 ms/zapytanie) to ~4 minuty tylko na same round-tripy.

Ten test importuje 20 nowych produktów (2 warianty + 2 obrazy każdy = 80
wariantów, 40 obrazów) i pilnuje że liczba zapytań zostaje płasko-mała,
niezależna od N - żeby ktoś przypadkiem nie wrócił do get()/exists()
w pętli per element.
"""
from __future__ import annotations

import pytest
from django.db import connections
from django.test.utils import CaptureQueriesContext

from matterhorn1.tasks import _bulk_import_products

from .factories import api_item, api_variant

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases=["default", "matterhorn1"])]

N_PRODUCTS = 20
# Rozsądny płaski budżet: pre-fetch produktów/marek/kategorii/wariantów/
# obrazów (kilka SELECT-ów) + bulk_create/bulk_update (kilka INSERT/UPDATE)
# + BEGIN/COMMIT transakcji. Rośnie z liczbą modeli dotkniętych, nie z N.
MAX_QUERIES = 30


def _make_items(n):
    items = []
    for i in range(n):
        items.append(api_item(
            id=20000 + i,
            brand_id="PERF", brand="Perf Brand",
            category_id="PERFCAT", category_name="Perf Category",
            variants=[
                api_variant(variant_uid=30000 + i * 2, stock="5"),
                api_variant(variant_uid=30000 + i * 2 + 1, stock="3"),
            ],
            images=[f"https://perf.example/{i}_1.jpg", f"https://perf.example/{i}_2.jpg"],
        ))
    return items


def test_zapytania_nie_rosna_liniowo_z_liczba_produktow():
    items = _make_items(N_PRODUCTS)

    with CaptureQueriesContext(connections["matterhorn1"]) as ctx:
        result = _bulk_import_products(items)

    assert result["status"] == "success"
    assert result["imported_count"] == N_PRODUCTS
    assert len(ctx.captured_queries) < MAX_QUERIES, (
        f"{len(ctx.captured_queries)} zapytań dla {N_PRODUCTS} produktów — "
        f"podejrzenie N+1 (query per element zamiast batcha)"
    )


def test_zapytania_przy_ponownym_imporcie_tez_plaskie():
    """Druga strona z tymi samymi product_uid (ścieżka update, nie create)."""
    items = _make_items(N_PRODUCTS)
    _bulk_import_products(items)

    with CaptureQueriesContext(connections["matterhorn1"]) as ctx:
        result = _bulk_import_products(items)

    assert result["status"] == "success"
    assert len(ctx.captured_queries) < MAX_QUERIES
