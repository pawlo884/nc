"""
Buildery obiektów DB i ładunków feedu Mada.

Wartości domyślne = minimalny poprawny rekord; nadpisujesz tylko to, co
testuje dany przypadek. `db` domyślnie `default` — w trybie testowym
`DATABASE_ROUTERS = []`, więc modele `mada` i tak lądują na `default`.
"""
from __future__ import annotations

import itertools
from typing import Any

from mada.models import Brand, Category, MadaProduct, MadaProductVariant

_pid = itertools.count(160_000)
_producer = itertools.count(100)
_img = itertools.count(300_000)


def brand(db: str = "default", **over: Any) -> Brand:
    data = {"producer_id": str(next(_producer)), "name": "Gatta"}
    data.update(over)
    return Brand.objects.using(db).create(**data)


def category(db: str = "default", **over: Any) -> Category:
    data = {"category_id": f"{next(_pid)}-1", "name": "Rajstopy", "path": "Rajstopy"}
    data.update(over)
    return Category.objects.using(db).create(**data)


def mada_product(db: str = "default", **over: Any) -> MadaProduct:
    api_id = over.pop("api_id", None) or next(_pid)
    data = {
        "api_id": api_id,
        "name": f"Produkt {api_id}",
        "price": "12.00",
        "vat": "23",
    }
    data.update(over)
    return MadaProduct.objects.using(db).create(**data)


def mada_variant(product: MadaProduct, db: str = "default", **over: Any) -> MadaProductVariant:
    ean = over.pop("ean", None) or f"590{next(_img):010d}"
    data = {
        "product": product,
        "variant_key": ean,
        "color": "czarny",
        "size": "M",
        "ean": ean,
        "stock": 5,
    }
    data.update(over)
    return MadaProductVariant.objects.using(db).create(**data)


# --- ładunki feedu (dict po parsowaniu, kształt jak `parse_product_element`) ---

def variant_dict(*, color="czarny", size="M", ean=None, stock=5) -> dict:
    ean = ean if ean is not None else f"590{next(_img):010d}"
    return {
        "color": color,
        "size": size,
        "ean": ean,
        "stock": stock,
        "variant_key": ean or f"{color}|{size}",
    }


def product_dict(*, api_id=None, producer_id="110", variants=None, images=None, **over) -> dict:
    api_id = api_id if api_id is not None else next(_pid)
    d = {
        "api_id": api_id,
        "name": f"Rajstopy {api_id}",
        "desc": "Opis",
        "producer_id": producer_id,
        "price": "12.04",
        "old_price": None,
        "vat": "23",
        "categories": [{"c1": "30", "c2": "63", "name": "Rajstopy / lycra"}],
        "variants": variants if variants is not None else [variant_dict()],
        "images": images if images is not None else [],
        "raw_data": {"similar_products": []},
    }
    d.update(over)
    return d
