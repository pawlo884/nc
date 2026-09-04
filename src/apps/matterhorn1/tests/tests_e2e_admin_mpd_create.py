"""
E2E: `ProductAdmin.mpd_create` — tworzenie produktu MPD z formularza przez
7-krokową `SagaService.create_product_with_mapping`.

`transaction=True`: kod pod testem miesza konwencje dostępu do baz — bare
`Product.objects.get()` (matterhorn1) idzie w testach do aliasu `default`
(routery wyłączone), ale krok uploadu zdjęć czyta `connections['matterhorn1']`
raw SQL. Bez prawdziwych commitów (`transaction=True`) te dwie strony nie
widziałyby nawzajem swoich zapisów — patrz `docs/TESTING.md` (gotcha
multi-DB) i notatka w PR #216. Wolniejsze niż zwykły `django_db`, ale to
jedyny sposób na realny e2e tego przepływu bez mockowania połowy sagi.

Produkt matterhorn bez zdjęć → krok 7 (`_upload_product_images`) jest
no-opem, nie trzeba mockować S3/MinIO. Bez `mpd_size_category` w POST kroki
4–6 (paths/fabric/warianty) są pomijane przez samą sagę (warunkowe
`saga.add_step`) — warianty mają już pokrycie w `tests_saga_variants.py`.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from django.contrib import admin
from django.test import RequestFactory

from matterhorn1.admin import ProductAdmin
from matterhorn1.models import Brand, Product
from MPD.models import Attributes, ProductAttribute
from MPD.models import Products as MpdProducts

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True, databases="__all__")]
MPD_DB = "MPD"


@pytest.fixture
def product_admin():
    return ProductAdmin(Product, admin.site)


@pytest.fixture
def mh_product():
    brand = Brand.objects.using("matterhorn1").create(brand_id="MPDC", name="Marko")
    return Product.objects.using("matterhorn1").create(
        product_uid=800001, name="Produkt do mpd_create", brand=brand)


class TestMpdCreateHappyPath:
    def test_tworzy_produkt_mpd_i_ustawia_mapping(self, product_admin, mh_product):
        request = RequestFactory().post("/", data={
            "mpd_name": "Kostium z formularza",
            "mpd_description": "Opis",
            "mpd_brand": "Marko",
        })

        response = product_admin.mpd_create(request, mh_product.id)

        payload = json.loads(response.content)
        assert payload["success"] is True, payload

        product = MpdProducts.objects.using(MPD_DB).get(name="Kostium z formularza")
        assert product.brand.name == "Marko"
        mh_product.refresh_from_db()
        assert mh_product.mapped_product_uid == product.id
        assert mh_product.is_mapped is True

    def test_dodaje_atrybuty(self, product_admin, mh_product):
        attr = Attributes.objects.using(MPD_DB).create(name="usztywniane miseczki")
        request = RequestFactory().post("/", data={
            "mpd_name": "Z atrybutem",
            "mpd_attributes": [str(attr.id)],
        })

        response = product_admin.mpd_create(request, mh_product.id)
        assert json.loads(response.content)["success"] is True

        product = MpdProducts.objects.using(MPD_DB).get(name="Z atrybutem")
        assert ProductAttribute.objects.using(MPD_DB).filter(
            product_id=product.id, attribute_id=attr.id).exists()


class TestMpdCreateValidation:
    def test_brak_nazwy_zwraca_blad_bez_efektow(self, product_admin, mh_product):
        request = RequestFactory().post("/", data={})

        response = product_admin.mpd_create(request, mh_product.id)

        assert json.loads(response.content)["success"] is False
        mh_product.refresh_from_db()
        assert mh_product.mapped_product_uid is None

    def test_get_zwraca_blad_metody(self, product_admin, mh_product):
        request = RequestFactory().get("/")
        response = product_admin.mpd_create(request, mh_product.id)
        assert json.loads(response.content)["success"] is False


class TestMpdCreateCompensation:
    def test_blad_w_kroku_atrybutow_cofa_mapping_ale_nie_produkt_mpd(
        self, product_admin, mh_product
    ):
        """Krok 3 (atrybuty) rzuca -> saga kompensuje krok 2 (mapping, przez
        ORM - działa) i krok 1 (produkt MPD, przez HTTP `requests.delete` -
        w testach nie ma dokąd polecieć, fail-open łyka wyjątek). Produkt MPD
        zostaje osierocony - to udokumentowane zachowanie z PR #213, nie cel
        tego testu, tylko dowód że saga faktycznie próbuje kompensować."""
        attr = Attributes.objects.using(MPD_DB).create(name="cecha")
        request = RequestFactory().post("/", data={
            "mpd_name": "Ma się nie udać",
            "mpd_attributes": [str(attr.id)],
        })

        with patch("matterhorn1.saga.SagaService._add_mpd_attributes",
                   side_effect=RuntimeError("boom")), \
             patch("requests.delete", side_effect=RuntimeError("brak sieci w testach")):
            response = product_admin.mpd_create(request, mh_product.id)

        assert json.loads(response.content)["success"] is False

        mh_product.refresh_from_db()
        assert mh_product.mapped_product_uid is None  # krok 2 skompensowany
        assert MpdProducts.objects.using(MPD_DB).filter(name="Ma się nie udać").exists()
