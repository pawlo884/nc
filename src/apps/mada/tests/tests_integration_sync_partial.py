"""
`sync_mada_partial` — import przyrostowy: kursor = najwyższy `file_name` wśród
ukończonych logów `partial_import`; przetwarza wszystkie nowsze pliki.
"""
from __future__ import annotations

import pytest
import responses
from django.core.management import call_command

from mada.models import ApiSyncLog, MadaProduct, StockHistory

from . import mock_mada

pytestmark = pytest.mark.django_db

PRODUCERS = {"110": "Gatta"}


@pytest.fixture
def rsps():
    with responses.RequestsMock() as r:
        yield r


def test_brak_nowych_plikow_to_noop(mada_api, rsps):
    mock_mada.register_manifest(rsps, [
        {"name": "2026-01-15_090000", "date": "2026-01-15 09:00:00", "type": "partial"},
    ])
    ApiSyncLog.objects.create(
        sync_type="partial_import", status="completed", file_name="2026-01-15_090000")

    call_command("sync_mada_partial")

    assert ApiSyncLog.objects.filter(sync_type="partial_import").count() == 1


def test_przetwarza_pliki_nowsze_niz_kursor(mada_api, rsps):
    ApiSyncLog.objects.create(
        sync_type="partial_import", status="completed", file_name="2026-01-15_090000")
    mock_mada.register_manifest(rsps, [
        {"name": "2026-01-15_090000", "date": "2026-01-15 09:00:00", "type": "partial"},
        {"name": "2026-01-15_100000", "date": "2026-01-15 10:00:00", "type": "partial"},
        {"name": "2026-01-15_110000", "date": "2026-01-15 11:00:00", "type": "partial"},
    ])
    mock_mada.register_file(rsps, "2026-01-15_100000", PRODUCERS,
                            [mock_mada.simple_product(161, ean="111", stock=3)])
    mock_mada.register_file(rsps, "2026-01-15_110000", PRODUCERS,
                            [mock_mada.simple_product(162, ean="222", stock=7)])

    call_command("sync_mada_partial")

    assert MadaProduct.objects.filter(api_id__in=[161, 162]).count() == 2
    done = set(ApiSyncLog.objects.filter(
        sync_type="partial_import", status="completed").values_list("file_name", flat=True))
    assert done == {"2026-01-15_090000", "2026-01-15_100000", "2026-01-15_110000"}


def test_kolejne_uruchomienie_nie_dubluje_historii(mada_api):
    def run(files_in_manifest, file_to_serve, stock):
        with responses.RequestsMock() as rsps:
            mock_mada.register_manifest(rsps, files_in_manifest)
            mock_mada.register_file(rsps, file_to_serve, PRODUCERS,
                                    [mock_mada.simple_product(161, ean="111", stock=stock)])
            call_command("sync_mada_partial")

    f1 = {"name": "2026-01-15_100000", "date": "2026-01-15 10:00:00", "type": "partial"}
    f2 = {"name": "2026-01-15_110000", "date": "2026-01-15 11:00:00", "type": "partial"}

    run([f1], "2026-01-15_100000", 5)            # increase 0→5
    run([f1, f2], "2026-01-15_110000", 1)        # decrease 5→1

    # symulacja redelivery: kursor "cofnięty", ten sam plik leci znów
    ApiSyncLog.objects.filter(file_name="2026-01-15_110000").delete()
    run([f1, f2], "2026-01-15_110000", 1)

    assert StockHistory.objects.count() == 2
