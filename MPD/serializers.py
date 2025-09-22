from rest_framework import serializers
from .models import ProductSet, ProductSetItem, Products
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample


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
)
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
)
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
)
class ProductSetSerializer(serializers.ModelSerializer):
    items = ProductSetItemSerializer(many=True, read_only=True)

    class Meta:
        model = ProductSet
        fields = ['id', 'mapped_product', 'name',
                  'description', 'items', 'created_at', 'updated_at']
