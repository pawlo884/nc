"""
Integration: `ProductAdmin.bulk_map_to_mpd` / `auto_map_variants` (endpointy
JSON). `_auto_map_variants` (rzeczywiste tworzenie wariantów w MPD) jest
zamockowane — jego własna logika ma osobne pokrycie w
`tests_admin_linking.py` (dispatch taska linkowania po commicie). Tu
testujemy warstwę widoku: walidację, kształt odpowiedzi, obsługę błędów.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from django.contrib import admin
from django.test import RequestFactory

from matterhorn1.admin import ProductAdmin
from matterhorn1.models import Brand, Product

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases=["default", "matterhorn1"])]


@pytest.fixture
def product_admin():
    return ProductAdmin(Product, admin.site)


@pytest.fixture
def mh_product():
    brand = Brand.objects.create(brand_id="BULK", name="Bulk Brand")
    return Product.objects.create(product_uid=810001, name="Bulk product", brand=brand)


class TestAutoMapVariantsView:
    def test_produkt_niezmapowany_zwraca_blad(self, product_admin, mh_product):
        request = RequestFactory().post("/")

        response = product_admin.auto_map_variants(request, mh_product.id)

        payload = json.loads(response.content)
        assert payload["success"] is False
        assert "zmapowany" in payload["error"]

    def test_produkt_zmapowany_woła_auto_map_i_zwraca_liste(self, product_admin, mh_product):
        mh_product.mapped_product_uid = 999
        mh_product.is_mapped = True
        mh_product.save()

        request = RequestFactory().post("/")
        with patch.object(ProductAdmin, "_auto_map_variants", return_value=[1, 2, 3]) as mocked:
            response = product_admin.auto_map_variants(request, mh_product.id)

        mocked.assert_called_once_with(mh_product, 999)
        payload = json.loads(response.content)
        assert payload["success"] is True
        assert payload["variants"] == [1, 2, 3]

    def test_get_zwraca_blad_metody(self, product_admin, mh_product):
        response = product_admin.auto_map_variants(RequestFactory().get("/"), mh_product.id)
        assert json.loads(response.content)["success"] is False


class TestBulkMapToMpd:
    def test_mapuje_i_liczy_sukcesy(self, product_admin, mh_product):
        body = json.dumps({"mappings": [{"product_id": mh_product.id, "mpd_product_id": 42}]})
        request = RequestFactory().post("/", data=body, content_type="application/json")

        with patch.object(ProductAdmin, "_auto_map_variants", return_value=[]):
            response = product_admin.bulk_map_to_mpd(request)

        payload = json.loads(response.content)
        assert payload["success"] is True
        assert "1" in payload["message"]

        mh_product.refresh_from_db()
        assert mh_product.mapped_product_uid == 42
        assert mh_product.is_mapped is True

    def test_pomija_mapowanie_bez_id(self, product_admin, mh_product):
        body = json.dumps({"mappings": [{"product_id": None, "mpd_product_id": 42}]})
        request = RequestFactory().post("/", data=body, content_type="application/json")

        with patch.object(ProductAdmin, "_auto_map_variants") as mocked:
            response = product_admin.bulk_map_to_mpd(request)

        mocked.assert_not_called()
        assert json.loads(response.content)["success"] is True
        mh_product.refresh_from_db()
        assert mh_product.mapped_product_uid is None

    def test_blad_pojedynczego_mapowania_nie_przerywa_reszty(self, product_admin, mh_product):
        other = Product.objects.create(product_uid=810002, name="Drugi")
        body = json.dumps({"mappings": [
            {"product_id": 99999999, "mpd_product_id": 1},   # nie istnieje -> błąd
            {"product_id": other.id, "mpd_product_id": 2},   # ten ma się udać
        ]})
        request = RequestFactory().post("/", data=body, content_type="application/json")

        with patch.object(ProductAdmin, "_auto_map_variants", return_value=[]):
            response = product_admin.bulk_map_to_mpd(request)

        payload = json.loads(response.content)
        assert payload["success"] is True
        assert len(payload["errors"]) == 1
        other.refresh_from_db()
        assert other.mapped_product_uid == 2

    def test_get_zwraca_blad_metody(self, product_admin):
        response = product_admin.bulk_map_to_mpd(RequestFactory().get("/"))
        assert json.loads(response.content)["success"] is False
