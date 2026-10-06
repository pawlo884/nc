"""
Integration: `matterhorn1/views.py` — legacy bulk API. **Nie jest martwym
kodem**: to równoległy (starszy, bez DRF permission_classes) zestaw
endpointów obok `views_secure.py`, oba routowane w `urls.py`
(`.../bulk/create/` vs `.../bulk/create-secure/`). Od PR #110
(`security/lock-legacy-api-endpoints`) chroniony przez
`core.legacy_auth.admin_required` / `AdminRequiredMixin` — sesja admina
albo `Authorization: Token <key>`, w przeciwnym razie 401/403.

Testujemy: (1) że blokada auth faktycznie działa (funkcyjny dekorator +
mixin klasowy), (2) że `ProductBulkCreateView` — reprezentatywny bulk
endpoint — poprawnie tworzy produkty przez `ProductSerializer`.
"""
from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from rest_framework.authtoken.models import Token

from matterhorn1.models import ApiSyncLog, Product
from matterhorn1.views import ProductBulkCreateView, get_product_details

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases=["default"])]


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user("mh_staff", is_staff=True)


@pytest.fixture
def normal_user(django_user_model):
    return django_user_model.objects.create_user("mh_normal", is_staff=False)


class TestLegacyAuthBoundary:
    """`admin_required` (dekorator funkcyjny) na `get_product_details`."""

    def test_brak_atrybutu_user_401(self):
        request = RequestFactory().get("/")
        response = get_product_details(request, product_id=1)
        assert response.status_code == 401

    def test_anonimowy_401(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        assert get_product_details(request, product_id=1).status_code == 401

    def test_zalogowany_nie_staff_403(self, normal_user):
        request = RequestFactory().get("/")
        request.user = normal_user
        assert get_product_details(request, product_id=1).status_code == 403

    def test_staff_przechodzi_dalej(self, staff_user):
        request = RequestFactory().get("/")
        request.user = staff_user
        # przeszedł auth -> trafia w logikę widoku, produkt nie istnieje = 404
        assert get_product_details(request, product_id=999999).status_code == 404

    def test_token_naglowka_akceptowany(self, staff_user):
        token = Token.objects.create(user=staff_user)
        request = RequestFactory().get("/", HTTP_AUTHORIZATION=f"Token {token.key}")
        assert get_product_details(request, product_id=999999).status_code == 404

    def test_bledny_token_401(self):
        request = RequestFactory().get("/", HTTP_AUTHORIZATION="Token nieistniejacy")
        assert get_product_details(request, product_id=1).status_code == 401


class TestGetProductDetailsHappyPath:
    def test_zwraca_dane_produktu(self, staff_user):
        from matterhorn1.models import Brand

        brand = Brand.objects.create(brand_id="LEG", name="Legacy Brand")
        product = Product.objects.create(
            product_uid=900100, name="Legacy produkt", brand=brand)

        request = RequestFactory().get("/")
        request.user = staff_user
        response = get_product_details(request, product_id=product.product_uid)

        payload = json.loads(response.content)
        assert payload["success"] is True
        assert payload["product"]["name"] == "Legacy produkt"
        assert payload["product"]["brand"]["name"] == "Legacy Brand"


class TestProductBulkCreateView:
    """`AdminRequiredMixin` (mixin klasowy) + logika bulk create."""

    def test_bez_auth_401(self):
        request = RequestFactory().post(
            "/", data=json.dumps([]), content_type="application/json")
        response = ProductBulkCreateView.as_view()(request)
        assert response.status_code == 401

    def test_tworzy_produkty_przez_serializer(self, staff_user):
        payload = [{
            "product_id": 900200,
            "name": "Bulk legacy produkt",
            "brand_id": "LEGB",
            "category_id": "LEGC",
        }]
        request = RequestFactory().post(
            "/", data=json.dumps(payload), content_type="application/json")
        request.user = staff_user

        response = ProductBulkCreateView.as_view()(request)

        out = json.loads(response.content)
        assert out["success"] is True
        assert out["created_count"] == 1
        product = Product.objects.get(product_uid=900200)
        assert product.brand.brand_id == "LEGB"
        assert ApiSyncLog.objects.filter(sync_type="products_bulk_create", status="success").exists()

    def test_niepoprawny_json_400(self, staff_user):
        request = RequestFactory().post(
            "/", data="nie-jest-jsonem", content_type="application/json")
        request.user = staff_user

        response = ProductBulkCreateView.as_view()(request)

        assert response.status_code == 400
        assert json.loads(response.content)["success"] is False

    def test_dane_nie_sa_lista_400(self, staff_user):
        request = RequestFactory().post(
            "/", data=json.dumps({"nie": "lista"}), content_type="application/json")
        request.user = staff_user

        response = ProductBulkCreateView.as_view()(request)

        assert response.status_code == 400

    def test_niepoprawny_produkt_w_liscie_odrzuca_caly_request(self, staff_user):
        """`BulkProductSerializer.products` (many=True ProductSerializer) waliduje
        każdy element tym samym serializerem co pętla zapisu niżej w widoku — jeden
        strukturalnie niepoprawny element odrzuca cały request na etapie
        `bulk_serializer.is_valid()`, zanim cokolwiek zostanie zapisane. Pętla
        `for product_data in data: ... else: errors.append(...)` w widoku obsługuje
        tylko błędy nieuchwycone na tym wcześniejszym etapie (np. zapisu)."""
        payload = [
            {"product_id": 900300, "name": "OK produkt"},
            {"name": "Brak product_id"},  # product_id wymagane -> błąd walidacji
        ]
        request = RequestFactory().post(
            "/", data=json.dumps(payload), content_type="application/json")
        request.user = staff_user

        response = ProductBulkCreateView.as_view()(request)

        assert response.status_code == 400
        out = json.loads(response.content)
        assert out["success"] is False
        assert "details" in out
        assert not Product.objects.filter(product_uid=900300).exists()
