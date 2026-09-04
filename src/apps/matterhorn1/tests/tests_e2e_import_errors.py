"""
E2E: przypadki brzegowe / błędy pipeline'u importu Matterhorn.

Bazuje na infrastrukturze z tests_e2e_import.py (mock `responses`,
`prior_items_sync`, `no_sleep`).
"""
from __future__ import annotations

import pytest

from matterhorn1.models import ApiSyncLog, Product, ProductVariant
from matterhorn1.tasks import full_import_and_update

from .mock_matterhorn import mock_inventory, mock_items

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(databases=["default", "matterhorn1"])]


def test_chwilowy_500_na_stronie_2_odzyskuje_bez_duplikatu(
    matterhorn_api, mocked_responses, prior_items_sync, api_item
):
    # strona 1: 1 produkt; strona 2: 500 raz, potem pusto (koniec)
    mock_items(mocked_responses, [[api_item(id=3001)], []],
               transient_errors={2: [500]})
    mock_inventory(mocked_responses, [[]])

    result = full_import_and_update(auto_continue=False, dry_run=False)

    assert result["status"] == "success"
    assert Product.objects.using("matterhorn1").filter(product_uid=3001).count() == 1


def test_blokada_rownoleglego_importu_zwraca_skipped(
    matterhorn_api, prior_items_sync, monkeypatch
):
    monkeypatch.setattr("matterhorn1.tasks.cache.add", lambda *a, **k: False)

    result = full_import_and_update(auto_continue=False, dry_run=False)

    assert result["status"] == "skipped"
    assert result["reason"] == "already_running"
    assert Product.objects.using("matterhorn1").count() == 0


def test_wznowienie_od_przerwanej_strony(
    matterhorn_api, mocked_responses, prior_items_sync, api_item
):
    # poprzedni przerwany import ITEMS zatrzymał się na stronie 3 (świeży, < 24 h)
    interrupted = ApiSyncLog.objects.using("matterhorn1").create(
        sync_type="items_import", status="error")
    ApiSyncLog.objects.using("matterhorn1").filter(pk=interrupted.pk).update(current_page=3)

    # strona 3 (idx 2) ma produkt, strona 4 pusta = koniec
    mock_items(mocked_responses, [[], [], [api_item(id=4001)], []])
    mock_inventory(mocked_responses, [[]])

    full_import_and_update(auto_continue=False, dry_run=False)

    item_pages = [int(c.request.params["page"]) for c in mocked_responses.calls
                  if "/B2BAPI/ITEMS/?" in c.request.url]
    assert item_pages[0] == 3  # start od przerwanej strony, nie od 1
    assert Product.objects.using("matterhorn1").filter(product_uid=4001).exists()


def test_pusta_odpowiedz_na_stronie_1_konczy_bez_produktow(
    matterhorn_api, mocked_responses, prior_items_sync
):
    mock_items(mocked_responses, [[]])
    mock_inventory(mocked_responses, [[]])

    result = full_import_and_update(auto_continue=False, dry_run=False)

    assert result["status"] == "success"
    assert Product.objects.using("matterhorn1").count() == 0


def test_produkt_bez_wariantow_i_obrazow_importuje_sie(
    matterhorn_api, mocked_responses, prior_items_sync, api_item
):
    item = api_item(id=5501, variants=[], images=[])
    mock_items(mocked_responses, [[item], []])
    mock_inventory(mocked_responses, [[]])

    full_import_and_update(auto_continue=False, dry_run=False)

    assert Product.objects.using("matterhorn1").filter(product_uid=5501).exists()
    assert ProductVariant.objects.using("matterhorn1").filter(product__product_uid=5501).count() == 0
