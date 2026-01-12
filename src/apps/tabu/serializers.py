from rest_framework import serializers
from .models import Brand, Category, Product, ProductImage, ProductVariant, ApiSyncLog


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


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer dla obrazów produktu"""
    
    class Meta:
        model = ProductImage
        fields = [
            'id', 'image_url', 'thumbnail_url', 'order', 'alt_text', 'is_main', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer dla wariantów produktu"""
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'variant_id', 'external_id', 'name', 'sku', 'ean',
            'size', 'color', 'color_code', 'stock', 'stock_reserved',
            'available', 'price', 'price_net', 'price_gross',
            'max_processing_time', 'attributes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    """Główny serializer dla produktów"""
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    stock_total = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'product_id', 'external_id', 'name', 'description', 'short_description',
            'active', 'brand', 'brand_name', 'category', 'category_name',
            'price', 'price_net', 'price_gross', 'currency', 'vat_rate',
            'url', 'slug', 'new_collection', 'featured', 'on_sale',
            'attributes', 'prices', 'other_colors', 'products_in_set',
            'images', 'variants', 'stock_total',
            'creation_date', 'created_at', 'updated_at', 'last_api_sync'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_api_sync', 'stock_total'
        ]


class ProductListSerializer(serializers.ModelSerializer):
    """Uproszczony serializer dla listy produktów"""
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    main_image = serializers.SerializerMethodField()
    stock_total = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'product_id', 'name', 'brand_name', 'category_name',
            'price', 'currency', 'active', 'main_image', 'stock_total',
            'url', 'slug', 'new_collection', 'featured', 'on_sale'
        ]
    
    def get_main_image(self, obj):
        """Zwraca główny obraz produktu"""
        main_image = obj.images.filter(is_main=True).first()
        if main_image:
            return main_image.image_url
        # Jeśli nie ma głównego, zwróć pierwszy obraz
        first_image = obj.images.first()
        return first_image.image_url if first_image else None


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
