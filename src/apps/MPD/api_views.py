import logging

from django.db.models import OuterRef, Q, Subquery
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import views as mpd_views
from .models import ProductImage, ProductPaths, Products
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
    authentication_classes = [TokenAuthentication]

    @extend_schema(
        summary="Lista produktów MPD",
        description=(
            "Zwraca listę produktów MPD z możliwością filtrowania po nazwie, "
            "marce (`brand_id`), widoczności (`visibility`) oraz kategorii/ścieżce "
            "(`path_id`). Obsługuje paginację poprzez parametry `page` i `page_size`."
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
                name="path_id",
                type=OpenApiTypes.INT,
                required=False,
                description="ID ścieżki/kategorii (product_path) — produkty przypisane do tej ścieżki.",
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                required=False,
                description="Rozmiar strony (1-200, domyślnie 50).",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                required=False,
                description=(
                    "Sortowanie listy. Dozwolone: id, name, brand_name, "
                    "visibility, updated_at, created_at. Prefiks `-` = malejąco "
                    "(np. `-updated_at`). Domyślnie: `-id`."
                ),
            ),
        ],
        responses={200: ProductListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """Lista produktów MPD z prostym filtrowaniem i paginacją."""
        first_image_path_subquery = (
            ProductImage.objects.filter(product_id=OuterRef('pk'))
            .order_by('id')
            .values('file_path')[:1]
        )
        queryset = (
            Products.objects.using('MPD')
            .select_related('brand')
            .annotate(first_image_path=Subquery(first_image_path_subquery))
        )

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

        path_id = request.query_params.get('path_id')
        if path_id:
            try:
                path_id_int = int(path_id)
            except (TypeError, ValueError):
                path_id_int = None
            if path_id_int is not None:
                product_ids = (
                    ProductPaths.objects.using('MPD')
                    .filter(path_id=path_id_int)
                    .values('product_id')
                )
                queryset = queryset.filter(id__in=product_ids)

        ordering_map = {
            'id': 'id',
            'name': 'name',
            'brand_name': 'brand__name',
            'visibility': 'visibility',
            'updated_at': 'updated_at',
            'created_at': 'created_at',
        }
        ordering_param = (request.query_params.get('ordering') or '-id').strip()
        descending = ordering_param.startswith('-')
        ordering_key = ordering_param.lstrip('-')
        order_field = ordering_map.get(ordering_key, 'id')
        if descending:
            order_field = f'-{order_field}'

        paginator = PageNumberPagination()
        page_size_param = request.query_params.get('page_size')
        if page_size_param:
            try:
                paginator.page_size = max(1, min(int(page_size_param), 200))
            except (TypeError, ValueError):
                paginator.page_size = 50
        else:
            paginator.page_size = 50

        # Stabilny tie-breaker: przy sortowaniu po id nie dubluj kolumny
        if order_field in ('id', '-id'):
            order_by_fields = (order_field,)
        else:
            order_by_fields = (order_field, '-id')
        page = paginator.paginate_queryset(
            queryset.order_by(*order_by_fields), request
        )
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
    authentication_classes = [TokenAuthentication]

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

    @extend_schema(
        summary="Usunięcie produktu MPD",
        description=(
            "Usuwa produkt MPD wraz z powiązaniami (jak w Django admin). "
            "Używa bazy MPD i uruchamia sygnały czyszczące mapowania."
        ),
        tags=["Products"],
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        try:
            product = Products.objects.using('MPD').get(pk=product_id)
        except Products.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Produkt nie istnieje.'},
                status=404,
            )
        product_name = product.name
        try:
            product.delete(using='MPD')
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception('Błąd usuwania produktu MPD %s', product_id)
            return Response(
                {
                    'status': 'error',
                    'message': f'Nie udało się usunąć produktu: {exc}',
                },
                status=500,
            )
        return Response(
            {
                'status': 'success',
                'message': f'Usunięto produkt „{product_name}”.',
                'product_id': product_id,
            }
        )


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

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

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

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

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

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

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


class MPDProductRetailPricesAPI(APIView):
    """API: zapis cen detalicznych wariantów produktu."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    @extend_schema(
        summary="Zapis cen detalicznych produktu",
        tags=["Products"],
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        return mpd_views.update_product_retail_prices(request._request, product_id=product_id)


class MPDCatalogAttributesAPI(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        from .models import Attributes
        rows = list(
            Attributes.objects.using('MPD').order_by('name').values('id', 'name')
        )
        return Response({'results': rows})


class MPDCatalogBrandsAPI(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        from .models import Brands
        rows = list(
            Brands.objects.using('MPD').order_by('name').values('id', 'name')
        )
        return Response({'results': rows})


class MPDCatalogFabricComponentsAPI(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        from .models import FabricComponent
        rows = list(
            FabricComponent.objects.using('MPD').order_by('name').values('id', 'name')
        )
        return Response({'results': rows})


class MPDCatalogPathsAPI(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        from .models import Paths
        rows = list(
            Paths.objects.using('MPD').order_by('path', 'name').values(
                'id', 'name', 'path', 'parent_id'
            )
        )
        return Response({'results': rows})


class MPDCatalogVatsAPI(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        from .models import Vat
        rows = list(
            Vat.objects.using('MPD').order_by('id').values('id', 'vat_rate')
        )
        return Response({'results': rows})


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
