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


def _mpd_db():
    """Alias bazy MPD – 'zzz_MPD' w dev/testach, 'MPD' na produkcji (spójnie z
    MPD.source_adapters/linking i registry, które też przez to przechodzą)."""
    from .source_adapters.registry import _get_mpd_db
    return _get_mpd_db()


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
                    'message': 'Nie udało się usunąć produktu.',
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


class MPDProductOrphanVariantsAPI(APIView):
    """
    API: warianty z hurtowni „nieprzypisane" (orphaned) do wariantów produktu MPD.

    GET  – lista wariantów źródłowych z produktów zmapowanych do tego produktu MPD,
           które nie mają jeszcze `mapped_variant_uid` (patrz
           `SourceAdapter.get_unmapped_variants_for_mpd_product`).
    POST – ręczne przypięcie takiego wariantu: do istniejącego wariantu MPD
           (`mode=existing`, `target_variant_id`) albo jako nowy wariant MPD
           (`mode=new`, `color_id`, opcjonalnie `producer_color_id` / `size_id` / `size_name`).
    """

    permission_classes = [IsAdminUser]
    authentication_classes = [TokenAuthentication]

    def get(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        from .source_adapters.registry import get_all_adapters, register_default_adapters
        from .models import Sources

        try:
            Products.objects.using(_mpd_db()).get(pk=product_id)
        except Products.DoesNotExist:
            return Response({'status': 'error', 'message': 'Produkt nie istnieje.'}, status=404)

        register_default_adapters()
        source_names = {
            s.id: s.name for s in Sources.objects.using(_mpd_db()).all()
        }
        results = []
        for source_id, adapter in get_all_adapters():
            try:
                matches = adapter.get_unmapped_variants_for_mpd_product(product_id)
            except Exception:  # pylint: disable=broad-except
                logger.exception(
                    'Błąd get_unmapped_variants_for_mpd_product source=%s product=%s',
                    source_id, product_id,
                )
                continue
            for m in matches:
                results.append({
                    'source_id': source_id,
                    'source_name': source_names.get(source_id),
                    'ean': m.ean or '',
                    'variant_uid': str(m.variant_uid) if m.variant_uid is not None else '',
                    'source_product_id': m.source_product_id,
                    'size': m.size or '',
                    'color': m.color or '',
                    'stock': m.stock,
                    'price': float(m.price) if m.price is not None else None,
                    'currency': m.currency or 'PLN',
                    'producer_code': m.producer_code or '',
                })
        results.sort(key=lambda r: (r['source_name'] or '', r['color'], r['size']))
        return Response({'status': 'success', 'results': results})

    def post(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        from django.utils import timezone
        from .source_adapters.registry import get_adapter_for_source, register_default_adapters
        from .models import (
            ProductVariants,
            ProductvariantsSources,
            Sizes,
            Sources,
            StockAndPrices,
        )

        data = request.data if isinstance(request.data, dict) else {}
        try:
            source_id = int(data['source_id'])
        except (KeyError, TypeError, ValueError):
            return Response({'status': 'error', 'message': 'Wymagane pole source_id.'}, status=400)

        source_variant_uid = str(data.get('source_variant_uid') or '').strip()
        source_product_id = data.get('source_product_id')
        ean = (data.get('ean') or '').strip()
        producer_code = (data.get('producer_code') or '').strip()[:255] or None
        mode = (data.get('mode') or 'existing').strip()

        try:
            product = Products.objects.using(_mpd_db()).get(pk=product_id)
        except Products.DoesNotExist:
            return Response({'status': 'error', 'message': 'Produkt nie istnieje.'}, status=404)

        try:
            source = Sources.objects.using(_mpd_db()).get(pk=source_id)
        except Sources.DoesNotExist:
            return Response({'status': 'error', 'message': 'Źródło nie istnieje.'}, status=404)

        register_default_adapters()
        adapter = get_adapter_for_source(source_id)
        if adapter is None:
            return Response(
                {'status': 'error', 'message': f'Brak adaptera dla źródła {source.name}.'},
                status=400,
            )

        if mode == 'new':
            color_id = data.get('color_id')
            if not color_id:
                return Response(
                    {'status': 'error', 'message': 'Tryb „new" wymaga color_id.'},
                    status=400,
                )
            producer_color_id = data.get('producer_color_id') or None
            size_id = data.get('size_id') or None
            if not size_id and (data.get('size_name') or '').strip():
                size_name = data['size_name'].strip()[:255]
                size_obj = (
                    Sizes.objects.using(_mpd_db()).filter(name__iexact=size_name).first()
                    or Sizes.objects.using(_mpd_db()).create(
                        name=size_name,
                        name_lower=size_name.lower(),
                    )
                )
                size_id = size_obj.id
            variant = ProductVariants.objects.using(_mpd_db()).create(
                product=product,
                color_id=color_id,
                producer_color_id=producer_color_id,
                size_id=size_id,
            )
        else:
            try:
                variant = ProductVariants.objects.using(_mpd_db()).get(
                    variant_id=data['target_variant_id'], product_id=product_id,
                )
            except (KeyError, TypeError, ValueError, ProductVariants.DoesNotExist):
                return Response(
                    {'status': 'error', 'message': 'Nieprawidłowy target_variant_id.'},
                    status=400,
                )

        # PG integer (32-bit); identyfikatory oparte na EAN przekraczają zakres → null
        variant_uid_int = (
            int(source_variant_uid)
            if source_variant_uid.isdigit() and int(source_variant_uid) <= 2_147_483_647
            else None
        )
        pvs, _created = ProductvariantsSources.objects.using(_mpd_db()).get_or_create(
            variant_id=variant.variant_id,
            source=source,
            defaults={
                'ean': ean[:50],
                'variant_uid': variant_uid_int,
                'producer_code': producer_code,
            },
        )
        stock_val = data.get('stock')
        price_val = data.get('price')
        StockAndPrices.objects.using(_mpd_db()).get_or_create(
            variant_id=variant.variant_id,
            source=source,
            defaults={
                'stock': stock_val if stock_val is not None else 0,
                'price': price_val if price_val is not None else 0,
                'currency': (data.get('currency') or 'PLN'),
                'last_updated': timezone.now(),
            },
        )

        if source_product_id:
            try:
                adapter.update_source_variant_mapped(
                    int(source_product_id), source_variant_uid or None, variant.variant_id,
                )
                adapter.update_source_product_mapped(int(source_product_id), product_id)
            except Exception:  # pylint: disable=broad-except
                logger.exception(
                    'Błąd ustawiania mapped_* w źródle %s dla wariantu %s',
                    source_id, source_variant_uid,
                )

        return Response({
            'status': 'success',
            'message': 'Wariant przypięty.',
            'variant_id': variant.variant_id,
        })


class MPDProductImagesImportAPI(APIView):
    """
    API: import zdjęć z galerii pozostałych hurtowni do „tacki" produktu MPD.

    POST – dla każdego źródła z adapterem: bierze produkty źródłowe zmapowane do tego
    produktu MPD, pobiera ich galerię (`SourceAdapter.get_gallery_images_for_mpd_product`),
    re-uploaduje do bucketa i zapisuje w `product_images` z `producer_color=NULL`
    (kolor przypisuje się ręcznie – drag&drop). Dedup po `origin_url`.
    """

    permission_classes = [IsAdminUser]
    authentication_classes = [TokenAuthentication]

    def post(self, request, product_id, *args, **kwargs):  # pylint: disable=unused-argument
        from matterhorn1.defs_db import upload_image_to_bucket_and_get_url
        from .source_adapters.registry import get_all_adapters, register_default_adapters
        from .models import ProductImage, Sources

        try:
            Products.objects.using(_mpd_db()).get(pk=product_id)
        except Products.DoesNotExist:
            return Response({'status': 'error', 'message': 'Produkt nie istnieje.'}, status=404)

        register_default_adapters()
        source_names = {s.id: s.name for s in Sources.objects.using(_mpd_db()).all()}
        existing_origins = set(
            ProductImage.objects.using(_mpd_db())
            .filter(product_id=product_id)
            .exclude(origin_url__isnull=True)
            .exclude(origin_url='')
            .values_list('origin_url', flat=True)
        )

        imported, skipped, errors = 0, 0, []
        for source_id, adapter in get_all_adapters():
            try:
                gallery = adapter.get_gallery_images_for_mpd_product(product_id)
            except Exception:  # pylint: disable=broad-except
                logger.exception('Błąd galerii source=%s product=%s', source_id, product_id)
                continue
            for idx, img in enumerate(gallery, start=1):
                url = (img or {}).get('url')
                if not url:
                    continue
                if url in existing_origins:
                    skipped += 1
                    continue
                try:
                    key = upload_image_to_bucket_and_get_url(
                        image_path=url,
                        product_id=product_id,
                        producer_color_name=f'src{source_id}',
                        image_number=idx,
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.exception('Upload zdjęcia %s nieudany', url)
                    errors.append(str(exc))
                    continue
                if not key:
                    errors.append(f'upload nieudany: {url}')
                    continue
                ProductImage.objects.using(_mpd_db()).create(
                    product_id=product_id,
                    file_path=key,
                    producer_color=None,
                    source_id=source_id,
                    origin_url=url,
                )
                existing_origins.add(url)
                imported += 1

        return Response({
            'status': 'success',
            'imported': imported,
            'skipped': skipped,
            'errors': errors,
            'message': f'Zaimportowano {imported}, pominięto {skipped}.',
        })


class MPDProductImageDetailAPI(APIView):
    """
    API: pojedyncze zdjęcie produktu MPD.

    PATCH  – przypisanie/zdjęcie koloru (`producer_color_id`; null = z powrotem do tacki).
    DELETE – trwałe usunięcie zdjęcia (wiersz + obiekt w buckecie).
    """

    permission_classes = [IsAdminUser]
    authentication_classes = [TokenAuthentication]

    def _get_image(self, product_id, image_id):
        from .models import ProductImage
        return ProductImage.objects.using(_mpd_db()).filter(
            pk=image_id, product_id=product_id,
        ).first()

    def patch(self, request, product_id, image_id, *args, **kwargs):  # pylint: disable=unused-argument
        from .models import Colors

        image = self._get_image(product_id, image_id)
        if image is None:
            return Response({'status': 'error', 'message': 'Zdjęcie nie istnieje.'}, status=404)

        data = request.data if isinstance(request.data, dict) else {}
        if 'producer_color_id' not in data:
            return Response(
                {'status': 'error', 'message': 'Wymagane pole producer_color_id (może być null).'},
                status=400,
            )
        pcid = data.get('producer_color_id')
        if pcid in (None, '', 'null'):
            image.producer_color = None
        else:
            try:
                image.producer_color = Colors.objects.using(_mpd_db()).get(pk=int(pcid))
            except (TypeError, ValueError, Colors.DoesNotExist):
                return Response(
                    {'status': 'error', 'message': 'Nieprawidłowy producer_color_id.'},
                    status=400,
                )
        image.save(using=_mpd_db(), update_fields=['producer_color'])
        return Response({
            'status': 'success',
            'message': 'Zaktualizowano.',
            'image_id': image.id,
            'producer_color_id': image.producer_color_id,
        })

    def delete(self, request, product_id, image_id, *args, **kwargs):  # pylint: disable=unused-argument
        from matterhorn1.defs_db import delete_object_from_bucket

        image = self._get_image(product_id, image_id)
        if image is None:
            return Response({'status': 'error', 'message': 'Zdjęcie nie istnieje.'}, status=404)
        file_path = image.file_path
        image.delete(using=_mpd_db())
        try:
            delete_object_from_bucket(file_path)
        except Exception:  # pylint: disable=broad-except
            logger.exception('Nie udało się usunąć obiektu %s z bucketa', file_path)
        return Response({'status': 'success', 'message': 'Zdjęcie usunięte.', 'image_id': image_id})


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
