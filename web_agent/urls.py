"""
URL routing dla aplikacji web_agent.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AutomationRunViewSet, ProductProcessingLogViewSet

router = DefaultRouter()
router.register(r'automation-runs', AutomationRunViewSet, basename='automation-run')
router.register(r'product-logs', ProductProcessingLogViewSet, basename='product-log')

urlpatterns = [
    path('', include(router.urls)),
]

