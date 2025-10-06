from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebAgentTaskViewSet, WebAgentLogViewSet, WebAgentConfigViewSet

app_name = 'web_agent'

# Router dla ViewSets
router = DefaultRouter()
router.register(r'tasks', WebAgentTaskViewSet, basename='webagenttask')
router.register(r'logs', WebAgentLogViewSet, basename='webagentlog')
router.register(r'configs', WebAgentConfigViewSet, basename='webagentconfig')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
]
