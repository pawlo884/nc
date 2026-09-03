"""
E2E: pełny pipeline importu Matterhorn z zamockowanym HTTP (`responses`).

`full_import_and_update` → B2BAPI/ITEMS + B2BAPI/ITEMS/INVENTORY (mock) →
asercje stanu w bazie matterhorn1.

Kolejne fazy (docs/TESTING.md): import → mpd_create → linkowanie po EAN,
scenariusze błędów (500 na stronie 2, blokada równoległa).
"""
from __future__ import annotations

import pytest

from matterhorn1.models import (
    ApiSyncLog,
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
)
from matterhorn1.tasks import full_import_and_update

from .mock_matterhorn import mock_inventory, mock_items

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(databases=["default", "matterhorn1"])]


def test_full_import_tworzy_produkty_marki_kategorie_warianty_obrazy(
    matterhorn_api, mocked_responses, prior_items_sync, api_item
):
    it1 = api_item(id=5001, brand="Marko", brand_id="MARKO",
                   category_name="Bikini", category_id="100")
    it2 = api_item(id=5002, brand="Self", brand_id="SELF",
                   category_name="Jednoczęściowe", category_id="200")
    mock_items(mocked_responses, [[it1, it2], []])   # str. 1: 2 produkty, str. 2: koniec
    mock_inventory(mocked_responses, [[]])

    result = full_import_and_update(auto_continue=False, dry_run=False)

    # `full_import_and_update` zwraca 'success' po czystym przejściu; status
    # 'completed' ląduje w ApiSyncLog (asercja niżej).
    assert result["status"] == "success"
    assert set(Product.objects.using("matterhorn1").values_list("product_uid", flat=True)) == {5001, 5002}
    assert set(Brand.objects.using("matterhorn1").values_list("name", flat=True)) == {"Marko", "Self"}
    assert set(Category.objects.using("matterhorn1").values_list("name", flat=True)) == {"Bikini", "Jednoczęściowe"}

    p1 = Product.objects.using("matterhorn1").get(product_uid=5001)
    assert p1.name == "Kostium 5001"
    assert p1.brand.name == "Marko"
    assert ProductVariant.objects.using("matterhorn1").filter(product=p1).count() == 1
    assert ProductImage.objects.using("matterhorn1").filter(product=p1).count() == 1

    assert ApiSyncLog.objects.using("matterhorn1").filter(
        sync_type="items_import", status="completed").exists()


def test_full_import_bez_wczesniejszego_synca_nie_startuje(matterhorn_api, mocked_responses, db):
    """Brak `ApiSyncLog` → `_get_last_items_update_time()` = None → import
    kończy się błędem, żaden produkt nie powstaje, żaden request nie leci."""
    result = full_import_and_update(auto_continue=False, dry_run=False)

    assert result["status"] != "completed"
    assert Product.objects.using("matterhorn1").count() == 0
    assert len(mocked_responses.calls) == 0


def test_full_import_aktualizuje_stan_z_inventory(
    matterhorn_api, mocked_responses, prior_items_sync, api_item, api_variant, inventory_record
):
    variant = api_variant(variant_uid=77001, stock="5", ean="5901111111111")
    item = api_item(id=6001, variants=[variant])
    mock_items(mocked_responses, [[item], []])
    # INVENTORY zmienia stan 5 -> 0 (ITEMS nie pokazuje zer, INVENTORY tak)
    mock_inventory(mocked_responses, [[inventory_record(6001, [{"variant_uid": 77001, "stock": 0}])], []])

    full_import_and_update(auto_continue=False, dry_run=False)

    v = ProductVariant.objects.using("matterhorn1").get(variant_uid=77001)
    assert v.stock == 0
