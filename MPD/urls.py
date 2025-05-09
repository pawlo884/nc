from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductSetViewSet

router = DefaultRouter()
router.register(r'product-sets', ProductSetViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('products/', views.products, name='products'),
    path('test-connection/', views.test_connection, name='test_connection'),
    path('test-structure/', views.test_table_structure, name='test_structure'),
]
