"""
Buildery obiektów DB i ładunków API Tabu.

Wartości domyślne = minimalny poprawny rekord; nadpisujesz tylko to, co
testuje dany przypadek. `db` domyślnie `default` — w trybie testowym
`DATABASE_ROUTERS = []`, więc modele `tabu` i tak lądują na `default`
(patrz `sync_tabu_stock` — `router.db_for_write` → `default`).
"""
from __future__ import annotations

import itertools
from typing import Any

from django.utils import timezone

from tabu.models import Brand, Category, TabuProduct, TabuProductVariant

_pid = itertools.count(500_000)
_vid = itertools.count(700_000)


def brand(db: str = "default", **over: Any) -> Brand:
    data = {"brand_id": f"B{next(_pid)}", "name": "Marka"}
    data.update(over)
    return Brand.objects.using(db).create(**data)


def category(db: str = "default", **over: Any) -> Category:
    data = {"category_id": f"C{next(_pid)}", "name": "Kategoria", "path": "Damskie/Bluzki"}
    data.update(over)
    return Category.objects.using(db).create(**data)


def tabu_product(db: str = "default", **over: Any) -> TabuProduct:
    api_id = over.pop("api_id", None) or next(_pid)
    data = {
        "api_id": api_id,
        "symbol": f"SYM-{api_id}",
        "name": f"Produkt {api_id}",
        "last_update": timezone.now(),
        "store_total": 0,
        "price_net": "100.00",
        "price_gross": "123.00",
    }
    data.update(over)
    return TabuProduct.objects.using(db).create(**data)


def tabu_variant(product: TabuProduct, db: str = "default", **over: Any) -> TabuProductVariant:
    api_id = over.pop("api_id", None) or next(_vid)
    data = {
        "api_id": api_id,
        "product": product,
        "symbol": f"VAR-{api_id}",
        "ean": "5901234567890",
        "store": 5,
        "price_net": "100.00",
        "price_gross": "123.00",
        "size": "M",
        "color": "czarny",
    }
    data.update(over)
    return TabuProductVariant.objects.using(db).create(**data)


def basic_record(*, product_api_id: int, variant_api_id: int, store: int,
                 price_net=None, price_gross=None) -> dict:
    """Pojedynczy rekord z `GET products/basic` — płaska lista wariantów
    (`id` = produkt, `variant_id` = wariant)."""
    r = {"id": product_api_id, "variant_id": variant_api_id, "store": store}
    if price_net is not None:
        r["price_net"] = str(price_net)
    if price_gross is not None:
        r["price_gross"] = str(price_gross)
    return r


def api_variant_detail(*, api_id: int, store: int = 3, color="czarny", size="M", **over):
    v = {
        "id": api_id,
        "symbol": f"V{api_id}",
        "ean": "5901234567890",
        "store": store,
        "price_net": "100.00",
        "price_gross": "123.00",
        "items": [{"name": "Kolor", "value": color}, {"name": "Rozmiar", "value": size}],
    }
    v.update(over)
    return v


def api_product_detail(*, api_id: int, variants=None, gallery=None, **over) -> dict:
    """Odpowiedź `GET products/{id}` (pełne dane) — kształt zgodny z
    `map_api_product_to_model`."""
    p = {
        "id": api_id,
        "symbol": f"P{api_id}",
        "name": f"Produkt {api_id}",
        "ean": "5900000000001",
        "producer_id": 7,
        "producer": "Marko",
        "category_id": 42,
        "category": "Damskie/Bluzki",
        "price_net": "100.00",
        "price_gross": "123.00",
        "last_update": "2026-01-15T10:00:00",
        "variants": variants if variants is not None else [api_variant_detail(api_id=api_id * 10)],
        "gallery": gallery if gallery is not None else [],
    }
    p.update(over)
    return p
