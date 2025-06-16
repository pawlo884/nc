from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductSetViewSet, products, test_connection, test_table_structure, export_xml

router = DefaultRouter()
router.register(r'product-sets', ProductSetViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('products/', products, name='products'),
    path('test-connection/', test_connection, name='test_connection'),
    path('test-structure/', test_table_structure, name='test_structure'),
    path('export-xml/<str:source_name>/', export_xml, name='export_xml'),
]
