from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductSetViewSet, products, test_connection, test_table_structure, export_xml, export_full_xml, get_xml_file, xml_links, get_gateway_xml, generate_full_xml, generate_full_change_xml, generate_gateway_xml, empty_xml, generate_light_xml, generate_producers_xml, generate_stocks_xml, generate_units_xml

router = DefaultRouter()
router.register(r'product-sets', ProductSetViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('products/', products, name='products'),
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
]
