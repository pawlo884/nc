import logging
import json
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle, AnonRateThrottle

from .models import (
    Product,
    Brand,
    Category,
    ProductImage,
    ProductVariant,
    ApiSyncLog,
)
from .serializers import (
    ProductSerializer,
    BrandSerializer,
    CategorySerializer,
    ProductVariantSerializer,
    ProductImageSerializer,
    BulkProductSerializer,
    BulkBrandSerializer,
    BulkCategorySerializer,
    BulkVariantSerializer,
    BulkImageSerializer,
)

logger = logging.getLogger(__name__)


class BulkThrottleMixin:
    throttle_scope = 'bulk'
    throttle_classes = [ScopedRateThrottle, UserRateThrottle, AnonRateThrottle]


class ProductBulkCreateAPI(BulkThrottleMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response(
                {
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bulk_serializer = BulkProductSerializer(data={'products': data})
        if not bulk_serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_objects = []
        errors = []

        with transaction.atomic():
            for product_data in data:
                try:
                    if product_data.get('creation_date'):
                        try:
                            product_data['creation_date'] = datetime.fromisoformat(
                                product_data['creation_date'].replace('Z', '+00:00')
                            )
                        except (ValueError, TypeError):
                            product_data['creation_date'] = None

                    serializer = ProductSerializer(data=product_data)
                    if serializer.is_valid():
                        created_objects.append(serializer.save())
                    else:
                        errors.append(
                            {
                                'product_id': product_data.get('product_id', 'unknown'),
                                'errors': serializer.errors,
                            }
                        )
                except Exception as exc:
                    logger.exception('Błąd podczas tworzenia produktu')
                    errors.append(
                        {
                            'product_id': product_data.get('product_id', 'unknown'),
                            'errors': [str(exc)],
                        }
                    )

            ApiSyncLog.objects.create(
                sync_type='products_bulk_create_secure',
                status='success' if not errors else 'partial',
                records_processed=len(data),
                records_created=len(created_objects),
                records_errors=len(errors),
                error_details=json.dumps(errors) if errors else '',
                completed_at=timezone.now(),
            )

        response_data = {
            'success': True,
            'message': f'Utworzono {len(created_objects)} produktów',
            'created_count': len(created_objects),
            'processed_count': len(data),
        }
        if errors:
            response_data['errors'] = errors
            response_data['message'] += f', {len(errors)} błędów'

        return Response(response_data)


class ProductBulkUpdateAPI(BulkThrottleMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response(
                {
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bulk_serializer = BulkProductSerializer(data={'products': data})
        if not bulk_serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_objects = []
        created_objects = []
        errors = []

        with transaction.atomic():
            for product_data in data:
                product_id = product_data.get('product_id')
                if not product_id:
                    errors.append(
                        {
                            'product_id': 'unknown',
                            'errors': {'product_id': ['Product ID jest wymagane']},
                        }
                    )
                    continue

                try:
                    product = Product.objects.get(product_id=product_id)
                    serializer = ProductSerializer(
                        product,
                        data=product_data,
                        partial=True,
                    )
                    if serializer.is_valid():
                        updated_objects.append(serializer.save())
                    else:
                        errors.append(
                            {
                                'product_id': product_id,
                                'errors': serializer.errors,
                            }
                        )
                except Product.DoesNotExist:
                    serializer = ProductSerializer(data=product_data)
                    if serializer.is_valid():
                        created_objects.append(serializer.save())
                    else:
                        errors.append(
                            {
                                'product_id': product_id,
                                'errors': serializer.errors,
                            }
                        )
                except Exception as exc:
                    logger.exception('Błąd podczas aktualizacji produktu')
                    errors.append(
                        {
                            'product_id': product_id,
                            'errors': [str(exc)],
                        }
                    )

            ApiSyncLog.objects.create(
                sync_type='products_bulk_update_secure',
                status='success' if not errors else 'partial',
                records_processed=len(data),
                records_updated=len(updated_objects),
                records_created=len(created_objects),
                records_errors=len(errors),
                error_details=json.dumps(errors) if errors else '',
                completed_at=timezone.now(),
            )

        response_data = {
            'success': True,
            'message': f'Zaktualizowano {len(updated_objects)} produktów',
            'updated_count': len(updated_objects),
            'created_count': len(created_objects),
            'processed_count': len(data),
        }
        if errors:
            response_data['errors'] = errors
            response_data['message'] += f', {len(errors)} błędów'

        return Response(response_data)


class VariantBulkCreateAPI(BulkThrottleMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response(
                {
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bulk_serializer = BulkVariantSerializer(data={'variants': data})
        if not bulk_serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_objects = []
        errors = []

        with transaction.atomic():
            for variant_data in data:
                product_id = variant_data.get('product_id')
                if not product_id:
                    errors.append(
                        {
                            'variant_uid': variant_data.get('variant_uid', 'unknown'),
                            'errors': {'product_id': ['Product ID jest wymagane']},
                        }
                    )
                    continue

                try:
                    product = Product.objects.get(product_id=product_id)
                    variant_data['product'] = product.id
                    serializer = ProductVariantSerializer(data=variant_data)
                    if serializer.is_valid():
                        created_objects.append(serializer.save())
                    else:
                        errors.append(
                            {
                                'variant_uid': variant_data.get('variant_uid', 'unknown'),
                                'errors': serializer.errors,
                            }
                        )
                except Product.DoesNotExist:
                    errors.append(
                        {
                            'variant_uid': variant_data.get('variant_uid', 'unknown'),
                            'errors': {'product_id': ['Produkt nie istnieje']},
                        }
                    )
                except Exception as exc:
                    logger.exception('Błąd podczas tworzenia wariantu')
                    errors.append(
                        {
                            'variant_uid': variant_data.get('variant_uid', 'unknown'),
                            'errors': [str(exc)],
                        }
                    )

            ApiSyncLog.objects.create(
                sync_type='variants_bulk_create_secure',
                status='success' if not errors else 'partial',
                records_processed=len(data),
                records_created=len(created_objects),
                records_errors=len(errors),
                error_details=json.dumps(errors) if errors else '',
                completed_at=timezone.now(),
            )

        response_data = {
            'success': True,
            'message': f'Utworzono {len(created_objects)} wariantów',
            'created_count': len(created_objects),
            'processed_count': len(data),
        }
        if errors:
            response_data['errors'] = errors
            response_data['message'] += f', {len(errors)} błędów'

        return Response(response_data)


class VariantBulkUpdateAPI(BulkThrottleMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response(
                {
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bulk_serializer = BulkVariantSerializer(data={'variants': data})
        if not bulk_serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_objects = []
        created_objects = []
        errors = []

        with transaction.atomic():
            for variant_data in data:
                variant_uid = variant_data.get('variant_uid')
                if not variant_uid:
                    errors.append(
                        {
                            'variant_uid': 'unknown',
                            'errors': {'variant_uid': ['Variant UID jest wymagane']},
                        }
                    )
                    continue

                try:
                    variant = ProductVariant.objects.get(variant_uid=variant_uid)
                    serializer = ProductVariantSerializer(
                        variant,
                        data=variant_data,
                        partial=True,
                    )
                    if serializer.is_valid():
                        updated_objects.append(serializer.save())
                    else:
                        errors.append(
                            {
                                'variant_uid': variant_uid,
                                'errors': serializer.errors,
                            }
                        )
                except ProductVariant.DoesNotExist:
                    serializer = ProductVariantSerializer(data=variant_data)
                    if serializer.is_valid():
                        created_objects.append(serializer.save())
                    else:
                        errors.append(
                            {
                                'variant_uid': variant_uid,
                                'errors': serializer.errors,
                            }
                        )
                except Exception as exc:
                    logger.exception('Błąd podczas aktualizacji wariantu')
                    errors.append(
                        {
                            'variant_uid': variant_uid,
                            'errors': [str(exc)],
                        }
                    )

            ApiSyncLog.objects.create(
                sync_type='variants_bulk_update_secure',
                status='success' if not errors else 'partial',
                records_processed=len(data),
                records_updated=len(updated_objects),
                records_created=len(created_objects),
                records_errors=len(errors),
                error_details=json.dumps(errors) if errors else '',
                completed_at=timezone.now(),
            )

        response_data = {
            'success': True,
            'message': f'Zaktualizowano {len(updated_objects)} wariantów',
            'updated_count': len(updated_objects),
            'created_count': len(created_objects),
            'processed_count': len(data),
        }
        if errors:
            response_data['errors'] = errors
            response_data['message'] += f', {len(errors)} błędów'

        return Response(response_data)


class BrandBulkCreateAPI(BulkThrottleMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response(
                {
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bulk_serializer = BulkBrandSerializer(data={'brands': data})
        if not bulk_serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_objects = []
        errors = []

        with transaction.atomic():
            for brand_data in data:
                serializer = BrandSerializer(data=brand_data)
                if serializer.is_valid():
                    created_objects.append(serializer.save())
                else:
                    errors.append(
                        {
                            'brand_id': brand_data.get('brand_id', 'unknown'),
                            'errors': serializer.errors,
                        }
                    )

            ApiSyncLog.objects.create(
                sync_type='brands_bulk_create_secure',
                status='success' if not errors else 'partial',
                records_processed=len(data),
                records_created=len(created_objects),
                records_errors=len(errors),
                error_details=json.dumps(errors) if errors else '',
                completed_at=timezone.now(),
            )

        response_data = {
            'success': True,
            'message': f'Utworzono {len(created_objects)} marek',
            'created_count': len(created_objects),
            'processed_count': len(data),
        }
        if errors:
            response_data['errors'] = errors
            response_data['message'] += f', {len(errors)} błędów'

        return Response(response_data)


class CategoryBulkCreateAPI(BulkThrottleMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response(
                {
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bulk_serializer = BulkCategorySerializer(data={'categories': data})
        if not bulk_serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_objects = []
        errors = []

        with transaction.atomic():
            for category_data in data:
                serializer = CategorySerializer(data=category_data)
                if serializer.is_valid():
                    created_objects.append(serializer.save())
                else:
                    errors.append(
                        {
                            'category_id': category_data.get('category_id', 'unknown'),
                            'errors': serializer.errors,
                        }
                    )

            ApiSyncLog.objects.create(
                sync_type='categories_bulk_create_secure',
                status='success' if not errors else 'partial',
                records_processed=len(data),
                records_created=len(created_objects),
                records_errors=len(errors),
                error_details=json.dumps(errors) if errors else '',
                completed_at=timezone.now(),
            )

        response_data = {
            'success': True,
            'message': f'Utworzono {len(created_objects)} kategorii',
            'created_count': len(created_objects),
            'processed_count': len(data),
        }
        if errors:
            response_data['errors'] = errors
            response_data['message'] += f', {len(errors)} błędów'

        return Response(response_data)


class ImageBulkCreateAPI(BulkThrottleMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response(
                {
                    'success': False,
                    'error': 'Dane muszą być listą obiektów'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bulk_serializer = BulkImageSerializer(data={'images': data})
        if not bulk_serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': 'Błędy walidacji',
                    'details': bulk_serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_objects = []
        errors = []

        with transaction.atomic():
            for image_data in data:
                product_id = image_data.get('product_id')
                if not product_id:
                    errors.append(
                        {
                            'image_url': image_data.get('image_url', 'unknown'),
                            'errors': {'product_id': ['Product ID jest wymagane']},
                        }
                    )
                    continue

                try:
                    product = Product.objects.get(product_id=product_id)
                    image_data['product'] = product.id
                    serializer = ProductImageSerializer(data=image_data)
                    if serializer.is_valid():
                        created_objects.append(serializer.save())
                    else:
                        errors.append(
                            {
                                'image_url': image_data.get('image_url', 'unknown'),
                                'errors': serializer.errors,
                            }
                        )
                except Product.DoesNotExist:
                    errors.append(
                        {
                            'image_url': image_data.get('image_url', 'unknown'),
                            'errors': {'product_id': ['Produkt nie istnieje']},
                        }
                    )
                except Exception as exc:
                    logger.exception('Błąd podczas tworzenia obrazu produktu')
                    errors.append(
                        {
                            'image_url': image_data.get('image_url', 'unknown'),
                            'errors': [str(exc)],
                        }
                    )

            ApiSyncLog.objects.create(
                sync_type='images_bulk_create_secure',
                status='success' if not errors else 'partial',
                records_processed=len(data),
                records_created=len(created_objects),
                records_errors=len(errors),
                error_details=json.dumps(errors) if errors else '',
                completed_at=timezone.now(),
            )

        response_data = {
            'success': True,
            'message': f'Utworzono {len(created_objects)} obrazów',
            'created_count': len(created_objects),
            'processed_count': len(data),
        }
        if errors:
            response_data['errors'] = errors
            response_data['message'] += f', {len(errors)} błędów'

        return Response(response_data)


class APISyncAPI(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        return Response(
            {'message': 'APISyncAPI - do implementacji'},
            status=status.HTTP_200_OK,
        )

