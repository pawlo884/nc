"""
Integration: `StockHistoryAdmin` changelist — regresja wydajności (N+1 przy
budowaniu linków do produktów, bo `product_uid` nie jest FK) i filtr
`product_uid` przez pole tekstowe zamiast listy ~dziesiątek tysięcy wartości.
"""
from __future__ import annotations

import pytest
from django.db import connections
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.db_routers import _get_matterhorn1_db
from matterhorn1.models import Brand, Product, StockHistory

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases="__all__")]

DB = _get_matterhorn1_db()


def _mk_history(n, *, with_product=True):
    brand = Brand.objects.using(DB).create(brand_id="B", name="B")
    rows = []
    for i in range(n):
        uid = 700000 + i
        if with_product:
            Product.objects.using(DB).create(product_uid=uid, name=f"P{i}", brand=brand)
        rows.append(StockHistory(
            variant_uid=str(800000 + i), product_uid=uid, product_name=f"P{i}",
            variant_name="M", old_stock=5, new_stock=3, stock_change=-2,
            change_type="decrease"))
    StockHistory.objects.using(DB).bulk_create(rows)


def test_changelist_liczba_zapytan_nie_rosnie_z_liczba_wierszy(admin_client):
    _mk_history(30)
    url = reverse("admin:matterhorn1_stockhistory_changelist")

    with CaptureQueriesContext(connections[DB]) as ctx:
        resp = admin_client.get(url)

    assert resp.status_code == 200
    # Przed fixem: ~1 zapytanie na wiersz (product_uid_link -> Product.objects.get).
    # Po fixie: pk produktu z adnotacji (jedno skorelowane podzapytanie),
    # reszta to stały narzut changelist/auth.
    assert len(ctx.captured_queries) < 10, (
        f"{len(ctx.captured_queries)} zapytań (matterhorn1) na changelist z 30 wierszami — podejrzenie N+1"
    )


def test_link_do_produktu_gdy_produkt_istnieje(admin_client):
    _mk_history(1, with_product=True)
    url = reverse("admin:matterhorn1_stockhistory_changelist")
    resp = admin_client.get(url)
    assert resp.status_code == 200
    product = Product.objects.using(DB).get(product_uid=700000)
    expected = reverse("admin:matterhorn1_product_change", args=[product.pk])
    assert expected.encode() in resp.content


def test_bez_produktu_link_to_sam_uid_bez_query(admin_client):
    _mk_history(1, with_product=False)
    url = reverse("admin:matterhorn1_stockhistory_changelist")
    resp = admin_client.get(url)
    assert resp.status_code == 200
    assert b"700000" in resp.content


def test_filtr_product_uid_zaweza_do_dokladnej_wartosci(admin_client):
    _mk_history(5)
    url = reverse("admin:matterhorn1_stockhistory_changelist")

    resp = admin_client.get(url, {"product_uid": "700002"})

    assert resp.status_code == 200
    cl = resp.context["cl"]
    assert cl.result_count == 1
    assert cl.result_list[0].product_uid == 700002


def test_filtr_product_uid_niepoprawna_wartosc_daje_pusto(admin_client):
    _mk_history(3)
    url = reverse("admin:matterhorn1_stockhistory_changelist")
    resp = admin_client.get(url, {"product_uid": "abc"})
    assert resp.status_code == 200
    assert resp.context["cl"].result_count == 0
