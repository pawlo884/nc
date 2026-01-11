from rest_framework import serializers
from .models import ProductSet, ProductSetItem, Products

# Import drf_spectacular tylko jeśli jest dostępny
try:
    from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
    DRF_SPECTACULAR_AVAILABLE = True
except ImportError:
    DRF_SPECTACULAR_AVAILABLE = False
    # Dummy decorator jeśli drf_spectacular nie jest dostępny

    def extend_schema_serializer(*args, **kwargs):
        def decorator(cls):
            return cls
        return decorator
    OpenApiExample = None


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Product Example',
            summary='Przykład produktu',
            description='Przykład danych produktu',
            value={
                'id': 1,
                'name': 'Strój kąpielowy model 123',
                'description': 'Elegancki strój kąpielowy z wysokiej jakości materiału'
            }
        )
    ]
) if DRF_SPECTACULAR_AVAILABLE else extend_schema_serializer()
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Products
        fields = ['id', 'name', 'description']


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Product Set Item Example',
            summary='Przykład elementu zestawu',
            description='Przykład elementu w zestawie produktów',
            value={
                'id': 1,
                'mapped_product': {
                    'id': 1,
                    'name': 'Strój kąpielowy model 123',
                    'description': 'Elegancki strój kąpielowy'
                },
                'quantity': 2,
                'created_at': '2024-01-15T10:30:00Z'
            }
        )
    ]
) if DRF_SPECTACULAR_AVAILABLE else extend_schema_serializer()
class ProductSetItemSerializer(serializers.ModelSerializer):
    mapped_product = ProductSerializer()

    class Meta:
        model = ProductSetItem
        fields = ['id', 'mapped_product', 'quantity', 'created_at']


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Product Set Example',
            summary='Przykład zestawu produktów',
            description='Przykład zestawu produktów z elementami',
            value={
                'id': 1,
                'mapped_product': 1,
                'name': 'Zestaw strojów kąpielowych',
                'description': 'Kompletny zestaw strojów kąpielowych',
                'items': [
                    {
                        'id': 1,
                        'mapped_product': {
                            'id': 1,
                            'name': 'Strój kąpielowy model 123',
                            'description': 'Elegancki strój kąpielowy'
                        },
                        'quantity': 2,
                        'created_at': '2024-01-15T10:30:00Z'
                    }
                ],
                'created_at': '2024-01-15T10:30:00Z',
                'updated_at': '2024-01-15T10:30:00Z'
            }
        )
    ]
) if DRF_SPECTACULAR_AVAILABLE else extend_schema_serializer()
class ProductSetSerializer(serializers.ModelSerializer):
    items = ProductSetItemSerializer(many=True, read_only=True)

    class Meta:
        model = ProductSet
        fields = ['id', 'mapped_product', 'name',
                  'description', 'items', 'created_at', 'updated_at']
