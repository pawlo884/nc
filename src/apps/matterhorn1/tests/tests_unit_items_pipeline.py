"""
Unit: orkiestracja pipeline'u pobierania stron ITEMS w `_import_products_from_items`
— kilka stron w locie naraz (patrz komentarz w tasks.py), ale zapis do bazy i
checkpoint muszą iść ŚCIŚLE w kolejności stron, niezależnie od tego, która
odpowiedź HTTP wróci pierwsza.

`_fetch_items_page` i `_bulk_import_products` są tu zamockowane — to czysta
weryfikacja logiki orkiestratora, bez DB/HTTP.
"""
from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

from matterhorn1.tasks import _import_products_from_items

pytestmark = pytest.mark.unit


def test_strony_przetwarzane_w_kolejnosci_mimo_odwroconej_kolejnosci_odpowiedzi(monkeypatch):
    """Strona 2 "odpowiada" (kończy fetch) zanim strona 1 zdąży - orkiestrator
    musi mimo to zapisać/przetworzyć 1 przed 2."""
    monkeypatch.setattr("matterhorn1.tasks.time.sleep", lambda *_a, **_k: None)

    page2_done = threading.Event()

    def fake_fetch(page, api_url, headers, limit, last_update):
        if page == 1:
            # Puść stronę 2 do przodu, zanim strona 1 "odpowie".
            assert page2_done.wait(5), "strona 2 nie odpowiedziała na czas"
            return {'outcome': 'ok', 'items': [{'id': 1, 'creation_date': '2026-01-01'}]}
        if page == 2:
            page2_done.set()
            return {'outcome': 'ok', 'items': [{'id': 2, 'creation_date': '2026-01-01'}]}
        return {'outcome': 'end_of_data', 'reason': 'no_more_products'}

    processed_order = []

    def fake_bulk_import(items):
        processed_order.append(items[0]['id'])
        return {'status': 'success', 'imported_count': len(items), 'updated_count': 0}

    with patch("matterhorn1.tasks._fetch_items_page", side_effect=fake_fetch), \
            patch("matterhorn1.tasks._bulk_import_products", side_effect=fake_bulk_import), \
            patch("matterhorn1.tasks._get_last_items_update_time", return_value="2026-01-01 00:00:00"), \
            patch("matterhorn1.tasks._get_last_items_page", return_value=1), \
            patch("matterhorn1.tasks._save_items_import_start_time"), \
            patch("matterhorn1.tasks._update_items_import_status"):
        result = _import_products_from_items(
            start_id=None, max_products=200000, api_url="https://matterhorn.example",
            username="u", password="p", batch_size=100, dry_run=False,
        )

    assert result["status"] == "completed"
    assert result["reason"] == "no_more_products"
    assert processed_order == [1, 2]


def test_blad_pobierania_strony_przerywa_i_ignoruje_juz_wystrzelone_strony(monkeypatch):
    """Strona 2 kończy się błędem (wyczerpane retry) - import ma się przerwać,
    a wynik już pobranej strony 3+ (przez okno w locie, wystrzelonej
    spekulatywnie zanim strona 2 zdążyła się nie udać) ma zostać zignorowany."""
    monkeypatch.setattr("matterhorn1.tasks.time.sleep", lambda *_a, **_k: None)

    def fake_fetch(page, api_url, headers, limit, last_update):
        if page == 1:
            return {'outcome': 'ok', 'items': [{'id': 1, 'creation_date': '2026-01-01'}]}
        if page == 2:
            return {'outcome': 'error', 'error': 'Strona 2 nieosiągalna po 10 próbach'}
        # strona 3 (i dalsze) - wystrzelona spekulatywnie, ma dane, ale nie
        # może zostać zapisana, bo stoi za martwą stroną 2.
        return {'outcome': 'ok', 'items': [{'id': page, 'creation_date': '2026-01-01'}]}

    processed_order = []

    def fake_bulk_import(items):
        processed_order.append(items[0]['id'])
        return {'status': 'success', 'imported_count': len(items), 'updated_count': 0}

    with patch("matterhorn1.tasks._fetch_items_page", side_effect=fake_fetch), \
            patch("matterhorn1.tasks._bulk_import_products", side_effect=fake_bulk_import), \
            patch("matterhorn1.tasks._get_last_items_update_time", return_value="2026-01-01 00:00:00"), \
            patch("matterhorn1.tasks._get_last_items_page", return_value=1), \
            patch("matterhorn1.tasks._save_items_import_start_time"), \
            patch("matterhorn1.tasks._update_items_import_status"):
        result = _import_products_from_items(
            start_id=None, max_products=200000, api_url="https://matterhorn.example",
            username="u", password="p", batch_size=100, dry_run=False,
        )

    assert result["status"] == "error"
    assert processed_order == [1]
