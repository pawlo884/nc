import logging

from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView

from . import views as mpd_views

logger = logging.getLogger(__name__)


class MPDProductCreateAPI(APIView):
    """
    API: tworzenie produktu MPD.

    Deleguje do istniejącego widoku `create_product`, nie zmieniając logiki.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.create_product(request._request)


class MPDProductDetailAPI(APIView):
    """
    API: pobieranie i aktualizacja produktu MPD.

    Deleguje do istniejących widoków `get_product` oraz `update_product`.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.get_product(request._request, product_id=product_id)

    def put(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.update_product(request._request, product_id=product_id)

    def patch(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.update_product(request._request, product_id=product_id)


class MPDBulkCreateProductsAPI(APIView):
    """
    API: bulk tworzenie produktów MPD.

    Deleguje do istniejącego widoku `bulk_create_products`.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.bulk_create_products(request._request)


class MPDManageProductPathsAPI(APIView):
    """
    API: zarządzanie ścieżkami produktów (assign/unassign).

    Deleguje do istniejącego widoku `manage_product_paths`.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.manage_product_paths(request._request)


class MPDManageProductFabricAPI(APIView):
    """
    API: zarządzanie składem materiałowym produktów.

    Deleguje do istniejącego widoku `manage_product_fabric`.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.manage_product_fabric(request._request)


class MPDManageProductAttributesAPI(APIView):
    """
    API: zarządzanie atrybutami produktów.

    Deleguje do istniejącego widoku `manage_product_attributes`.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.manage_product_attributes(request._request)


class MPDBulkMapFromMatterhorn1API(APIView):
    """
    API: bulk mapowanie produktów z matterhorn1 do MPD.

    Deleguje do istniejącego widoku `bulk_map_from_matterhorn1`.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.bulk_map_from_matterhorn1(request._request)


class MPDGetMatterhorn1ProductsAPI(APIView):
    """
    API: pobieranie produktów z matterhorn1 do mapowania.

    Deleguje do istniejącego widoku `get_matterhorn1_products`.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.get_matterhorn1_products(request._request)


class MPDUpdateProducerCodeAPI(APIView):
    """
    API: aktualizacja kodu producenta wariantu.

    Deleguje do istniejącego widoku `update_producer_code`.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.update_producer_code(request._request)
