"""
Integration: akcje admina `matterhorn1.ProductAdmin` łączące produkt
matterhorn1 z MPD.

`mpd_create` (nowy produkt MPD przez sagę) jest ciężki — 7-krokowa saga
+ upload zdjęć + kompensacja przez HTTP; e2e tego zostaje do osobnego
podejścia. Tu lżejsze `assign_mapping` (podpięcie istniejącego produktu MPD).
"""
from __future__ import annotations

import json

import pytest
from django.contrib import admin
from django.test import RequestFactory

from matterhorn1.admin import ProductAdmin
from matterhorn1.models import Brand, Product
from MPD.models import Products as MpdProducts

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases="__all__")]


@pytest.fixture
def product_admin():
    return ProductAdmin(Product, admin.site)


@pytest.fixture
def mh_product():
    brand = Brand.objects.using("matterhorn1").create(brand_id="B", name="Marko")
    return Product.objects.using("matterhorn1").create(
        product_uid=990001, name="Produkt MH", brand=brand)


@pytest.fixture
def mpd_product():
    return MpdProducts.objects.using(
        _mpd_db()).create(name="Produkt MPD do podpięcia")


def _mpd_db():
    from django.conf import settings
    return "zzz_MPD" if "zzz_MPD" in settings.DATABASES else "MPD"


class TestAssignMapping:
    def test_ustawia_mapowanie_na_produkcie_matterhorn(self, product_admin, mh_product, mpd_product):
        request = RequestFactory().post("/", data={})

        response = product_admin.assign_mapping(request, mh_product.id, mpd_product.id)

        payload = json.loads(response.content)
        assert payload["success"] is True

        mh_product.refresh_from_db()
        assert mh_product.mapped_product_uid == mpd_product.id
        assert mh_product.is_mapped is True

    def test_get_zwraca_blad_metody(self, product_admin, mh_product, mpd_product):
        request = RequestFactory().get("/")

        response = product_admin.assign_mapping(request, mh_product.id, mpd_product.id)

        assert json.loads(response.content)["success"] is False
