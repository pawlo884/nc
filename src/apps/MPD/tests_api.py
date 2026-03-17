"""
Testy API dla nowych endpointów /api/mpd/.

Sprawdzają tylko poprawne wpięcie pod DRF (auth, statusy, brak 404),
logika zostaje po stronie istniejących widoków w MPD/views.py.
"""

from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase, APIClient

from MPD.models import Brands, Products


DEBUG_TOOLBAR_OFF = {"SHOW_TOOLBAR_CALLBACK": lambda request: False}


@override_settings(DEBUG_TOOLBAR_CONFIG=DEBUG_TOOLBAR_OFF)
class MPDProductsAPITest(APITestCase):
    """Testy podstawowych endpointów produktów MPD pod /api/mpd/."""

    databases = {"default", "MPD"}

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)

        self.brand = Brands.objects.create(name="Test Brand")
        self.product = Products.objects.create(
            name="Test Product",
            description="Desc",
            short_description="Short",
            brand=self.brand,
            visibility=True,
        )

    def test_products_create_requires_auth(self):
        """POST /api/mpd/products/ wymaga autoryzacji."""
        client = APIClient()
        response = client.post("/api/mpd/products/", {}, format="json")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_products_list_requires_auth(self):
        """GET /api/mpd/products/ wymaga autoryzacji."""
        client = APIClient()
        response = client.get("/api/mpd/products/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_products_list_returns_data(self):
        """GET /api/mpd/products/ zwraca poprawnie paginowaną listę produktów."""
        # dodaj drugi produkt, żeby lista nie była pusta
        Products.objects.create(
            name="Another Product",
            description="Other",
            short_description="Other short",
            brand=self.brand,
            visibility=False,
        )

        url = "/api/mpd/products/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        # struktura odpowiedzi powinna zawierać listę wyników
        results = response.data["results"]
        self.assertIsInstance(results, list)
        if results:
            first = results[0]
            self.assertIn("id", first)
            self.assertIn("name", first)
            self.assertIn("brand_name", first)

    def test_products_detail_requires_auth(self):
        """GET /api/mpd/products/{id}/ wymaga autoryzacji."""
        client = APIClient()
        url = f"/api/mpd/products/{self.product.id}/"
        response = client.get(url)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_products_detail_exists(self):
        """GET /api/mpd/products/{id}/ jest poprawnie zarejestrowany (nie 405/501)."""
        url = f"/api/mpd/products/{self.product.id}/"
        response = self.client.get(url)
        self.assertNotIn(
            response.status_code,
            [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_501_NOT_IMPLEMENTED],
        )


@override_settings(DEBUG_TOOLBAR_CONFIG=DEBUG_TOOLBAR_OFF)
class MPDAdminOnlyAPITest(APITestCase):
    """Testy endpointów wymagających uprawnień admina pod /api/mpd/."""

    databases = {"default", "MPD"}

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.admin_token = Token.objects.create(user=self.admin)

        self.user = User.objects.create_user(
            username="regular",
            password="regularpass123",
        )
        self.user_token = Token.objects.create(user=self.user)

    def _admin_client(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        return client

    def _user_client(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token " + self.user_token.key)
        return client

    def test_bulk_create_requires_admin(self):
        """POST /api/mpd/products/bulk-create/ wymaga admina."""
        url = "/api/mpd/products/bulk-create/"

        response_user = self._user_client().post(url, {}, format="json")
        self.assertEqual(response_user.status_code, status.HTTP_403_FORBIDDEN)

        response_admin = self._admin_client().post(url, {}, format="json")
        self.assertNotEqual(response_admin.status_code, status.HTTP_404_NOT_FOUND)

    def test_manage_paths_requires_admin(self):
        """POST /api/mpd/products/manage-paths/ wymaga admina."""
        url = "/api/mpd/products/manage-paths/"

        response_user = self._user_client().post(url, {}, format="json")
        self.assertEqual(response_user.status_code, status.HTTP_403_FORBIDDEN)

        response_admin = self._admin_client().post(url, {}, format="json")
        self.assertNotEqual(response_admin.status_code, status.HTTP_404_NOT_FOUND)

    def test_manage_fabric_requires_admin(self):
        """POST /api/mpd/products/manage-fabric/ wymaga admina."""
        url = "/api/mpd/products/manage-fabric/"

        response_user = self._user_client().post(url, {}, format="json")
        self.assertEqual(response_user.status_code, status.HTTP_403_FORBIDDEN)

        response_admin = self._admin_client().post(url, {}, format="json")
        self.assertNotEqual(response_admin.status_code, status.HTTP_404_NOT_FOUND)

    def test_manage_attributes_requires_admin(self):
        """POST /api/mpd/products/manage-attributes/ wymaga admina."""
        url = "/api/mpd/products/manage-attributes/"

        response_user = self._user_client().post(url, {}, format="json")
        self.assertEqual(response_user.status_code, status.HTTP_403_FORBIDDEN)

        response_admin = self._admin_client().post(url, {}, format="json")
        self.assertNotEqual(response_admin.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_map_from_matterhorn1_requires_admin(self):
        """POST /api/mpd/matterhorn1/bulk-map/ wymaga admina."""
        url = "/api/mpd/matterhorn1/bulk-map/"

        response_user = self._user_client().post(url, {}, format="json")
        self.assertEqual(response_user.status_code, status.HTTP_403_FORBIDDEN)

        response_admin = self._admin_client().post(url, {}, format="json")
        self.assertNotEqual(response_admin.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_producer_code_requires_admin(self):
        """POST /api/mpd/variants/update-producer-code/ wymaga admina."""
        url = "/api/mpd/variants/update-producer-code/"

        response_user = self._user_client().post(url, {}, format="json")
        self.assertEqual(response_user.status_code, status.HTTP_403_FORBIDDEN)

        response_admin = self._admin_client().post(url, {}, format="json")
        self.assertNotEqual(response_admin.status_code, status.HTTP_404_NOT_FOUND)
