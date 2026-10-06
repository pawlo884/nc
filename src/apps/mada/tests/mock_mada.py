"""
Buildery odpowiedzi API Mada (`get_xml.php`) do mockowania przez `responses`.

- manifest: `<FILES><FILE><NAME/><DATE/><TYPE/></FILE>...</FILES>`
- plik danych: ZIP zawierający `products.xml`
"""
from __future__ import annotations

import io
import zipfile
from typing import Iterable

import responses

BASE_URL = "https://mada.test"
MANIFEST_URL = f"{BASE_URL}/get_xml.php"


def manifest_xml(files: Iterable[dict]) -> bytes:
    """`files`: [{'name':..., 'date':'2026-01-15 00:01:00', 'type':'full'|'partial'}]"""
    rows = "".join(
        f"<FILE><NAME>{f['name']}</NAME><DATE>{f.get('date', '')}</DATE>"
        f"<TYPE>{f['type']}</TYPE></FILE>"
        for f in files
    )
    return f'<?xml version="1.0" encoding="utf-8"?><FILES>{rows}</FILES>'.encode()


def _product_xml(p: dict) -> str:
    cats = "".join(
        f'<CATEGORY c1="{c["c1"]}" c2="{c["c2"]}"><![CDATA[{c.get("name", "")}]]></CATEGORY>'
        for c in p.get("categories", [])
    )
    models = ""
    for color, sizes in p.get("models", []):
        size_els = "".join(
            f'<SIZE amount="{s["amount"]}"'
            + (f' ean="{s["ean"]}"' if s.get("ean") else "")
            + f'>{s["label"]}</SIZE>'
            for s in sizes
        )
        models += f"<MODEL><COLOR><![CDATA[{color}]]></COLOR>{size_els}</MODEL>"
    imgs = "".join(
        f'<IMG id="{i["id"]}">{i["url"]}</IMG>' for i in p.get("images", [])
    )
    old_price = f"<OLD_PRICE>{p['old_price']}</OLD_PRICE>" if p.get("old_price") else ""
    return (
        f"<PRODUCT><ID>{p['id']}</ID>"
        f"<NAME><![CDATA[{p.get('name', '')}]]></NAME>"
        f"<DESC><![CDATA[{p.get('desc', '')}]]></DESC>"
        f"<PRODUCER>{p.get('producer_id', '')}</PRODUCER>"
        f"<PRICE>{p.get('price', '0')}</PRICE>{old_price}<VAT>{p.get('vat', '23')}</VAT>"
        f"<CATEGORIES>{cats}</CATEGORIES>"
        f"<MODELS>{models}</MODELS><IMAGES>{imgs}</IMAGES></PRODUCT>"
    )


def products_xml(producers: dict, products: Iterable[dict]) -> bytes:
    prod_rows = "".join(
        f'<PRODUCER id="{pid}"><![CDATA[{name}]]></PRODUCER>'
        for pid, name in producers.items()
    )
    product_rows = "".join(_product_xml(p) for p in products)
    return (
        '<?xml version="1.0" encoding="utf-8"?><DATA>'
        f"<PRODUCERS>{prod_rows}</PRODUCERS>"
        f"<PRODUCTS>{product_rows}</PRODUCTS></DATA>"
    ).encode()


def zip_bytes(inner_xml: bytes, inner_name: str = "products.xml") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_name, inner_xml)
    return buf.getvalue()


def simple_product(pid: int, *, name="Rajstopy", producer_id="110", stock=5,
                   ean="5901234567890", price="12.04", **over) -> dict:
    d = {
        "id": pid,
        "name": name,
        "desc": "Opis",
        "producer_id": producer_id,
        "price": price,
        "categories": [{"c1": "30", "c2": "63", "name": "Rajstopy / lycra"}],
        "models": [("czarny", [{"amount": stock, "ean": ean, "label": "M"}])],
        "images": [],
    }
    d.update(over)
    return d


def register_manifest(rsps: responses.RequestsMock, files):
    rsps.add(responses.GET, MANIFEST_URL, body=manifest_xml(files),
             content_type="application/xml")


def register_file(rsps: responses.RequestsMock, file_name: str, producers: dict, products):
    rsps.add(
        responses.GET, MANIFEST_URL,
        match=[responses.matchers.query_param_matcher({"file": file_name}, strict_match=False)],
        body=zip_bytes(products_xml(producers, products)),
        content_type="application/zip",
    )
