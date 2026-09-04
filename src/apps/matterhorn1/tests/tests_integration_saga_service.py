"""
Integration: kroki `matterhorn1.saga.SagaService` (implementacje execute /
compensate). Silnik sagi jest osobno w tests_integration_saga_orchestrator.py;
tu testujemy co robi każdy krok z osobna.

Pełne `create_product_with_mapping` end-to-end nie — krok 7 (upload zdjęć do
S3) i kompensacja kroku 1 przez HTTP (patrz `_delete_mpd_product`) wymagają
zamockowania zbyt wielu rzeczy naraz.

Uwaga o aliasach baz: `saga.py` używa `.using('MPD')` / `connections['MPD']`
dla MPD, ale dla matterhorn1 woła `Product.objects.get()` BEZ `.using()` —
w trybie testów (routery wyłączone) trafia to do `default`. Dlatego produkty
matterhorn tworzymy tu bez `.using()`, a MPD-owe przez `.using('MPD')` — tak
jak robi to kod pod testem.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from matterhorn1.models import Brand, Product
from matterhorn1.saga import SagaService
from MPD.models import Attributes, Brands, ProductAttribute, Products

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases="__all__")]
MPD_DB = "MPD"


class TestCreateMpdProduct:
    def test_tworzy_produkt_i_marke(self):
        res = SagaService._create_mpd_product({"name": "Kostium Saga", "brand_name": "Marko"})

        product = Products.objects.using(MPD_DB).get(id=res["mpd_product_id"])
        assert product.name == "Kostium Saga"
        assert product.brand.name == "Marko"
        assert Brands.objects.using(MPD_DB).filter(name="Marko").count() == 1

    def test_idempotentne_dla_tej_samej_nazwy_i_marki(self):
        r1 = SagaService._create_mpd_product({"name": "Dup", "brand_name": "Marko"})
        r2 = SagaService._create_mpd_product({"name": "Dup", "brand_name": "Marko"})

        assert r1["mpd_product_id"] == r2["mpd_product_id"]
        assert Products.objects.using(MPD_DB).filter(name="Dup").count() == 1

    def test_bez_marki_tez_dziala(self):
        res = SagaService._create_mpd_product({"name": "Bez marki"})
        assert Products.objects.using(MPD_DB).get(id=res["mpd_product_id"]).brand is None


class TestMatterhornMapping:
    @pytest.fixture
    def mh_product(self):
        # bez .using() — kod (_create_matterhorn_product_with_mapping) też woła
        # Product.objects.get() bez aliasu -> 'default' w testach
        brand = Brand.objects.create(brand_id="B", name="B")
        return Product.objects.create(product_uid=700001, name="MH", brand=brand)

    def test_create_mapping_ustawia_mapped_uid(self, mh_product):
        SagaService._create_matterhorn_product_with_mapping(
            {"product_id": mh_product.id}, mpd_product_id=555)

        mh_product.refresh_from_db()
        assert mh_product.mapped_product_uid == 555
        assert mh_product.is_mapped is True

    def test_create_mapping_rzuca_gdy_brak_produktu(self):
        with pytest.raises(Exception, match="not found"):
            SagaService._create_matterhorn_product_with_mapping(
                {"product_id": 99999999}, mpd_product_id=1)

    def test_delete_mapping_czysci(self, mh_product):
        mh_product.mapped_product_uid = 555
        mh_product.is_mapped = True
        mh_product.save()

        SagaService._delete_matterhorn_product_mapping({"product_id": mh_product.id})

        mh_product.refresh_from_db()
        assert mh_product.mapped_product_uid is None
        assert mh_product.is_mapped is False


class TestMpdAttributes:
    @pytest.fixture
    def product_and_attrs(self):
        p = Products.objects.using(MPD_DB).create(name="P attr")
        a1 = Attributes.objects.using(MPD_DB).create(name="wysoki stan")
        a2 = Attributes.objects.using(MPD_DB).create(name="usztywniane miseczki")
        return p, [a1.id, a2.id]

    def test_add_wpisuje_atrybuty(self, product_and_attrs):
        product, attr_ids = product_and_attrs
        res = SagaService._add_mpd_attributes(product.id, attr_ids)

        assert res["added_attributes"] == 2
        assert ProductAttribute.objects.using(MPD_DB).filter(product_id=product.id).count() == 2

    def test_add_pusta_lista_to_noop(self, product_and_attrs):
        product, _ = product_and_attrs
        assert SagaService._add_mpd_attributes(product.id, []) == {}

    def test_remove_usuwa_atrybuty(self, product_and_attrs):
        product, attr_ids = product_and_attrs
        SagaService._add_mpd_attributes(product.id, attr_ids)

        SagaService._remove_mpd_attributes(product.id, attr_ids)

        assert ProductAttribute.objects.using(MPD_DB).filter(product_id=product.id).count() == 0


class TestDeleteMpdProduct:
    def test_brak_id_to_noop(self):
        assert SagaService._delete_mpd_product({}, mpd_product_id=None) == {}

    def test_wola_api_mpd_z_delete(self):
        with patch("requests.delete") as mock_delete:
            mock_delete.return_value.status_code = 200
            SagaService._delete_mpd_product({}, mpd_product_id=123)

        mock_delete.assert_called_once()
        assert "/products/123/" in mock_delete.call_args[0][0]

    def test_blad_http_nie_rzuca(self):
        with patch("requests.delete", side_effect=RuntimeError("network down")):
            # fail-open — kompensacja nie może rzucać
            assert SagaService._delete_mpd_product({}, mpd_product_id=123) == {}
