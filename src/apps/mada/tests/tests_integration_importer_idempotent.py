"""
`importer.upsert_variants` — idempotencja i odporność na wyścig full/partial.

Stan aktualizowany warunkowym UPDATE (`filter(pk=…, stock=old)`), wpis do
StockHistory tylko gdy UPDATE zmienił wiersz. Powtórny import tego samego okna
(redelivery Celery) lub równoległy full+partial nie dublują historii.
"""
from __future__ import annotations

import pytest

from mada.importer import import_product_dict, upsert_variants
from mada.models import MadaProductVariant, StockHistory

from .factories import brand, mada_product, mada_variant, product_dict, variant_dict

pytestmark = pytest.mark.django_db


def test_utworzenie_wariantu_zapisuje_wpis_increase():
    brand(producer_id="110")
    import_product_dict("default", product_dict(producer_id="110",
                        variants=[variant_dict(ean="111", stock=43)]), {})

    rows = list(StockHistory.objects.all())
    assert len(rows) == 1
    assert (rows[0].old_stock, rows[0].new_stock, rows[0].change_type) == (0, 43, "increase")


def test_zmiana_stanu_tworzy_jeden_wpis():
    cache = {}
    pd = product_dict(producer_id="110", variants=[variant_dict(ean="111", stock=43)])
    import_product_dict("default", pd, cache)

    pd2 = {**pd, "variants": [variant_dict(ean="111", stock=10)]}
    import_product_dict("default", pd2, cache)

    assert MadaProductVariant.objects.get(variant_key="111").stock == 10
    assert StockHistory.objects.count() == 2
    last = StockHistory.objects.order_by("-timestamp", "-id").first()
    assert (last.old_stock, last.new_stock, last.change_type) == (43, 10, "decrease")


def test_powtorny_import_tego_samego_okna_nie_dubluje_historii():
    """Redelivery Celery po visibility_timeout: ten sam plik leci drugi raz."""
    cache = {}
    pd = product_dict(producer_id="110", variants=[variant_dict(ean="111", stock=43)])
    import_product_dict("default", pd, cache)
    pd2 = {**pd, "variants": [variant_dict(ean="111", stock=10)]}

    import_product_dict("default", pd2, cache)
    import_product_dict("default", pd2, cache)  # powtórka
    import_product_dict("default", pd2, cache)  # i jeszcze raz

    assert StockHistory.objects.count() == 2  # increase 0→43, decrease 43→10 — bez duplikatów


def test_import_gdy_stan_juz_docelowy_nie_tworzy_wpisu():
    """Równoległy przebieg (full) zdążył ustawić stan docelowy zanim nasz
    (partial) doszedł do UPDATE — warunek `stock=old` nie łapie, 0 wierszy."""
    product = mada_product(api_id=161)
    v = mada_variant(product, variant_key="111", ean="111", stock=5)
    # inny przebieg ustawił już 9
    MadaProductVariant.objects.filter(pk=v.pk).update(stock=9)

    changed = upsert_variants("default", product, [variant_dict(ean="111", stock=9)])

    assert changed == 0
    assert StockHistory.objects.count() == 0
    assert MadaProductVariant.objects.get(pk=v.pk).stock == 9


def test_zmiana_atrybutu_bez_zmiany_stanu_nie_tworzy_wpisu_historii():
    product = mada_product(api_id=161)
    mada_variant(product, variant_key="111", ean="111", stock=5, color="czarny")

    upsert_variants("default", product, [
        variant_dict(ean="111", stock=5, color="grafitowy"),
    ])

    assert StockHistory.objects.count() == 0
    assert MadaProductVariant.objects.get(variant_key="111").color == "grafitowy"
