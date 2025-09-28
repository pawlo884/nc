from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
import json

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

from .models import (
    Product, Brand, Category, ProductDetails,
    ProductImage, ProductVariant, ApiSyncLog
)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Brand Example',
            summary='Przykład marki',
            description='Przykład danych marki',
            value={
                'brand_id': 'BRAND001',
                'name': 'Lupo Line'
            }
        )
    ]
) if DRF_SPECTACULAR_AVAILABLE else extend_schema_serializer()
class BrandSerializer(serializers.ModelSerializer):
    """Serializer dla marek"""

    class Meta:
        model = Brand
        fields = ['brand_id', 'name']

    def validate_brand_id(self, value):
        """Walidacja brand_id"""
        if not value:
            raise serializers.ValidationError("Brand ID jest wymagane")
        return value

    def validate_name(self, value):
        """Walidacja nazwy marki"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Nazwa marki jest wymagana")
        return value.strip()


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Category Example',
            summary='Przykład kategorii',
            description='Przykład danych kategorii',
            value={
                'category_id': 'CAT001',
                'name': 'Stroje kąpielowe',
                'path': 'odziez/stroje-kapielowe'
            }
        )
    ]
) if DRF_SPECTACULAR_AVAILABLE else extend_schema_serializer()
class CategorySerializer(serializers.ModelSerializer):
    """Serializer dla kategorii"""

    class Meta:
        model = Category
        fields = ['category_id', 'name', 'path']

    def validate_category_id(self, value):
        """Walidacja category_id"""
        if not value:
            raise serializers.ValidationError("Category ID jest wymagane")
        return value

    def validate_name(self, value):
        """Walidacja nazwy kategorii"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Nazwa kategorii jest wymagana")
        return value.strip()


class ProductDetailsSerializer(serializers.ModelSerializer):
    """Serializer dla szczegółów produktu"""

    class Meta:
        model = ProductDetails
        fields = ['weight', 'size_table', 'size_table_txt', 'size_table_html']

    def validate_weight(self, value):
        """Walidacja wagi"""
        if value and not value.replace('.', '').replace(',', '').isdigit():
            raise serializers.ValidationError("Waga musi być liczbą")
        return value


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Product Image Example',
            summary='Przykład obrazu produktu',
            description='Przykład danych obrazu produktu',
            value={
                'image_url': 'https://example.com/images/product1.jpg',
                'order': 1
            }
        )
    ]
) if DRF_SPECTACULAR_AVAILABLE else extend_schema_serializer()
class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer dla obrazów produktu"""

    class Meta:
        model = ProductImage
        fields = ['image_url', 'order']

    def validate_image_url(self, value):
        """Walidacja URL obrazu"""
        if not value:
            raise serializers.ValidationError("URL obrazu jest wymagany")
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError(
                "URL musi zaczynać się od http:// lub https://")
        return value

    def validate_order(self, value):
        """Walidacja kolejności"""
        if value < 0:
            raise serializers.ValidationError("Kolejność nie może być ujemna")
        return value


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Product Variant Example',
            summary='Przykład wariantu produktu',
            description='Przykład danych wariantu produktu',
            value={
                'variant_uid': 'VAR001',
                'name': 'Rozmiar M - Czarny',
                'stock': 10,
                'max_processing_time': 5,
                'ean': '1234567890123'
            }
        )
    ]
) if DRF_SPECTACULAR_AVAILABLE else extend_schema_serializer()
class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer dla wariantów produktu"""

    class Meta:
        model = ProductVariant
        fields = ['variant_uid', 'name', 'stock', 'max_processing_time', 'ean']

    def validate_variant_uid(self, value):
        """Walidacja variant_uid"""
        if not value:
            raise serializers.ValidationError("Variant UID jest wymagane")
        return value

    def validate_name(self, value):
        """Walidacja nazwy wariantu (rozmiar)"""
        if not value:
            raise serializers.ValidationError("Nazwa wariantu jest wymagana")
        return value.strip()

    def validate_stock(self, value):
        """Walidacja stanu magazynowego"""
        if value < 0:
            raise serializers.ValidationError(
                "Stan magazynowy nie może być ujemny")
        return value

    def validate_max_processing_time(self, value):
        """Walidacja maksymalnego czasu przetwarzania"""
        if value < 0:
            raise serializers.ValidationError(
                "Czas przetwarzania nie może być ujemny")
        return value


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Product Example',
            summary='Przykład produktu',
            description='Przykład danych produktu z wariantami i obrazami',
            value={
                'product_id': 'PROD001',
                'active': True,
                'name': 'strój kąpielowy model 123 - Lupo Line',
                'description': 'Elegancki strój kąpielowy z wysokiej jakości materiału',
                'creation_date': '2024-01-15T10:30:00Z',
                'color': 'Czarny',
                'url': 'https://example.com/products/prod001',
                'new_collection': False,
                'products_in_set': 1,
                'other_colors': ['Biały', 'Niebieski'],
                'prices': {'PLN': 299.99, 'EUR': 69.99},
                'brand_id': 'BRAND001',
                'category_id': 'CAT001',
                'details': {
                    'weight': '0.5',
                    'size_table': 'M,L,XL',
                    'size_table_txt': 'M: 80-85cm, L: 85-90cm, XL: 90-95cm'
                },
                'images': [
                    {
                        'image_url': 'https://example.com/images/prod001_1.jpg',
                        'order': 1
                    }
                ],
                'variants': [
                    {
                        'variant_uid': 'VAR001',
                        'name': 'Rozmiar M - Czarny',
                        'stock': 10,
                        'max_processing_time': 5,
                        'ean': '1234567890123'
                    }
                ]
            }
        )
    ]
) if DRF_SPECTACULAR_AVAILABLE else extend_schema_serializer()
class ProductSerializer(serializers.ModelSerializer):
    """Główny serializer dla produktów"""

    # Nested serializers
    details = ProductDetailsSerializer(required=False, allow_null=True)
    images = ProductImageSerializer(many=True, required=False)
    variants = ProductVariantSerializer(many=True, required=False)

    # Pola zewnętrzne (do parsowania z API)
    brand_id = serializers.CharField(write_only=True, required=False)
    category_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Product
        fields = [
            'product_id', 'active', 'name', 'description', 'creation_date',
            'color', 'url', 'new_collection', 'products_in_set', 'other_colors',
            'prices', 'brand_id', 'category_id', 'details', 'images', 'variants'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_api_sync']

    def validate_product_id(self, value):
        """Walidacja product_id"""
        if not value:
            raise serializers.ValidationError("Product ID jest wymagane")
        return value

    def validate_name(self, value):
        """Walidacja nazwy produktu"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Nazwa produktu jest wymagana")
        return value.strip()

    def validate_creation_date(self, value):
        """Konwersja i walidacja daty utworzenia"""
        if isinstance(value, str):
            try:
                # Obsługa różnych formatów daty z API
                if 'T' in value:
                    # Format ISO: 2025-09-09T00:00:00
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    # Format: 2025-09-09 00:00:00
                    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise serializers.ValidationError("Nieprawidłowy format daty")
        return value

    def validate_active(self, value):
        """Konwersja active z string na boolean"""
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'y')
        return bool(value)

    def validate_new_collection(self, value):
        """Konwersja new_collection z string na boolean"""
        if isinstance(value, str):
            return value.upper() in ('Y', 'YES', 'TRUE', '1')
        return bool(value)

    def validate_products_in_set(self, value):
        """Walidacja products_in_set"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError(
                    "Nieprawidłowy format JSON dla products_in_set")
        return value or []

    def validate_other_colors(self, value):
        """Walidacja other_colors"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError(
                    "Nieprawidłowy format JSON dla other_colors")
        return value or []

    def validate_prices(self, value):
        """Walidacja prices"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError(
                    "Nieprawidłowy format JSON dla prices")
        return value or {}

    def validate_url(self, value):
        """Walidacja URL"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError(
                "URL musi zaczynać się od http:// lub https://")
        return value

    def create(self, validated_data):
        """Tworzenie produktu z relacjami"""
        # Wyciągnij dane dla relacji
        details_data = validated_data.pop('details', None)
        images_data = validated_data.pop('images', [])
        variants_data = validated_data.pop('variants', [])
        brand_id = validated_data.pop('brand_id', None)
        category_id = validated_data.pop('category_id', None)

        # Znajdź lub utwórz brand
        if brand_id:
            brand, _ = Brand.objects.get_or_create(
                brand_id=brand_id,
                defaults={'name': f'Brand {brand_id}'}
            )
            validated_data['brand'] = brand

        # Znajdź lub utwórz category
        if category_id:
            category, _ = Category.objects.get_or_create(
                category_id=category_id,
                defaults={'name': f'Category {category_id}',
                          'path': f'/Category {category_id}'}
            )
            validated_data['category'] = category

        # Ustaw last_api_sync
        validated_data['last_api_sync'] = timezone.now()

        # Utwórz produkt
        product = Product.objects.create(**validated_data)

        # Utwórz szczegóły
        if details_data:
            ProductDetails.objects.create(product=product, **details_data)

        # Utwórz obrazy
        for image_data in images_data:
            ProductImage.objects.create(product=product, **image_data)

        # Utwórz warianty
        for variant_data in variants_data:
            ProductVariant.objects.create(product=product, **variant_data)

        return product

    def update(self, instance, validated_data):
        """Aktualizacja produktu z relacjami"""
        # Wyciągnij dane dla relacji
        details_data = validated_data.pop('details', None)
        images_data = validated_data.pop('images', None)
        variants_data = validated_data.pop('variants', None)
        brand_id = validated_data.pop('brand_id', None)
        category_id = validated_data.pop('category_id', None)

        # Znajdź lub utwórz brand
        if brand_id:
            brand, _ = Brand.objects.get_or_create(
                brand_id=brand_id,
                defaults={'name': f'Brand {brand_id}'}
            )
            validated_data['brand'] = brand

        # Znajdź lub utwórz category
        if category_id:
            category, _ = Category.objects.get_or_create(
                category_id=category_id,
                defaults={'name': f'Category {category_id}',
                          'path': f'/Category {category_id}'}
            )
            validated_data['category'] = category

        # Ustaw last_api_sync
        validated_data['last_api_sync'] = timezone.now()

        # Aktualizuj produkt
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Aktualizuj szczegóły
        if details_data is not None:
            if hasattr(instance, 'details'):
                for attr, value in details_data.items():
                    setattr(instance.details, attr, value)
                instance.details.save()
            else:
                ProductDetails.objects.create(product=instance, **details_data)

        # Aktualizuj obrazy
        if images_data is not None:
            # Usuń stare obrazy
            instance.images.all().delete()
            # Utwórz nowe
            for image_data in images_data:
                ProductImage.objects.create(product=instance, **image_data)

        # Aktualizuj warianty
        if variants_data is not None:
            # Usuń stare warianty
            instance.variants.all().delete()
            # Utwórz nowe
            for variant_data in variants_data:
                ProductVariant.objects.create(product=instance, **variant_data)

        return instance


class ApiSyncLogSerializer(serializers.ModelSerializer):
    """Serializer dla logów synchronizacji"""

    class Meta:
        model = ApiSyncLog
        fields = '__all__'
        read_only_fields = ['started_at', 'completed_at', 'duration_seconds']


class BulkProductSerializer(serializers.Serializer):
    """Serializer dla bulk operations na produktach"""

    products = ProductSerializer(many=True)

    def validate_products(self, value):
        """Walidacja listy produktów"""
        if not value:
            raise serializers.ValidationError(
                "Lista produktów nie może być pusta")

        # Sprawdź unikalność product_id
        product_ids = [product.get('product_id')
                       for product in value if product.get('product_id')]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("Duplikaty w product_id")

        return value

    def create(self, validated_data):
        """Bulk create produktów"""
        products_data = validated_data['products']
        created_products = []

        for product_data in products_data:
            serializer = ProductSerializer(data=product_data)
            if serializer.is_valid():
                product = serializer.save()
                created_products.append(product)
            else:
                raise serializers.ValidationError(
                    f"Błąd walidacji produktu: {serializer.errors}")

        return {'products': created_products}


class BulkBrandSerializer(serializers.Serializer):
    """Serializer dla bulk operations na markach"""

    brands = BrandSerializer(many=True)

    def validate_brands(self, value):
        """Walidacja listy marek"""
        if not value:
            raise serializers.ValidationError("Lista marek nie może być pusta")

        # Sprawdź unikalność brand_id
        brand_ids = [brand.get('brand_id')
                     for brand in value if brand.get('brand_id')]
        if len(brand_ids) != len(set(brand_ids)):
            raise serializers.ValidationError("Duplikaty w brand_id")

        return value


class BulkCategorySerializer(serializers.Serializer):
    """Serializer dla bulk operations na kategoriach"""

    categories = CategorySerializer(many=True)

    def validate_categories(self, value):
        """Walidacja listy kategorii"""
        if not value:
            raise serializers.ValidationError(
                "Lista kategorii nie może być pusta")

        # Sprawdź unikalność category_id
        category_ids = [category.get('category_id')
                        for category in value if category.get('category_id')]
        if len(category_ids) != len(set(category_ids)):
            raise serializers.ValidationError("Duplikaty w category_id")

        return value


class BulkVariantSerializer(serializers.Serializer):
    """Serializer dla bulk operations na wariantach"""

    variants = ProductVariantSerializer(many=True)

    def validate_variants(self, value):
        """Walidacja listy wariantów"""
        if not value:
            raise serializers.ValidationError(
                "Lista wariantów nie może być pusta")

        # Sprawdź unikalność variant_uid
        variant_uids = [variant.get('variant_uid')
                        for variant in value if variant.get('variant_uid')]
        if len(variant_uids) != len(set(variant_uids)):
            raise serializers.ValidationError("Duplikaty w variant_uid")

        return value


class BulkImageSerializer(serializers.Serializer):
    """Serializer dla bulk operations na obrazach"""

    images = ProductImageSerializer(many=True)

    def validate_images(self, value):
        """Walidacja listy obrazów"""
        if not value:
            raise serializers.ValidationError(
                "Lista obrazów nie może być pusta")

        return value
