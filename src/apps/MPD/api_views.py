import logging

from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView

from . import views as mpd_views
from .models import Products
from .serializers import ProductListSerializer

# Import drf_spectacular tylko jeśli jest dostępny
try:
    from drf_spectacular.utils import (
        OpenApiParameter,
        OpenApiTypes,
        extend_schema,
    )
    DRF_SPECTACULAR_AVAILABLE = True
except ImportError:  # pragma: no cover - środowisko bez drf_spectacular
    DRF_SPECTACULAR_AVAILABLE = False

    def extend_schema(*args, **kwargs):  # type: ignore[override]
        def decorator(obj):
            return obj

        return decorator

    class OpenApiParameter:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            pass

    class OpenApiTypes:  # type: ignore[override]
        STR = None
        INT = None
        BOOL = None

logger = logging.getLogger(__name__)


class MPDProductCreateAPI(APIView):
    """
    API: tworzenie produktu MPD.

    Deleguje do istniejącego widoku `create_product`, nie zmieniając logiki.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Lista produktów MPD",
        description=(
            "Zwraca listę produktów MPD z możliwością filtrowania po nazwie, "
            "marce (`brand_id`) oraz widoczności (`visibility`). "
            "Obsługuje paginację poprzez parametry `page` i `page_size`."
        ),
        tags=["Products"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                required=False,
                description="Fragment nazwy produktu lub nazwy marki.",
            ),
            OpenApiParameter(
                name="brand_id",
                type=OpenApiTypes.INT,
                required=False,
                description="ID marki, po którym filtrowane są produkty.",
            ),
            OpenApiParameter(
                name="visibility",
                type=OpenApiTypes.BOOL,
                required=False,
                description=(
                    "Filtr widoczności produktu. Akceptowane wartości: "
                    "`true/1/yes/y` lub `false/0/no/n`."
                ),
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                required=False,
                description="Rozmiar strony (1-200, domyślnie 50).",
            ),
        ],
        responses={200: ProductListSerializer(many=True)},
    )
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

    @extend_schema(
        summary="Utworzenie produktu MPD",
        description=(
            "Tworzy nowy produkt MPD. Logika tworzenia jest "
            "delegowana do istniejącego widoku `create_product`, "
            "dzięki czemu zachowane są wszystkie dotychczasowe zasady walidacji."
        ),
        tags=["Products"],
        request=OpenApiTypes.OBJECT,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.create_product(request._request)


class MPDProductDetailAPI(APIView):
    """
    API: pobieranie i aktualizacja produktu MPD.

    Deleguje do istniejących widoków `get_product` oraz `update_product`.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Szczegóły produktu MPD",
        description="Zwraca szczegóły pojedynczego produktu MPD.",
        tags=["Products"],
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.get_product(request._request, product_id=product_id)

    @extend_schema(
        summary="Aktualizacja produktu MPD (PUT)",
        description="Pełna aktualizacja danych produktu MPD.",
        tags=["Products"],
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def put(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.update_product(request._request, product_id=product_id)

    @extend_schema(
        summary="Częściowa aktualizacja produktu MPD (PATCH)",
        description="Częściowa aktualizacja danych produktu MPD.",
        tags=["MPD / Products"],
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def patch(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.update_product(request._request, product_id=product_id)


class MPDBulkCreateProductsAPI(APIView):
    """
    API: bulk tworzenie produktów MPD.

    Deleguje do istniejącego widoku `bulk_create_products`.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Bulk tworzenie produktów MPD",
        description=(
            "Przyjmuje listę produktów i tworzy je w bazie MPD w trybie bulk. "
            "Logika tworzenia delegowana jest do widoku `bulk_create_products`."
        ),
        tags=["MPD / Products"],
        request=OpenApiTypes.OBJECT,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.bulk_create_products(request._request)


class MPDManageProductPathsAPI(APIView):
    """
    API: zarządzanie ścieżkami produktów (assign/unassign).

    Deleguje do istniejącego widoku `manage_product_paths`.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Zarządzanie ścieżkami produktów",
        description=(
            "Endpoint do przypisywania/odpinania ścieżek/kategorii produktów. "
            "Deleguje logikę do widoku `manage_product_paths`."
        ),
        tags=["Database"],
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.manage_product_paths(request._request)


class MPDManageProductFabricAPI(APIView):
    """
    API: zarządzanie składem materiałowym produktów.

    Deleguje do istniejącego widoku `manage_product_fabric`.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Zarządzanie składem materiałowym produktów",
        description=(
            "Endpoint do modyfikacji składu materiałowego produktów. "
            "Deleguje logikę do widoku `manage_product_fabric`."
        ),
        tags=["Database"],
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.manage_product_fabric(request._request)


class MPDManageProductAttributesAPI(APIView):
    """
    API: zarządzanie atrybutami produktów.

    Deleguje do istniejącego widoku `manage_product_attributes`.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Zarządzanie atrybutami produktów",
        description=(
            "Endpoint do dodawania/usuwania atrybutów produktów. "
            "Deleguje logikę do widoku `manage_product_attributes`."
        ),
        tags=["Database"],
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.manage_product_attributes(request._request)


class MPDBulkMapFromMatterhorn1API(APIView):
    """
    API: bulk mapowanie produktów z matterhorn1 do MPD.

    Deleguje do istniejącego widoku `bulk_map_from_matterhorn1`.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Bulk mapowanie produktów z matterhorn1 do MPD",
        description=(
            "Wykonuje masowe mapowanie produktów z bazy matterhorn1 do bazy MPD. "
            "Deleguje logikę do widoku `bulk_map_from_matterhorn1`."
        ),
        tags=["Sync"],
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.bulk_map_from_matterhorn1(request._request)


class MPDGetMatterhorn1ProductsAPI(APIView):
    """
    API: pobieranie produktów z matterhorn1 do mapowania.

    Deleguje do istniejącego widoku `get_matterhorn1_products`.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Lista produktów z matterhorn1",
        description=(
            "Zwraca listę produktów z bazy matterhorn1 do dalszego mapowania w MPD. "
            "Deleguje logikę do widoku `get_matterhorn1_products`."
        ),
        tags=["Sync"],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.get_matterhorn1_products(request._request)


class MPDUpdateProducerCodeAPI(APIView):
    """
    API: aktualizacja kodu producenta wariantu.

    Deleguje do istniejącego widoku `update_producer_code`.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Aktualizacja kodu producenta wariantu",
        description=(
            "Aktualizuje kod producenta dla wybranych wariantów produktów MPD. "
            "Deleguje logikę do widoku `update_producer_code`."
        ),
        tags=["Variants"],
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.update_producer_code(request._request)
