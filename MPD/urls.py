from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductSetViewSet, products, test_connection, test_table_structure, export_xml, export_full_xml, get_xml_file, xml_links, get_gateway_xml, generate_full_xml, generate_full_change_xml, generate_gateway_xml, generate_gateway_xml_api, empty_xml, generate_light_xml, generate_producers_xml, generate_stocks_xml, generate_units_xml, generate_categories_xml, generate_sizes_xml, generate_parameters_xml, generate_series_xml, generate_warranties_xml, generate_preset_xml, manage_product_paths, manage_product_attributes, manage_product_fabric, create_product, update_product, get_product, bulk_create_products, bulk_map_from_matterhorn1, get_matterhorn1_products, product_mapping

router = DefaultRouter()
router.register(r'product-sets', ProductSetViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('products/', products, name='products'),
    path('product-mapping/', product_mapping, name='product_mapping'),
    path('test-connection/', test_connection, name='test_connection'),
    path('test-structure/', test_table_structure, name='test_structure'),
    path('export-xml/<str:source_name>/', export_xml, name='export_xml'),
    path('export-full-xml/', export_full_xml, name='export_full_xml'),
    path('generate-full-xml/', generate_full_xml, name='generate_full_xml'),
    path('generate-full-change-xml/', generate_full_change_xml,
         name='generate_full_change_xml'),
    path('generate-light-xml/', generate_light_xml, name='generate_light_xml'),
    path('generate-producers-xml/', generate_producers_xml,
         name='generate_producers_xml'),
    path('generate-stocks-xml/', generate_stocks_xml, name='generate_stocks_xml'),
    path('generate-gateway-xml/<str:source_name>/',
         generate_gateway_xml, name='generate_gateway_xml'),
    path('empty-xml/', empty_xml, name='empty_xml'),
    path('get-xml/<str:xml_type>/', get_xml_file, name='get_xml_file'),
    path('get-gateway-xml/', get_gateway_xml, name='get_gateway_xml'),
    path('xml-links/', xml_links, name='xml_links'),
    path('generate-units-xml/', generate_units_xml, name='generate_units_xml'),
    path('generate-categories-xml/', generate_categories_xml,
         name='generate_categories_xml'),
    path('generate-sizes-xml/', generate_sizes_xml, name='generate_sizes_xml'),
    path('generate-parameters-xml/', generate_parameters_xml,
         name='generate_parameters_xml'),
    path('generate-series-xml/', generate_series_xml, name='generate_series_xml'),
    path('generate-warranties-xml/', generate_warranties_xml,
         name='generate_warranties_xml'),
    path('generate-preset-xml/', generate_preset_xml, name='generate_preset_xml'),
    path('generate-gateway-xml-api/', generate_gateway_xml_api,
         name='generate_gateway_xml_api'),
    path('manage-product-paths/', manage_product_paths,
         name='manage_product_paths'),
    path('manage-product-attributes/', manage_product_attributes,
         name='manage_product_attributes'),
    path('manage-product-fabric/', manage_product_fabric,
         name='manage_product_fabric'),
    path('products/create/', create_product, name='create_product'),
    path('products/<int:product_id>/', get_product, name='get_product'),
    path('products/<int:product_id>/update/',
         update_product, name='update_product'),
    # Bulk operations
    path('bulk-create/', bulk_create_products, name='bulk_create_products'),
    # Mapowanie produktów z matterhorn1
    path('matterhorn1/products/', get_matterhorn1_products,
         name='get_matterhorn1_products'),
    path('matterhorn1/bulk-map/', bulk_map_from_matterhorn1,
         name='bulk_map_from_matterhorn1'),
]
