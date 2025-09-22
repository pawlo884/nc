from django.urls import path, include
from . import views

app_name = 'matterhorn1'

urlpatterns = [
    # API endpoints dla bulk operations
    path('api/', include([
        # Bulk operations dla produktów
        path('products/bulk/', views.ProductBulkView.as_view(), name='product_bulk'),
        path('products/bulk/create/', views.ProductBulkCreateView.as_view(),
             name='product_bulk_create'),
        path('products/bulk/update/', views.ProductBulkUpdateView.as_view(),
             name='product_bulk_update'),

        # Bulk operations dla wariantów
        path('variants/bulk/', views.VariantBulkView.as_view(), name='variant_bulk'),
        path('variants/bulk/create/', views.VariantBulkCreateView.as_view(),
             name='variant_bulk_create'),
        path('variants/bulk/update/', views.VariantBulkUpdateView.as_view(),
             name='variant_bulk_update'),

        # Bulk operations dla marek
        path('brands/bulk/', views.BrandBulkView.as_view(), name='brand_bulk'),
        path('brands/bulk/create/', views.BrandBulkCreateView.as_view(),
             name='brand_bulk_create'),

        # Bulk operations dla kategorii
        path('categories/bulk/', views.CategoryBulkView.as_view(),
             name='category_bulk'),
        path('categories/bulk/create/',
             views.CategoryBulkCreateView.as_view(), name='category_bulk_create'),

        # Bulk operations dla obrazów
        path('images/bulk/', views.ImageBulkView.as_view(), name='image_bulk'),
        path('images/bulk/create/', views.ImageBulkCreateView.as_view(),
             name='image_bulk_create'),

        # Synchronizacja z API
        path('sync/', views.APISyncView.as_view(), name='api_sync'),
        path('sync/products/', views.ProductSyncView.as_view(), name='product_sync'),
        path('sync/variants/', views.VariantSyncView.as_view(), name='variant_sync'),

        # Status i logi
        path('status/', views.APIStatusView.as_view(), name='api_status'),
        path('logs/', views.APILogsView.as_view(), name='api_logs'),

        # Pojedyncze produkty
        path('products/<int:product_id>/',
             views.get_product_details, name='get_product_details'),
    ])),
]
