from rest_framework import serializers
from .models import ProductSet, ProductSetItem, Products

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Products
        fields = ['id', 'name', 'description']

class ProductSetItemSerializer(serializers.ModelSerializer):
    mapped_product = ProductSerializer()

    class Meta:
        model = ProductSetItem
        fields = ['id', 'mapped_product', 'quantity', 'created_at']

class ProductSetSerializer(serializers.ModelSerializer):
    items = ProductSetItemSerializer(many=True, read_only=True)

    class Meta:
        model = ProductSet
        fields = ['id', 'mapped_product', 'name', 'description', 'items', 'created_at', 'updated_at'] 