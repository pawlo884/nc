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


def test_trwaly_500_na_stronie_przerywa_import_zamiast_petlic(
    matterhorn_api, mocked_responses, prior_items_sync, api_item
):
    """#214: przed fixem `page` rosło tylko po sukcesie, więc trwały 5xx =
    nieskończona pętla aż do soft-timeoutu Celery. Teraz: po wyczerpaniu
    prób na stronie import kończy się błędem, current_page zachowany."""
    # strona 1 OK, strona 2 zawsze 500 (więcej niż 10 prób retry).
    # INVENTORY nie jest wołane — błąd ITEMS przerywa przed tym krokiem.
    mock_items(mocked_responses, [[api_item(id=3100)], []],
               transient_errors={2: [500] * 15})

    result = full_import_and_update(auto_continue=False, dry_run=False)

    assert result["status"] == "error"

    assert Product.objects.using("matterhorn1").filter(product_uid=3100).count() == 1
    last = ApiSyncLog.objects.using("matterhorn1").filter(
        sync_type="items_import").order_by("-started_at").first()
    assert last.status == "error"
    assert last.current_page == 2  # zachowane do wznowienia


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
    # Strony 3+ lecą kilka naraz (pipeline, patrz _import_products_from_items),
    # więc kolejność ODPOWIEDZI HTTP nie jest gwarantowana - liczy się, że
    # nigdy nie zeszliśmy poniżej checkpointu (start od 3, nie od 1).
    assert min(item_pages) == 3
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
