"""
`sync_mada_full` — pełny import: pobranie najnowszego pliku full z manifestu,
import produktów, wygaszenie nieobecnych, log ApiSyncLog.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
import responses
from django.core.management import call_command

from mada.models import ApiSyncLog, MadaProduct, MadaProductVariant, StockHistory

from . import mock_mada
from .factories import mada_product

pytestmark = pytest.mark.django_db

PRODUCERS = {"110": "Gatta", "43": "Golden Lady"}


@pytest.fixture
def rsps():
    with responses.RequestsMock() as r:
        yield r


def _manifest_and_file(rsps, file_name, products):
    mock_mada.register_manifest(rsps, [
        {"name": file_name, "date": "2026-01-15 00:01:00", "type": "full"},
    ])
    mock_mada.register_file(rsps, file_name, PRODUCERS, products)


def test_pelny_import_tworzy_produkty_warianty_i_log(mada_api, rsps):
    _manifest_and_file(rsps, "2026-01-15-full", [
        mock_mada.simple_product(161, ean="111", stock=5),
        mock_mada.simple_product(162, producer_id="43", ean="222", stock=0),
    ])

    call_command("sync_mada_full")

    assert MadaProduct.objects.count() == 2
    assert MadaProductVariant.objects.get(variant_key="111").stock == 5
    log = ApiSyncLog.objects.get(sync_type="full_import")
    assert log.status == "completed"
    assert log.products_processed == 2
    assert log.products_created == 2


def test_deaktywuje_produkty_nieobecne_w_feedzie(mada_api, rsps):
    mada_product(api_id=999, name="Znika z oferty", is_active=True)
    _manifest_and_file(rsps, "2026-01-15-full", [mock_mada.simple_product(161, ean="111")])

    call_command("sync_mada_full")

    assert MadaProduct.objects.get(api_id=999).is_active is False
    assert MadaProduct.objects.get(api_id=161).is_active is True


def test_blad_jednego_produktu_nie_przerywa_importu(mada_api, rsps):
    _manifest_and_file(rsps, "2026-01-15-full", [
        mock_mada.simple_product(161, ean="111"),
        mock_mada.simple_product(162, ean="222"),
        mock_mada.simple_product(163, ean="333"),
    ])
    from mada import importer as mada_importer

    def flaky(db, pd, cat_cache, brand_cache=None):
        if pd["api_id"] == 162:
            raise RuntimeError("boom")
        return mada_importer.import_product_dict(db, pd, cat_cache, brand_cache)

    with patch("mada.management.commands.sync_mada_full.import_product_dict", side_effect=flaky):
        call_command("sync_mada_full")

    assert MadaProduct.objects.filter(api_id__in=[161, 163]).count() == 2
    assert not MadaProduct.objects.filter(api_id=162).exists()
    log = ApiSyncLog.objects.get(sync_type="full_import")
    assert log.status == "completed"
    assert log.products_failed == 1


def test_wymuszony_plik_pomija_manifest_full(mada_api, rsps):
    mock_mada.register_file(rsps, "reczny-full", PRODUCERS,
                            [mock_mada.simple_product(161, ean="111")])

    call_command("sync_mada_full", file="reczny-full")

    assert ApiSyncLog.objects.get(sync_type="full_import").file_name == "reczny-full"
    assert MadaProduct.objects.count() == 1


def test_powtorny_pelny_import_nie_dubluje_historii(mada_api):
    """Idempotencja przez komendę (regresja na nakładające się runy / redelivery)."""
    def run(stock):
        with responses.RequestsMock() as rsps:
            _manifest_and_file(rsps, "2026-01-15-full",
                               [mock_mada.simple_product(161, ean="111", stock=stock)])
            call_command("sync_mada_full")

    run(5)          # increase 0→5
    run(2)          # decrease 5→2
    run(2)          # bez zmiany
    run(2)

    assert StockHistory.objects.count() == 2
