"""
Unit: `_fetch_inventory_page` — klasyfikacja odpowiedzi B2BAPI/ITEMS/INVENTORY.

Regresja: wcześniej KAŻDY problem (200-nie-JSON, 5xx, sieć) był 'stop' i INVENTORY
kończyło się jako 'success' z 0 update'ów — okno stanów magazynowych przepadało
po cichu. Teraz błąd (po wyczerpaniu prób) to 'error', a tylko pusta odpowiedź /
[] / 404 to 'end_of_data'.
"""
from __future__ import annotations

import pytest
import responses

from matterhorn1.tasks import _fetch_inventory_page

pytestmark = pytest.mark.unit

URL_RE = responses.matchers.query_param_matcher({}, strict_match=False)
BASE = "https://matterhorn.test/B2BAPI/ITEMS/INVENTORY/"
HEADERS = {"Authorization": "test"}


def _call(page=1):
    return _fetch_inventory_page(page, "https://matterhorn.test", HEADERS, 1000, "2026-01-01 00:00:00")


@responses.activate
def test_200_z_danymi_to_ok():
    responses.add(responses.GET, BASE, json=[{"id": 1, "inventory": []}], status=200)
    assert _call() == {"outcome": "ok", "items": [{"id": 1, "inventory": []}]}


@responses.activate
def test_pusta_odpowiedz_to_end_of_data():
    responses.add(responses.GET, BASE, body="   ", status=200)
    assert _call() == {"outcome": "end_of_data"}


@responses.activate
def test_pusta_lista_to_end_of_data():
    responses.add(responses.GET, BASE, json=[], status=200)
    assert _call() == {"outcome": "end_of_data"}


@responses.activate
def test_404_to_end_of_data():
    responses.add(responses.GET, BASE, status=404)
    assert _call() == {"outcome": "end_of_data"}


@responses.activate
def test_200_nie_json_ponawiane_potem_error():
    # 5 prób (max_attempts) — wszystkie 200 z HTML-em
    for _ in range(5):
        responses.add(responses.GET, BASE, body="<html>Rate limit exceeded</html>", status=200)
    out = _call()
    assert out["outcome"] == "error"
    assert "JSON" in out["error"]
    assert len(responses.calls) == 5


@responses.activate
def test_200_nie_json_a_potem_sukces():
    responses.add(responses.GET, BASE, body="<html>chwilowy błąd</html>", status=200)
    responses.add(responses.GET, BASE, json=[{"id": 7, "inventory": []}], status=200)
    out = _call()
    assert out == {"outcome": "ok", "items": [{"id": 7, "inventory": []}]}
    assert len(responses.calls) == 2


@responses.activate
def test_500_ponawiane_potem_error():
    for _ in range(5):
        responses.add(responses.GET, BASE, status=500)
    out = _call()
    assert out["outcome"] == "error"
    assert "500" in out["error"]


@responses.activate
def test_500_a_potem_sukces():
    responses.add(responses.GET, BASE, status=503)
    responses.add(responses.GET, BASE, json=[{"id": 9, "inventory": []}], status=200)
    assert _call()["outcome"] == "ok"


@responses.activate
def test_blad_sieci_ponawiany_potem_error():
    for _ in range(5):
        responses.add(responses.GET, BASE, body=responses.ConnectionError("boom"))
    out = _call()
    assert out["outcome"] == "error"
    assert "nieosiągalna" in out["error"]
