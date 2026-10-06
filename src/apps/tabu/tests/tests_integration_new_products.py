"""
Integration: `sync_tabu_new_products` — persistentny `check_range` (rośnie o 1
co run, zeruje po znalezieniu nowego produktu).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.management import call_command

from tabu.models import ApiSyncLog
from tabu.management.commands.sync_tabu_products import Command as SyncProductsCommand

from . import factories
from .mock_tabu import mock_product_detail

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _run(**extra):
    call_command("sync_tabu_new_products", "--api-url", "https://tabu.test",
                 "--api-key", "test-key", "--delay", "0", **extra)


@pytest.fixture(autouse=True)
def _no_real_save():
    with patch.object(SyncProductsCommand, "_save_product") as m:
        yield m


def test_wszystkie_404_check_range_rosnie(tabu_api, mocked_responses):
    factories.tabu_product(api_id=100)  # max api_id = 100
    mock_product_detail(mocked_responses, tabu_api, {})  # wszystko 404

    _run()

    log = ApiSyncLog.objects.filter(sync_type="products_new_check").latest("started_at")
    assert log.status == "completed"
    assert log.raw_response["check_range"] == 1
    assert log.raw_response["new_products_imported"] == 0


def test_check_range_kontynuuje_z_poprzedniego_runu(tabu_api, mocked_responses):
    factories.tabu_product(api_id=200)
    ApiSyncLog.objects.create(
        sync_type="products_new_check", status="completed",
        raw_response={"check_range": 3})
    mock_product_detail(mocked_responses, tabu_api, {})

    _run()

    log = ApiSyncLog.objects.filter(sync_type="products_new_check").latest("started_at")
    assert log.raw_response["check_range"] == 4  # 3 + 1


def test_znaleziony_produkt_importuje_i_zeruje_check_range(tabu_api, mocked_responses, _no_real_save):
    factories.tabu_product(api_id=300)
    ApiSyncLog.objects.create(
        sync_type="products_new_check", status="completed",
        raw_response={"check_range": 1})
    # #301 istnieje, #302 już 404 → koniec serii
    mock_product_detail(mocked_responses, tabu_api, {301: {"id": 301, "symbol": "NEW"}})

    _run()

    _no_real_save.assert_called()  # zaimportowano #301
    log = ApiSyncLog.objects.filter(sync_type="products_new_check").latest("started_at")
    assert log.raw_response["check_range"] == 0  # reset
    assert log.raw_response["new_products_imported"] >= 1
