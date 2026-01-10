"""
URL configuration for nc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.views.generic import TemplateView
from nc.views import index, health_check

# Import drf_spectacular tylko jeśli jest dostępny
try:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
    DRF_SPECTACULAR_AVAILABLE = True
except ImportError:
    DRF_SPECTACULAR_AVAILABLE = False

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('health/', health_check, name='health_check'),  # Health check dla Docker
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain'
    ), name='robots'),
    path('', index, name='index'),
]

# Dodaj URL-e drf_spectacular tylko jeśli jest dostępny
if DRF_SPECTACULAR_AVAILABLE:
    urlpatterns += [
        # API Documentation
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'),
             name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    # path('matterhorn/', include('matterhorn.urls')),  # stara aplikacja usunięta
    path('mpd/', include('MPD.urls')),
    path('matterhorn1/', include('matterhorn1.urls')),
    prefix_default_language=False
)

# API URLs (bez i18n)
urlpatterns += [
    path('api/web-agent/', include('web_agent.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]

# Serwuj pliki statyczne w produkcji jeśli nie ma nginx (fallback)
# To jest potrzebne gdy aplikacja działa bezpośrednio na porcie 8001
# Używamy zawsze (nie tylko gdy DEBUG=False), bo na VPS może nie być nginx
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
