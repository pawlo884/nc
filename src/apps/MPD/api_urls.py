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
        "products/<int:product_id>/retail-prices/",
        api_views.MPDProductRetailPricesAPI.as_view(),
        name="products-retail-prices",
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
    path(
        "catalog/attributes/",
        api_views.MPDCatalogAttributesAPI.as_view(),
        name="catalog-attributes",
    ),
    path(
        "catalog/brands/",
        api_views.MPDCatalogBrandsAPI.as_view(),
        name="catalog-brands",
    ),
    path(
        "catalog/fabric-components/",
        api_views.MPDCatalogFabricComponentsAPI.as_view(),
        name="catalog-fabric-components",
    ),
    path(
        "catalog/paths/",
        api_views.MPDCatalogPathsAPI.as_view(),
        name="catalog-paths",
    ),
    path(
        "catalog/vats/",
        api_views.MPDCatalogVatsAPI.as_view(),
        name="catalog-vats",
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

