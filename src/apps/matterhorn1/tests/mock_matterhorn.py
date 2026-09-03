"""
Mock API Matterhorn (B2BAPI) oparty o `responses`.

Rejestruje `GET {api_url}/B2BAPI/ITEMS/` i `.../ITEMS/INVENTORY/` jako
stronicowane endpointy — kolejne `?page=N` zwracają kolejne elementy listy
`pages`, a strona za końcem zwraca `[]` (import traktuje to jako koniec).

Wszystkie helpery biorą `rsps` (instancję `responses.RequestsMock` z fixture
`mocked_responses`) jako pierwszy argument:

    def test_x(matterhorn_api, mocked_responses):
        mock_items(mocked_responses, [[api_item(), api_item()], []])
        mock_inventory(mocked_responses, [[]])
        full_import_and_update(auto_continue=False)

`page` w API Matterhorn jest 1-indeksowane.
"""
from __future__ import annotations

import json

import responses
from django.conf import settings

ITEMS_PATH = "/B2BAPI/ITEMS/"
INVENTORY_PATH = "/B2BAPI/ITEMS/INVENTORY/"


def _base_url() -> str:
    return getattr(settings, "MATTERHORN_API_URL", "https://matterhorn.pl").rstrip("/")


def _paginated_callback(pages: list[list[dict]]):
    def _cb(request):
        try:
            page = int(request.params.get("page", "1"))
        except (TypeError, ValueError):
            page = 1
        idx = page - 1  # API 1-indeksowane
        body = pages[idx] if 0 <= idx < len(pages) else []
        return (200, {"Content-Type": "application/json"}, json.dumps(body))
    return _cb


def mock_items(rsps, pages: list[list[dict]]) -> None:
    """`pages` = lista stron, każda to lista elementów ITEMS."""
    rsps.add_callback(
        responses.GET,
        f"{_base_url()}{ITEMS_PATH}",
        callback=_paginated_callback(pages),
        content_type="application/json",
    )


def mock_inventory(rsps, pages: list[list[dict]]) -> None:
    """`pages` = lista stron, każda to lista rekordów INVENTORY."""
    rsps.add_callback(
        responses.GET,
        f"{_base_url()}{INVENTORY_PATH}",
        callback=_paginated_callback(pages),
        content_type="application/json",
    )


def mock_items_error(rsps, status: int = 500, page: int | None = None) -> None:
    """Błąd HTTP na endpoincie ITEMS (opcjonalnie tylko dla `page`)."""
    kwargs = {}
    if page is not None:
        kwargs["match"] = [responses.matchers.query_param_matcher(
            {"page": str(page)}, strict_match=False)]
    rsps.add(responses.GET, f"{_base_url()}{ITEMS_PATH}", status=status, **kwargs)
