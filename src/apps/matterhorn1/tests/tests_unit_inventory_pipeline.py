"""
Unit: orkiestracja pipeline'u pobierania stron INVENTORY w
`_update_inventory_from_api` — ten sam wzorzec co ITEMS
(`tests_unit_items_pipeline.py`): kilka stron w locie naraz, ale zapis
(`_bulk_update_inventory`) musi iść ŚCIŚLE w kolejności stron, niezależnie od
tego, która odpowiedź HTTP wróci pierwsza.

`_fetch_inventory_page` i `_bulk_update_inventory` są tu zamockowane — to
czysta weryfikacja logiki orkiestratora, bez DB/HTTP.
"""
from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

from matterhorn1.tasks import _update_inventory_from_api

pytestmark = pytest.mark.unit


def test_strony_przetwarzane_w_kolejnosci_mimo_odwroconej_kolejnosci_odpowiedzi(monkeypatch):
    """Strona 2 "odpowiada" (kończy fetch) zanim strona 1 zdąży - orkiestrator
    musi mimo to zapisać/przetworzyć 1 przed 2."""
    monkeypatch.setattr("matterhorn1.tasks.time.sleep", lambda *_a, **_k: None)

    page2_done = threading.Event()

    def fake_fetch(page, api_url, headers, limit, last_update):
        if page == 1:
            assert page2_done.wait(5), "strona 2 nie odpowiedziała na czas"
            return {'outcome': 'ok', 'items': [{'id': 1, 'inventory': []}]}
        if page == 2:
            page2_done.set()
            return {'outcome': 'ok', 'items': [{'id': 2, 'inventory': []}]}
        return {'outcome': 'stop'}

    processed_order = []

    def fake_bulk_update(inventory_data):
        processed_order.append(inventory_data[0]['id'])
        return len(inventory_data)

    with patch("matterhorn1.tasks._fetch_inventory_page", side_effect=fake_fetch), \
            patch("matterhorn1.tasks._bulk_update_inventory", side_effect=fake_bulk_update), \
            patch("matterhorn1.tasks._get_last_items_update_time", return_value="2026-01-01 00:00:00"):
        result = _update_inventory_from_api(
            api_url="https://matterhorn.example", username="u", password="p",
            batch_size=100, dry_run=False,
        )

    assert result["status"] == "success"
    assert result["updated_count"] == 2
    assert processed_order == [1, 2]


def test_stop_na_stronie_przerywa_i_ignoruje_juz_wystrzelone_strony(monkeypatch):
    """Strona 2 kończy się "stop" (koniec danych/błąd - bez retry, jak
    oryginalnie) - aktualizacja ma się zatrzymać, a wynik już pobranej
    strony 3+ (wystrzelonej spekulatywnie zanim strona 2 zdążyła odpowiedzieć)
    ma zostać zignorowany. W przeciwieństwie do ITEMS - to nadal 'success'
    (częściowy wynik), bo INVENTORY tak działało już wcześniej."""
    monkeypatch.setattr("matterhorn1.tasks.time.sleep", lambda *_a, **_k: None)

    def fake_fetch(page, api_url, headers, limit, last_update):
        if page == 1:
            return {'outcome': 'ok', 'items': [{'id': 1, 'inventory': []}]}
        if page == 2:
            return {'outcome': 'stop'}
        # strona 3 (i dalsze) - wystrzelona spekulatywnie, ma dane, ale nie
        # może zostać zapisana, bo stoi za stroną 2, która kończy pipeline.
        return {'outcome': 'ok', 'items': [{'id': page, 'inventory': []}]}

    processed_order = []

    def fake_bulk_update(inventory_data):
        processed_order.append(inventory_data[0]['id'])
        return len(inventory_data)

    with patch("matterhorn1.tasks._fetch_inventory_page", side_effect=fake_fetch), \
            patch("matterhorn1.tasks._bulk_update_inventory", side_effect=fake_bulk_update), \
            patch("matterhorn1.tasks._get_last_items_update_time", return_value="2026-01-01 00:00:00"):
        result = _update_inventory_from_api(
            api_url="https://matterhorn.example", username="u", password="p",
            batch_size=100, dry_run=False,
        )

    assert result["status"] == "success"
    assert result["updated_count"] == 1
    assert processed_order == [1]


def test_dry_run_nie_woła_bulk_update(monkeypatch):
    monkeypatch.setattr("matterhorn1.tasks.time.sleep", lambda *_a, **_k: None)

    def fake_fetch(page, api_url, headers, limit, last_update):
        if page == 1:
            return {'outcome': 'ok', 'items': [{'id': 1, 'inventory': []}]}
        return {'outcome': 'stop'}

    with patch("matterhorn1.tasks._fetch_inventory_page", side_effect=fake_fetch), \
            patch("matterhorn1.tasks._bulk_update_inventory") as mock_bulk, \
            patch("matterhorn1.tasks._get_last_items_update_time", return_value="2026-01-01 00:00:00"):
        result = _update_inventory_from_api(
            api_url="https://matterhorn.example", username="u", password="p",
            batch_size=100, dry_run=True,
        )

    mock_bulk.assert_not_called()
    assert result["status"] == "success"
    assert result["updated_count"] == 0
