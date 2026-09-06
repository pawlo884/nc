"""
Mock API Tabu (`responses`). `GET {base}/products/basic` — stronicowana płaska
lista wariantów; kolejne `?page=N` zwracają kolejne elementy listy `pages`,
strona za końcem zwraca `{'products': []}` (command traktuje to jako koniec).
"""
from __future__ import annotations

import json

import responses

BASIC_PATH = "products/basic"


def _base(settings) -> str:
    return (settings.TABU_API_BASE_URL or "https://tabu.test").rstrip("/")


def mock_products_basic(rsps, settings, pages: list[list[dict]],
                        total: int | None = None) -> None:
    """`pages` = lista stron, każda to lista rekordów (`factories.basic_record`)."""
    url = f"{_base(settings)}/{BASIC_PATH}"

    def _cb(request):
        try:
            page = int(request.params.get("page", "1"))
        except (TypeError, ValueError):
            page = 1
        idx = page - 1
        body = pages[idx] if 0 <= idx < len(pages) else []
        payload = {"products": body}
        if total is not None:
            payload["total"] = total
        return (200, {"Content-Type": "application/json"}, json.dumps(payload))

    rsps.add_callback(responses.GET, url, callback=_cb, content_type="application/json")


def mock_products_basic_error(rsps, settings, status: int = 500) -> None:
    rsps.add(responses.GET, f"{_base(settings)}/{BASIC_PATH}", status=status)
