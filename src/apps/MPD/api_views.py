import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import views as mpd_views
from .models import Products
from .serializers import ProductListSerializer

logger = logging.getLogger(__name__)


class MPDProductCreateAPI(APIView):
    """
    API: tworzenie produktu MPD.

    Deleguje do istniejącego widoku `create_product`, nie zmieniając logiki.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """Lista produktów MPD z prostym filtrowaniem i paginacją."""
        queryset = Products.objects.using('MPD').all()

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(brand__name__icontains=search)
            )

        brand_id = request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        visibility = request.query_params.get('visibility')
        if visibility is not None:
            visibility = visibility.lower()
            if visibility in ('true', '1', 'yes', 'y'):
                queryset = queryset.filter(visibility=True)
            elif visibility in ('false', '0', 'no', 'n'):
                queryset = queryset.filter(visibility=False)

        paginator = PageNumberPagination()
        page_size_param = request.query_params.get('page_size')
        if page_size_param:
            try:
                paginator.page_size = max(1, min(int(page_size_param), 200))
            except (TypeError, ValueError):
                paginator.page_size = 50
        else:
            paginator.page_size = 50

        page = paginator.paginate_queryset(queryset.order_by('id'), request)
        serializer = ProductListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

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
