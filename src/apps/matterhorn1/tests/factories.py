"""
Buildery ładunków API Matterhorn (B2BAPI/ITEMS, B2BAPI/ITEMS/INVENTORY).

Kształt zgodny z tym, co parsuje `matterhorn1.tasks._prepare_product_create`
i `_bulk_update_inventory`. Wartości domyślne = minimalny poprawny produkt;
nadpisujesz tylko to, co testuje dany przypadek.
"""
from __future__ import annotations

import itertools
from typing import Any

_pid = itertools.count(10_000)
_vid = itertools.count(90_000)


def api_variant(**over: Any) -> dict:
    """Wariant w elemencie ITEMS."""
    v = {
        "variant_uid": next(_vid),
        "name": "M",
        "stock": "5",
        "max_processing_time": "2",
        "ean": "5900000000001",
    }
    v.update(over)
    return v


def api_item(**over: Any) -> dict:
    """Pojedynczy produkt z B2BAPI/ITEMS. `creation_date` jest WYMAGANE przez
    import (`_bulk_import_products` pomija elementy bez niego)."""
    pid = over.pop("id", None)
    if pid is None:
        pid = next(_pid)
    item = {
        "id": pid,
        "name": f"Kostium {pid}",
        "description": "Opis produktu.",
        "creation_date": "2026-01-15T10:00:00",
        "color": "czarny",
        "url": f"https://matterhorn.example/p/{pid}",
        "active": True,
        "new_collection": "N",
        "brand_id": "MARKO",
        "brand": "Marko",
        "category_id": "100",
        "category_name": "Bikini",
        "category_path": "Damskie/Bikini",
        "prices": {"retail": "134.00"},
        "products_in_set": [],
        "other_colors": [],
        "variants": [api_variant()],
        "images": [f"https://matterhorn.example/img/{pid}_1.jpg"],
    }
    item.update(over)
    return item


def inventory_record(item_id: int, variants: list[dict]) -> dict:
    """Rekord z B2BAPI/ITEMS/INVENTORY: `{id, inventory: [{variant_uid, stock}]}`."""
    return {
        "id": item_id,
        "inventory": [
            {"variant_uid": v["variant_uid"], "stock": str(v["stock"])}
            for v in variants
        ],
    }
