from django.urls import path
from django.http import HttpResponse


def index(request):
    """Strona główna aplikacji Web Agent"""
    return HttpResponse(
        '<html><head><title>Web Agent</title></head><body>'
        '<h1>Web Agent Application</h1>'
        '<p>Aplikacja w trakcie budowy...</p>'
        '</body></html>'
    )


app_name = 'web_agent'

urlpatterns = [
    path('', index, name='index'),
]

