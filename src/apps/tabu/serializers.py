from rest_framework import serializers
from .models import Brand, Category, ApiSyncLog


class BrandSerializer(serializers.ModelSerializer):
    """Serializer dla marki"""
    
    class Meta:
        model = Brand
        fields = [
            'id', 'brand_id', 'name', 'logo_url', 'description',
            'created_at', 'updated_at', 'last_api_sync'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_api_sync']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer dla kategorii"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'category_id', 'name', 'path', 'parent', 'parent_name',
            'description', 'created_at', 'updated_at', 'last_api_sync'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_api_sync']


class ApiSyncLogSerializer(serializers.ModelSerializer):
    """Serializer dla logów synchronizacji API"""
    
    class Meta:
        model = ApiSyncLog
        fields = [
            'id', 'sync_type', 'status', 'started_at', 'completed_at',
            'products_processed', 'products_success', 'products_failed',
            'error_message'
        ]
        read_only_fields = ['id', 'started_at', 'completed_at']
