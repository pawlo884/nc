import logging

from django.contrib import admin
from django.db import connections
from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import (
    Brand, Category, ApiSyncLog, MadaProduct, MadaProductImage, MadaProductVariant,
    StockHistory, Saga, SagaStep,
)
from core.db_routers import _get_mada_db, _get_mpd_db
from core.wholesaler_admin import (
    make_scoped_filter, render_product_thumbnail, fuzzy_suggest_mpd_products,
    build_mpd_change_context, ReadOnlyLogAdminMixin,
    RouterScopedQuerysetMixin,
)

logger = logging.getLogger(__name__)


@admin.register(Brand)
class BrandAdmin(RouterScopedQuerysetMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = ['producer_id', 'name', 'created_at', 'updated_at']
    search_fields = ['producer_id', 'name']
    ordering = ['name']


@admin.register(Category)
class CategoryAdmin(RouterScopedQuerysetMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = ['category_id', 'name', 'parent', 'path', 'created_at']
    list_filter = ['parent']
    search_fields = ['category_id', 'name', 'path']
    ordering = ['name']


MadaBrandFilter = make_scoped_filter(
    title='Marka', parameter_name='brand', counterpart_parameter_name='category',
    related_model=Brand,
)
MadaCategoryFilter = make_scoped_filter(
    title='Kategoria', parameter_name='category', counterpart_parameter_name='brand',
    related_model=Category,
)


class MadaProductImageInline(admin.TabularInline):
    model = MadaProductImage
    extra = 0
    fields = ['api_image_id', 'image_preview', 'image_url', 'order']
    readonly_fields = ['api_image_id', 'image_preview']

    def image_preview(self, obj):
        if obj and obj.image_url:
            return render_product_thumbnail(obj.image_url, fallback_host='mada.pl')
        return '-'
    image_preview.short_description = 'Podgląd'


class MadaProductVariantInline(admin.TabularInline):
    model = MadaProductVariant
    extra = 0
    fields = ['variant_key', 'color', 'size', 'ean', 'stock', 'is_mapped', 'mapped_variant_uid']
    readonly_fields = ['variant_key']


@admin.register(MadaProduct)
class MadaProductAdmin(RouterScopedQuerysetMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = [
        'api_id', 'thumbnail', 'name', 'brand', 'category', 'price', 'old_price',
        'is_active', 'mapped_product_uid', 'updated_at',
    ]
    list_filter = ['is_active', MadaBrandFilter, MadaCategoryFilter]
    search_fields = ['api_id', 'name']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync', 'raw_data', 'mapped_product_uid']
    inlines = [MadaProductVariantInline, MadaProductImageInline]
    ordering = ['-api_id']
    change_form_template = 'admin/mada/madaproduct/change_form.html'

    def get_queryset(self, request):
        first_image_subquery = (
            MadaProductImage.objects.filter(product_id=OuterRef('pk'))
            .order_by('order', 'api_image_id')
            .values('image_url')[:1]
        )
        return (
            super()
            .get_queryset(request)
            .select_related('brand', 'category')
            .annotate(first_image_url=Subquery(first_image_subquery))
        )

    def thumbnail(self, obj):
        url = getattr(obj, 'first_image_url', None)
        if url:
            return render_product_thumbnail(url, fallback_host='mada.pl')
        return '-'
    thumbnail.short_description = 'Zdjęcie'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('mpd-create/<int:product_id>/', self.admin_site.admin_view(self.mpd_create), name='mada-mpd-create'),
            path('assign-mapping/<int:product_id>/<int:mpd_product_id>/', self.admin_site.admin_view(self.assign_mapping), name='mada-assign-mapping'),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        try:
            product = MadaProduct.objects.select_related('brand').get(pk=object_id)
            is_mapped = bool(product.mapped_product_uid)

            mpd_context = build_mpd_change_context(
                product.mapped_product_uid if is_mapped else None,
                mpd_db_alias=_get_mpd_db(),
            )
            mpd_context['is_mapped'] = is_mapped
            mpd_context['suggested_products'] = fuzzy_suggest_mpd_products(
                product.name, product.brand.name if product.brand else None,
                mpd_db_alias=_get_mpd_db(),
            )
            mpd_context['source_colors'] = sorted({
                (c or '').strip()
                for c in product.variants.values_list('color', flat=True)
                if c and c.strip()
            })
            extra_context.update(mpd_context)
        except MadaProduct.DoesNotExist:
            extra_context['is_mapped'] = False
            extra_context['suggested_products'] = []
        except Exception as e:
            logger.exception("Błąd change_view Mada: %s", e)
            extra_context['is_mapped'] = False
            extra_context['suggested_products'] = []

        return super().change_view(request, object_id, form_url, extra_context)

    @method_decorator(csrf_exempt)
    @method_decorator(require_http_methods(["POST"]))
    def mpd_create(self, request, product_id):
        """Tworzy nowy produkt w MPD na podstawie danych Mada i formularza."""
        form_data = {
            'mpd_name': request.POST.get('mpd_name'),
            'mpd_short_description': request.POST.get('mpd_short_description'),
            'mpd_description': request.POST.get('mpd_description'),
            'mpd_brand': request.POST.get('mpd_brand'),
            'series_name': request.POST.get('series_name'),
            'unit_id': request.POST.get('unit_id'),
            'main_color_id': request.POST.get('main_color_id'),
            'producer_color_name': request.POST.get('producer_color_name'),
            'producer_code': request.POST.get('producer_code'),
            'source_color': request.POST.get('source_color'),
            'mpd_paths': request.POST.getlist('mpd_paths'),
            'mpd_attributes': request.POST.getlist('mpd_attributes'),
            'fabric_component': request.POST.getlist('fabric_component[]'),
            'fabric_percentage': request.POST.getlist('fabric_percentage[]'),
            'upload_images': True,
        }
        from .services import create_mpd_product_from_mada
        result = create_mpd_product_from_mada(int(product_id), form_data)
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f'Utworzono produkt w MPD (ID: {result["mpd_product_id"]})',
                'mpd_product_id': result['mpd_product_id'],
            })
        status_code = 404 if (result.get('error_message') or '').find('nie istnieje') >= 0 else 400
        err = result.get('error_message') or ''
        safe = {
            'Produkt Mada nie istnieje',
            'Produkt jest już zmapowany do MPD',
            'Saga zakończona kompensacją',
        }
        if err not in safe:
            err = 'Nie udało się utworzyć produktu w MPD'
        return JsonResponse({'success': False, 'error': err}, status=status_code)

    @method_decorator(csrf_exempt)
    @method_decorator(require_http_methods(["POST"]))
    def assign_mapping(self, request, product_id, mpd_product_id):
        """Przypisuje istniejący produkt MPD do produktu Mada (wzór: tabu assign_mapping)."""
        try:
            mada_product = MadaProduct.objects.get(pk=product_id)
        except MadaProduct.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Produkt Mada nie istnieje'}, status=404)
        try:
            from MPD.models import ProductVariants
            from mada.services import create_mpd_variants_from_mada, upload_mada_images_to_mpd

            mpd_db = _get_mpd_db()
            if not ProductVariants.objects.using(mpd_db).filter(product_id=mpd_product_id).exists():
                return JsonResponse({'success': False, 'error': 'Produkt MPD nie istnieje'}, status=404)

            mada_product.mapped_product_uid = mpd_product_id
            mada_product.save(update_fields=['mapped_product_uid'])

            size_category = None
            with connections[mpd_db].cursor() as cursor:
                cursor.execute("""
                    SELECT s.category
                    FROM product_variants pv
                    JOIN sizes s ON pv.size_id = s.id
                    WHERE pv.product_id = %s
                    LIMIT 1
                """, [mpd_product_id])
                row = cursor.fetchone()
                if row and row[0]:
                    size_category = row[0]

            producer_color_name = (request.POST.get('producer_color_name') or '').strip() or None
            source_color = (request.POST.get('source_color') or '').strip() or None
            mapping_info = {}
            if size_category:
                producer_code = request.POST.get('producer_code', '').strip() or None
                main_color_id = request.POST.get('main_color_id')
                main_color_id = int(main_color_id) if main_color_id and str(main_color_id).isdigit() else None
                try:
                    mapping_info = create_mpd_variants_from_mada(
                        mpd_product_id,
                        product_id,
                        size_category,
                        producer_code=producer_code,
                        main_color_id=main_color_id,
                        producer_color_name=producer_color_name,
                        source_color=source_color,
                    )
                    logger.info("Wynik dodawania wariantów Mada→MPD: %s", mapping_info)
                except Exception as e:
                    logger.exception("Błąd podczas dodawania wariantów Mada→MPD: %s", e)
                    mapping_info = {'error': 'Wystąpił błąd'}

            try:
                upload_result = upload_mada_images_to_mpd(
                    mpd_product_id, product_id, producer_color_name=producer_color_name
                )
                mapping_info['uploaded_images'] = upload_result.get('uploaded_images', 0)
                if upload_result.get('upload_error'):
                    mapping_info['upload_error'] = upload_result['upload_error']
                logger.info("Wynik uploadu zdjęć Mada→MPD: %s", upload_result)
            except Exception as e:
                logger.exception("Błąd podczas uploadu zdjęć Mada→MPD: %s", e)
                mapping_info['upload_error'] = 'Błąd uploadu zdjęć'

            if not size_category and not mapping_info.get('error'):
                mapping_info['error'] = 'Brak kategorii rozmiarowej w MPD (produkt bez wariantów z rozmiarem?).'

            created = mapping_info.get('created_variants', 0)
            uploaded = mapping_info.get('uploaded_images', 0)
            msg = f'Przypisano do MPD ID {mpd_product_id}. Wariantów: {created}. Zdjęć: {uploaded}.'
            return JsonResponse({
                'success': True,
                'message': msg,
                'mapping_info': mapping_info,
            })
        except Exception as e:
            logger.exception("Błąd assign_mapping Mada: %s", e)
            return JsonResponse({'success': False, 'error': 'Wystąpił błąd'}, status=500)


@admin.register(MadaProductVariant)
class MadaProductVariantAdmin(RouterScopedQuerysetMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = [
        'product', 'color', 'size', 'ean', 'stock', 'is_mapped', 'mapped_variant_uid', 'updated_at',
    ]
    list_filter = ['is_mapped']
    search_fields = ['ean', 'variant_key', 'product__name', 'product__api_id']


@admin.register(ApiSyncLog)
class ApiSyncLogAdmin(RouterScopedQuerysetMixin, ReadOnlyLogAdminMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = [
        'sync_type', 'status', 'file_name', 'started_at', 'completed_at',
        'products_processed', 'products_created', 'products_updated', 'products_failed',
    ]
    list_filter = ['sync_type', 'status']
    ordering = ['-started_at']


@admin.register(StockHistory)
class StockHistoryAdmin(RouterScopedQuerysetMixin, ReadOnlyLogAdminMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = [
        'product_name', 'variant_label', 'old_stock', 'new_stock', 'stock_change',
        'change_type', 'timestamp',
    ]
    list_filter = ['change_type']
    search_fields = ['product_name', 'product_api_id', 'variant_key']
    ordering = ['-timestamp']


@admin.register(Saga)
class SagaAdmin(RouterScopedQuerysetMixin, ReadOnlyLogAdminMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = ['saga_id', 'saga_type', 'status', 'completed_steps', 'total_steps', 'created_at']
    list_filter = ['saga_type', 'status']
    search_fields = ['saga_id']
    ordering = ['-created_at']


@admin.register(SagaStep)
class SagaStepAdmin(RouterScopedQuerysetMixin, ReadOnlyLogAdminMixin, admin.ModelAdmin):
    db_alias_getter = staticmethod(_get_mada_db)
    list_display = ['saga', 'step_order', 'step_name', 'status', 'started_at', 'completed_at']
    list_filter = ['status']
    ordering = ['saga', 'step_order']
