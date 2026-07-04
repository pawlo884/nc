"""Endpointy autoryzacji dla frontendu React."""

from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

try:
    from drf_spectacular.utils import extend_schema

    @extend_schema(
        summary="Logowanie (token)",
        description="Zwraca token autoryzacyjny DRF dla frontendu SPA.",
        tags=["Auth"],
    )
    class CustomObtainAuthToken(ObtainAuthToken):
        """Zwraca token + podstawowe dane użytkownika."""

        def post(self, request, *args, **kwargs):
            serializer = self.serializer_class(
                data=request.data,
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            token, _created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.pk,
                'username': user.username,
                'is_staff': user.is_staff,
            })

except ImportError:

    class CustomObtainAuthToken(ObtainAuthToken):
        """Zwraca token + podstawowe dane użytkownika."""

        def post(self, request, *args, **kwargs):
            serializer = self.serializer_class(
                data=request.data,
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            token, _created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.pk,
                'username': user.username,
                'is_staff': user.is_staff,
            })
