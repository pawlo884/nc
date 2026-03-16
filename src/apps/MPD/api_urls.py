from django.urls import path

from . import api_views

app_name = "mpd_api"

urlpatterns = [
    # Produkty MPD
    path(
        "products/",
        api_views.MPDProductCreateAPI.as_view(),
        name="products-create",
    ),
    path(
        "products/<int:product_id>/",
        api_views.MPDProductDetailAPI.as_view(),
        name="products-detail",
    ),
    path(
        "products/bulk-create/",
        api_views.MPDBulkCreateProductsAPI.as_view(),
        name="products-bulk-create",
    ),
    # Zarządzanie relacjami produktu
    path(
        "products/manage-paths/",
        api_views.MPDManageProductPathsAPI.as_view(),
        name="products-manage-paths",
    ),
    path(
        "products/manage-fabric/",
        api_views.MPDManageProductFabricAPI.as_view(),
        name="products-manage-fabric",
    ),
    path(
        "products/manage-attributes/",
        api_views.MPDManageProductAttributesAPI.as_view(),
        name="products-manage-attributes",
    ),
    # Integracja z matterhorn1
    path(
        "matterhorn1/products/",
        api_views.MPDGetMatterhorn1ProductsAPI.as_view(),
        name="matterhorn1-products",
    ),
    path(
        "matterhorn1/bulk-map/",
        api_views.MPDBulkMapFromMatterhorn1API.as_view(),
        name="matterhorn1-bulk-map",
    ),
    # Aktualizacja kodu producenta
    path(
        "variants/update-producer-code/",
        api_views.MPDUpdateProducerCodeAPI.as_view(),
        name="variants-update-producer-code",
    ),
]

