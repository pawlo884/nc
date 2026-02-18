from django.urls import path
from . import views

app_name = 'dashboard_pydash'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('audit/', views.audit_log_view, name='audit_log'),
    path('trigger-simulation/', views.trigger_simulation_view, name='trigger_simulation'),
]
