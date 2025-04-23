from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.products, name='products'),
    path('test-connection/', views.test_connection, name='test_connection'),
    path('test-structure/', views.test_table_structure, name='test_structure'),
]
