from django.urls import path
from . import views

app_name = 'matterhorn'

urlpatterns = [
    path('add-new-product/', views.add_new_product, name='add_new_product'),
] 