"""
Wspólne zabezpieczenie dla "legacy" widoków (sprzed wprowadzenia DRF APIView
z permission_classes), które mimo to muszą pozostać dostępne tylko dla adminów.

Akceptuje albo zalogowaną sesję (Django admin), albo nagłówek
``Authorization: Token <key>`` (ten sam mechanizm co reszta API), żeby nie
zrywać ewentualnych integracji serwer-serwer używających tokenu.
"""
from functools import wraps

from django.http import JsonResponse
from rest_framework.authtoken.models import Token


def _resolve_staff_user(request):
    """Zwraca zalogowanego użytkownika (sesja lub Token), albo None."""
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        return user

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Token '):
        key = auth_header.split(' ', 1)[1].strip()
        try:
            return Token.objects.select_related('user').get(key=key).user
        except Token.DoesNotExist:
            return None

    return None


def _forbidden_response(request):
    user = _resolve_staff_user(request)
    if user is None:
        return JsonResponse({'detail': 'Wymagane uwierzytelnienie.'}, status=401)
    if not user.is_staff:
        return JsonResponse({'detail': 'Brak uprawnień.'}, status=403)
    return None


def admin_required(view_func):
    """Dekorator dla widoków funkcyjnych: wymaga zalogowanego admina."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        denied = _forbidden_response(request)
        if denied is not None:
            return denied
        return view_func(request, *args, **kwargs)
    return wrapped


class AdminRequiredMixin:
    """Mixin dla widoków klasowych (django.views.View): wymaga zalogowanego admina."""

    def dispatch(self, request, *args, **kwargs):
        denied = _forbidden_response(request)
        if denied is not None:
            return denied
        return super().dispatch(request, *args, **kwargs)
