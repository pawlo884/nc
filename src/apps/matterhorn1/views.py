from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.utils import timezone
import json
import logging
from datetime import datetime

# Import drf_spectacular tylko jeśli jest dostępny
try:
    from drf_spectacular.utils import extend_schema, OpenApiExample
    DRF_SPECTACULAR_AVAILABLE = True
except ImportError:
    DRF_SPECTACULAR_AVAILABLE = False
    # Dummy decorator jeśli drf_spectacular nie jest dostępny

    def extend_schema(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    OpenApiExample = None

from .models import (
    Product, Brand, Category,
    ProductImage, ProductVariant, ApiSyncLog
)
from .defs_db import resolve_image_url
from .serializers import (
    ProductSerializer, BrandSerializer, CategorySerializer,
    ProductVariantSerializer, ProductImageSerializer,
    BulkProductSerializer, BulkBrandSerializer, BulkCategorySerializer,
    BulkVariantSerializer, BulkImageSerializer
)

logger = logging.getLogger(__name__)


class BaseBulkView(View):
    """Bazowa klasa dla bulk operations"""

    def get_model(self):
        """Zwraca model dla danej operacji - do nadpisania w klasach potomnych"""
        raise NotImplementedError

    def get_serializer_fields(self):
        """Zwraca pola do serializacji - do nadpisania w klasach potomnych"""
        raise NotImplementedError

    def validate_data(self, data):
        """Waliduje dane przed zapisem - do nadpisania w klasach potomnych"""
        return True, []

    def prepare_bulk_data(self, data):
        """Przygotowuje dane do bulk operations - do nadpisania w klasach potomnych"""
        return data


class ProductBulkView(BaseBulkView):
    """Bulk operations dla produktów"""

    def get_model(self):
        return Product

    def get_serializer_fields(self):
        return [
            'product_id', 'active', 'name', 'description', 'creation_date',
            'color', 'url', 'new_collection', 'products_in_set', 'other_colors',
            'prices', 'category_id', 'brand_id'
        ]

    def validate_data(self, data):
        errors = []

        # Sprawdź czy product_id jest unikalne
        product_ids = [item.get('product_id')
                       for item in data if item.get('product_id')]
        if len(product_ids) != len(set(product_ids)):
            errors.append("Duplikaty w product_id")

        # Sprawdź czy wymagane pola są obecne
        for i, item in enumerate(data):
            if not item.get('product_id'):
                errors.append(f"Element {i}: brak product_id")
            if not item.get('name'):
                errors.append(f"Element {i}: brak name")

        return len(errors) == 0, errors

    def prepare_bulk_data(self, data):
        prepared_data = []
        for item in data:
            # Konwertuj daty
            if item.get('creation_date'):
                try:
                    item['creation_date'] = datetime.fromisoformat(
                        item['creation_date'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    item['creation_date'] = None

            # Konwertuj boolean
            item['active'] = str(item.get('active', 'true')).lower() == 'true'
            item['new_collection'] = str(
                item.get('new_collection', 'false')).lower() == 'true'

            prepared_data.append(item)

        return prepared_data


@extend_schema(
    operation_id='products_bulk_create',
    summary='Masowe tworzenie produktów',
    description='Tworzy wiele produktów jednocześnie. Wymaga tablicy obiektów produktów.',
    tags=['Products'],
    request=BulkProductSerializer,
    responses={
        200: {'description': 'Produkty zostały pomyślnie utworzone'},
        400: {'description': 'Błąd walidacji danych'},
        500: {'description': 'Błąd serwera'}
    },
    examples=[
        OpenApiExample(
            'Bulk Create Products',
            summary='Przykład masowego tworzenia produktów',
            description='Przykład żądania do masowego tworzenia produktów',
            value=[
                {
                    'product_id': 'PROD001',
                    'active': True,
                    'name': 'strój kąpielowy model 123 - Lupo Line',
                    'description': 'Elegancki strój kąpielowy',
                    'creation_date': '2024-01-15T10:30:00Z',
                    'color': 'Czarny',
                    'url': 'https://example.com/products/prod001',
                    'new_collection': False,
                    'products_in_set': 1,
                    'other_colors': ['Biały', 'Niebieski'],
                    'prices': {'PLN': 299.99, 'EUR': 69.99},
                    'brand_id': 'BRAND001',
                    'category_id': 'CAT001'
                }
            ]
        )
    ]
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class ProductBulkCreateView(ProductBulkView):
    """Bulk create dla produktów"""

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)

            if not isinstance(data, list):
                return JsonResponse({
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                }, status=400)

            # Użyj BulkProductSerializer
            bulk_serializer = BulkProductSerializer(data={'products': data})

            if not bulk_serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                }, status=400)

            # Bulk create z serializers
            with transaction.atomic():
                created_objects = []
                errors = []

                for product_data in data:
                    serializer = ProductSerializer(data=product_data)
                    if serializer.is_valid():
                        product = serializer.save()
                        created_objects.append(product)
                    else:
                        errors.append({
                            'product_id': product_data.get('product_id', 'unknown'),
                            'errors': serializer.errors
                        })

                # Log operacji
                ApiSyncLog.objects.create(
                    sync_type='products_bulk_create',
                    status='success' if not errors else 'partial',
                    records_processed=len(data),
                    records_created=len(created_objects),
                    records_errors=len(errors),
                    error_details=json.dumps(errors) if errors else '',
                    completed_at=timezone.now()
                )

            response_data = {
                'success': True,
                'message': f'Utworzono {len(created_objects)} produktów',
                'created_count': len(created_objects),
                'processed_count': len(data)
            }

            if errors:
                response_data['errors'] = errors
                response_data['message'] += f', {len(errors)} błędów'

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Nieprawidłowy format JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Błąd w ProductBulkCreateView: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Błąd serwera: {str(e)}'
            }, status=500)


@extend_schema(
    operation_id='products_bulk_update',
    summary='Masowe aktualizowanie produktów',
    description='Aktualizuje wiele produktów jednocześnie. Wymaga tablicy obiektów produktów z product_id.',
    tags=['Products'],
    request=BulkProductSerializer,
    responses={
        200: {'description': 'Produkty zostały pomyślnie zaktualizowane'},
        400: {'description': 'Błąd walidacji danych'},
        500: {'description': 'Błąd serwera'}
    }
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class ProductBulkUpdateView(ProductBulkView):
    """Bulk update dla produktów"""

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)

            if not isinstance(data, list):
                return JsonResponse({
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                }, status=400)

            # Użyj BulkProductSerializer
            bulk_serializer = BulkProductSerializer(data={'products': data})

            if not bulk_serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                }, status=400)

            # Bulk update z serializers
            with transaction.atomic():
                updated_objects = []
                created_objects = []
                errors = []

                for product_data in data:
                    product_id = product_data.get('product_id')
                    if not product_id:
                        errors.append({
                            'product_id': 'unknown',
                            'errors': {'product_id': ['Product ID jest wymagane']}
                        })
                        continue

                    try:
                        # Znajdź istniejący produkt
                        product = Product.objects.get(product_id=product_id)
                        serializer = ProductSerializer(
                            product, data=product_data, partial=True)

                        if serializer.is_valid():
                            updated_product = serializer.save()
                            updated_objects.append(updated_product)
                        else:
                            errors.append({
                                'product_id': product_id,
                                'errors': serializer.errors
                            })
                    except Product.DoesNotExist:
                        # Jeśli produkt nie istnieje, utwórz go
                        serializer = ProductSerializer(data=product_data)
                        if serializer.is_valid():
                            new_product = serializer.save()
                            created_objects.append(new_product)
                        else:
                            errors.append({
                                'product_id': product_id,
                                'errors': serializer.errors
                            })

                # Log operacji
                ApiSyncLog.objects.create(
                    sync_type='products_bulk_update',
                    status='success' if not errors else 'partial',
                    records_processed=len(data),
                    records_updated=len(updated_objects),
                    records_created=len(created_objects),
                    records_errors=len(errors),
                    error_details=json.dumps(errors) if errors else '',
                    completed_at=timezone.now()
                )

            response_data = {
                'success': True,
                'message': f'Zaktualizowano {len(updated_objects)} produktów',
                'updated_count': len(updated_objects),
                'created_count': len(created_objects),
                'processed_count': len(data)
            }

            if errors:
                response_data['errors'] = errors
                response_data['message'] += f', {len(errors)} błędów'

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Nieprawidłowy format JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Błąd w ProductBulkUpdateView: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Błąd serwera: {str(e)}'
            }, status=500)


# Placeholder views dla pozostałych endpointów
class VariantBulkView(BaseBulkView):
    def get_model(self):
        return ProductVariant


@extend_schema(
    operation_id='variants_bulk_create',
    summary='Masowe tworzenie wariantów',
    description='Tworzy wiele wariantów produktów jednocześnie.',
    tags=['Variants'],
    request=BulkVariantSerializer,
    responses={
        200: {'description': 'Warianty zostały pomyślnie utworzone'},
        400: {'description': 'Błąd walidacji danych'},
        500: {'description': 'Błąd serwera'}
    }
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class VariantBulkCreateView(View):
    """Bulk create dla wariantów"""

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)

            if not isinstance(data, list):
                return JsonResponse({
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                }, status=400)

            # Użyj BulkVariantSerializer
            bulk_serializer = BulkVariantSerializer(data={'variants': data})

            if not bulk_serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                }, status=400)

            # Bulk create z serializers
            with transaction.atomic():
                created_objects = []
                errors = []

                for variant_data in data:
                    # Sprawdź czy product_id istnieje
                    product_id = variant_data.get('product_id')
                    if not product_id:
                        errors.append({
                            'variant_uid': variant_data.get('variant_uid', 'unknown'),
                            'errors': {'product_id': ['Product ID jest wymagane']}
                        })
                        continue

                    try:
                        product = Product.objects.get(product_id=product_id)
                        variant_data['product'] = product.id
                        serializer = ProductVariantSerializer(
                            data=variant_data)

                        if serializer.is_valid():
                            variant = serializer.save()
                            created_objects.append(variant)
                        else:
                            errors.append({
                                'variant_uid': variant_data.get('variant_uid', 'unknown'),
                                'errors': serializer.errors
                            })
                    except Product.DoesNotExist:
                        errors.append({
                            'variant_uid': variant_data.get('variant_uid', 'unknown'),
                            'errors': {'product_id': ['Produkt nie istnieje']}
                        })

                # Log operacji
                ApiSyncLog.objects.create(
                    sync_type='variants_bulk_create',
                    status='success' if not errors else 'partial',
                    records_processed=len(data),
                    records_created=len(created_objects),
                    records_errors=len(errors),
                    error_details=json.dumps(errors) if errors else '',
                    completed_at=timezone.now()
                )

            response_data = {
                'success': True,
                'message': f'Utworzono {len(created_objects)} wariantów',
                'created_count': len(created_objects),
                'processed_count': len(data)
            }

            if errors:
                response_data['errors'] = errors
                response_data['message'] += f', {len(errors)} błędów'

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Nieprawidłowy format JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Błąd w VariantBulkCreateView: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Błąd serwera: {str(e)}'
            }, status=500)


class VariantBulkUpdateView(View):
    """Bulk update dla wariantów"""

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)

            if not isinstance(data, list):
                return JsonResponse({
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                }, status=400)

            # Użyj BulkVariantSerializer
            bulk_serializer = BulkVariantSerializer(data={'variants': data})

            if not bulk_serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                }, status=400)

            # Bulk update z serializers
            with transaction.atomic():
                updated_objects = []
                created_objects = []
                errors = []

                for variant_data in data:
                    variant_uid = variant_data.get('variant_uid')
                    if not variant_uid:
                        errors.append({
                            'variant_uid': 'unknown',
                            'errors': {'variant_uid': ['Variant UID jest wymagane']}
                        })
                        continue

                    try:
                        # Znajdź istniejący wariant
                        variant = ProductVariant.objects.get(
                            variant_uid=variant_uid)
                        serializer = ProductVariantSerializer(
                            variant, data=variant_data, partial=True)

                        if serializer.is_valid():
                            updated_variant = serializer.save()
                            updated_objects.append(updated_variant)
                        else:
                            errors.append({
                                'variant_uid': variant_uid,
                                'errors': serializer.errors
                            })
                    except ProductVariant.DoesNotExist:
                        # Jeśli wariant nie istnieje, utwórz go
                        serializer = ProductVariantSerializer(
                            data=variant_data)
                        if serializer.is_valid():
                            new_variant = serializer.save()
                            created_objects.append(new_variant)
                        else:
                            errors.append({
                                'variant_uid': variant_uid,
                                'errors': serializer.errors
                            })

                # Log operacji
                ApiSyncLog.objects.create(
                    sync_type='variants_bulk_update',
                    status='success' if not errors else 'partial',
                    records_processed=len(data),
                    records_updated=len(updated_objects),
                    records_created=len(created_objects),
                    records_errors=len(errors),
                    error_details=json.dumps(errors) if errors else '',
                    completed_at=timezone.now()
                )

            response_data = {
                'success': True,
                'message': f'Zaktualizowano {len(updated_objects)} wariantów',
                'updated_count': len(updated_objects),
                'created_count': len(created_objects),
                'processed_count': len(data)
            }

            if errors:
                response_data['errors'] = errors
                response_data['message'] += f', {len(errors)} błędów'

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Nieprawidłowy format JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Błąd w VariantBulkUpdateView: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Błąd serwera: {str(e)}'
            }, status=500)


class BrandBulkView(BaseBulkView):
    def get_model(self):
        return Brand


@extend_schema(
    operation_id='brands_bulk_create',
    summary='Masowe tworzenie marek',
    description='Tworzy wiele marek jednocześnie.',
    tags=['Brands'],
    request=BulkBrandSerializer,
    responses={
        200: {'description': 'Marki zostały pomyślnie utworzone'},
        400: {'description': 'Błąd walidacji danych'},
        500: {'description': 'Błąd serwera'}
    }
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class BrandBulkCreateView(View):
    """Bulk create dla marek"""

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)

            if not isinstance(data, list):
                return JsonResponse({
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                }, status=400)

            # Użyj BulkBrandSerializer
            bulk_serializer = BulkBrandSerializer(data={'brands': data})

            if not bulk_serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                }, status=400)

            # Bulk create z serializers
            with transaction.atomic():
                created_objects = []
                errors = []

                for brand_data in data:
                    serializer = BrandSerializer(data=brand_data)
                    if serializer.is_valid():
                        brand = serializer.save()
                        created_objects.append(brand)
                    else:
                        errors.append({
                            'brand_id': brand_data.get('brand_id', 'unknown'),
                            'errors': serializer.errors
                        })

                # Log operacji
                ApiSyncLog.objects.create(
                    sync_type='brands_bulk_create',
                    status='success' if not errors else 'partial',
                    records_processed=len(data),
                    records_created=len(created_objects),
                    records_errors=len(errors),
                    error_details=json.dumps(errors) if errors else '',
                    completed_at=timezone.now()
                )

            response_data = {
                'success': True,
                'message': f'Utworzono {len(created_objects)} marek',
                'created_count': len(created_objects),
                'processed_count': len(data)
            }

            if errors:
                response_data['errors'] = errors
                response_data['message'] += f', {len(errors)} błędów'

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Nieprawidłowy format JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Błąd w BrandBulkCreateView: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Błąd serwera: {str(e)}'
            }, status=500)


class CategoryBulkView(BaseBulkView):
    def get_model(self):
        return Category


@extend_schema(
    operation_id='categories_bulk_create',
    summary='Masowe tworzenie kategorii',
    description='Tworzy wiele kategorii jednocześnie.',
    tags=['Categories'],
    request=BulkCategorySerializer,
    responses={
        200: {'description': 'Kategorie zostały pomyślnie utworzone'},
        400: {'description': 'Błąd walidacji danych'},
        500: {'description': 'Błąd serwera'}
    }
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class CategoryBulkCreateView(View):
    """Bulk create dla kategorii"""

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)

            if not isinstance(data, list):
                return JsonResponse({
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                }, status=400)

            # Użyj BulkCategorySerializer
            bulk_serializer = BulkCategorySerializer(data={'categories': data})

            if not bulk_serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                }, status=400)

            # Bulk create z serializers
            with transaction.atomic():
                created_objects = []
                errors = []

                for category_data in data:
                    serializer = CategorySerializer(data=category_data)
                    if serializer.is_valid():
                        category = serializer.save()
                        created_objects.append(category)
                    else:
                        errors.append({
                            'category_id': category_data.get('category_id', 'unknown'),
                            'errors': serializer.errors
                        })

                # Log operacji
                ApiSyncLog.objects.create(
                    sync_type='categories_bulk_create',
                    status='success' if not errors else 'partial',
                    records_processed=len(data),
                    records_created=len(created_objects),
                    records_errors=len(errors),
                    error_details=json.dumps(errors) if errors else '',
                    completed_at=timezone.now()
                )

            response_data = {
                'success': True,
                'message': f'Utworzono {len(created_objects)} kategorii',
                'created_count': len(created_objects),
                'processed_count': len(data)
            }

            if errors:
                response_data['errors'] = errors
                response_data['message'] += f', {len(errors)} błędów'

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Nieprawidłowy format JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Błąd w CategoryBulkCreateView: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Błąd serwera: {str(e)}'
            }, status=500)


class ImageBulkView(BaseBulkView):
    def get_model(self):
        return ProductImage


@extend_schema(
    operation_id='images_bulk_create',
    summary='Masowe tworzenie obrazów',
    description='Tworzy wiele obrazów produktów jednocześnie.',
    tags=['Images'],
    request=BulkImageSerializer,
    responses={
        200: {'description': 'Obrazy zostały pomyślnie utworzone'},
        400: {'description': 'Błąd walidacji danych'},
        500: {'description': 'Błąd serwera'}
    }
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class ImageBulkCreateView(View):
    """Bulk create dla obrazów"""

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)

            if not isinstance(data, list):
                return JsonResponse({
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                }, status=400)

            # Użyj BulkImageSerializer
            bulk_serializer = BulkImageSerializer(data={'images': data})

            if not bulk_serializer.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                }, status=400)

            # Bulk create z serializers
            with transaction.atomic():
                created_objects = []
                errors = []

                for image_data in data:
                    # Sprawdź czy product_id istnieje
                    product_id = image_data.get('product_id')
                    if not product_id:
                        errors.append({
                            'image_url': resolve_image_url(image_data.get('image_url')) or image_data.get('image_url', 'unknown'),
                            'errors': {'product_id': ['Product ID jest wymagane']}
                        })
                        continue

                    try:
                        product = Product.objects.get(product_id=product_id)
                        image_data['product'] = product.id
                        serializer = ProductImageSerializer(data=image_data)

                        if serializer.is_valid():
                            image = serializer.save()
                            created_objects.append(image)
                        else:
                            errors.append({
                                'image_url': resolve_image_url(image_data.get('image_url')) or image_data.get('image_url', 'unknown'),
                                'errors': serializer.errors
                            })
                    except Product.DoesNotExist:
                        errors.append({
                            'image_url': resolve_image_url(image_data.get('image_url')) or image_data.get('image_url', 'unknown'),
                            'errors': {'product_id': ['Produkt nie istnieje']}
                        })

                # Log operacji
                ApiSyncLog.objects.create(
                    sync_type='images_bulk_create',
                    status='success' if not errors else 'partial',
                    records_processed=len(data),
                    records_created=len(created_objects),
                    records_errors=len(errors),
                    error_details=json.dumps(errors) if errors else '',
                    completed_at=timezone.now()
                )

            response_data = {
                'success': True,
                'message': f'Utworzono {len(created_objects)} obrazów',
                'created_count': len(created_objects),
                'processed_count': len(data)
            }

            if errors:
                response_data['errors'] = errors
                response_data['message'] += f', {len(errors)} błędów'

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Nieprawidłowy format JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Błąd w ImageBulkCreateView: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Błąd serwera: {str(e)}'
            }, status=500)


@extend_schema(
    operation_id='api_sync',
    summary='Synchronizacja z API',
    description='Endpoint do synchronizacji z zewnętrznym API (do implementacji).',
    tags=['Sync'],
    responses={
        200: {'description': 'Synchronizacja została uruchomiona'}
    }
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class APISyncView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        return JsonResponse({'message': 'APISyncView - do implementacji'})


@extend_schema(
    operation_id='product_sync',
    summary='Synchronizacja produktów',
    description='Endpoint do synchronizacji produktów z zewnętrznym API (do implementacji).',
    tags=['Sync'],
    responses={
        200: {'description': 'Synchronizacja produktów została uruchomiona'}
    }
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class ProductSyncView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        return JsonResponse({'message': 'ProductSyncView - do implementacji'})


@extend_schema(
    operation_id='variant_sync',
    summary='Synchronizacja wariantów',
    description='Endpoint do synchronizacji wariantów produktów z zewnętrznym API (do implementacji).',
    tags=['Sync'],
    responses={
        200: {'description': 'Synchronizacja wariantów została uruchomiona'}
    }
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class VariantSyncView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        return JsonResponse({'message': 'VariantSyncView - do implementacji'})


@extend_schema(
    operation_id='api_status',
    summary='Status API',
    description='Sprawdza status API i zwraca podstawowe informacje o systemie.',
    tags=['Sync'],
    responses={
        200: {'description': 'Status API został pobrany pomyślnie'}
    }
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class APIStatusView(View):
    def get(self, request):
        return JsonResponse({'message': 'APIStatusView - do implementacji'})


@extend_schema(
    operation_id='api_logs',
    summary='Logi API',
    description='Zwraca logi operacji API i synchronizacji.',
    tags=['Sync'],
    responses={
        200: {'description': 'Logi zostały pobrane pomyślnie'}
    }
) if DRF_SPECTACULAR_AVAILABLE else extend_schema()
class APILogsView(View):
    def get(self, request):
        return JsonResponse({'message': 'APILogsView - do implementacji'})


@csrf_exempt
def get_product_details(request, product_id):
    """
    API endpoint do pobierania szczegółów produktu z matterhorn1
    """
    try:
        product = Product.objects.select_related(
            'brand', 'category').get(product_id=product_id)

        # Pobierz warianty
        variants = []
        for variant in product.variants.all():
            variants.append({
                'variant_uid': variant.variant_uid,
                'name': variant.name,
                'stock': variant.stock,
                'ean': variant.ean,
                'max_processing_time': variant.max_processing_time
            })

        # Pobierz obrazy
        images = []
        for image in product.images.all().order_by('order'):
            images.append({
                'image_url': resolve_image_url(image.image_url) or image.image_url,
                'order': image.order
            })

        # Pobierz szczegóły produktu
        details = None
        if hasattr(product, 'details'):
            details = {
                'weight': product.details.weight,
                'size_table': product.details.size_table,
                'size_table_txt': product.details.size_table_txt,
                'size_table_html': product.details.size_table_html
            }

        return JsonResponse({
            'success': True,
            'product': {
                'product_id': product.product_uid,
                'name': product.name,
                'description': product.description,
                'active': product.active,
                'creation_date': product.creation_date.isoformat() if product.creation_date else None,
                'color': product.color,
                'url': product.url,
                'new_collection': product.new_collection,
                'products_in_set': product.products_in_set,
                'other_colors': product.other_colors,
                'prices': product.prices,
                'brand': {
                    'brand_id': product.brand.brand_id,
                    'name': product.brand.name
                } if product.brand else None,
                'category': {
                    'category_id': product.category.category_id,
                    'name': product.category.name,
                    'path': product.category.path
                } if product.category else None,
                'variants': variants,
                'images': images,
                'details': details,
                'mapped_product_uid': product.mapped_product_uid
            }
        })

    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Produkt nie został znaleziony'
        }, status=404)

    except Exception as e:
        logger.error(f"Błąd podczas pobierania produktu: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Błąd serwera: {str(e)}'
        }, status=500)
