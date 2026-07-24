import json
import logging
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connections
from django.db.models import OuterRef, Subquery
from django.utils.html import format_html

from .models import (
    Brand, Category, ApiSyncLog, TabuProduct, TabuProductImage, TabuProductVariant,
    StockHistory, Saga, SagaStep,
)
from . import bestsellers_data
from core.db_routers import _get_mpd_db, _get_tabu_db
from core.wholesaler_admin import (
    make_scoped_filter, render_product_thumbnail, fuzzy_suggest_mpd_products,
    build_mpd_change_context, StockHistoryAdminBase, ReadOnlyLogAdminMixin,
    RouterScopedQuerysetMixin,
)


logger = logging.getLogger(__name__)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['brand_id', 'name', 'last_api_sync', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at', 'last_api_sync']
    search_fields = ['brand_id', 'name']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync']
    ordering = ['name']

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('brand_id', 'name', 'logo_url', 'description')
        }),
        ('Synchronizacja', {
            'fields': ('last_api_sync',)
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_id', 'name', 'parent', 'path', 'last_api_sync', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at', 'parent']
    search_fields = ['category_id', 'name', 'path']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync']
    ordering = ['name']

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('category_id', 'name', 'path', 'parent', 'description')
        }),
        ('Synchronizacja', {
            'fields': ('last_api_sync',)
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


TabuBrandFilter = make_scoped_filter(
    title='Marka', parameter_name='brand', counterpart_parameter_name='category',
    related_model=Brand,
)
TabuCategoryFilter = make_scoped_filter(
    title='Kategoria', parameter_name='category', counterpart_parameter_name='brand',
    related_model=Category,
)


class TabuProductImageInline(admin.TabularInline):
    model = TabuProductImage
    extra = 0
    fields = ['api_image_id', 'image_preview', 'image_url', 'is_main', 'order']
    readonly_fields = ['api_image_id', 'image_preview']

    def image_preview(self, obj):
        if obj and obj.image_url:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 80px; max-height: 80px;" /></a>',
                obj.image_url, obj.image_url
            )
        return '-'
    image_preview.short_description = 'Podgląd'


class TabuProductVariantInline(admin.TabularInline):
    model = TabuProductVariant
    extra = 0
    fields = ['api_id', 'symbol', 'color', 'size', 'store', 'price_gross', 'ean']
    readonly_fields = ['api_id']


@admin.register(TabuProduct)
class TabuProductAdmin(admin.ModelAdmin):
    list_display = [
        'product_image_thumbnail', 'api_id', 'name', 'brand', 'category', 'symbol', 'price_gross',
        'store_total', 'stock_history_link', 'is_mapped_mpd', 'last_update'
    ]
    list_display_links = ['api_id', 'name']
    list_filter = [TabuBrandFilter, TabuCategoryFilter, 'last_update']
    search_fields = ['name', 'symbol', 'ean', 'producer_name', 'brand__name', 'category__name']
    readonly_fields = ['api_id', 'last_update', 'image_preview', 'mapped_product_uid']
    ordering = ['-api_id']
    inlines = [TabuProductImageInline, TabuProductVariantInline]
    change_form_template = 'admin/tabu/tabuproduct/change_form.html'

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('api_id', 'name', 'desc_short', 'desc_long', 'desc_safety', 'brand', 'category', 'symbol', 'ean')
        }),
        ('Obraz główny', {
            'fields': ('image_url', 'image_preview'),
            'classes': ('collapse',)
        }),
        ('Ceny i VAT', {
            'fields': ('price_net', 'price_gross', 'price_old', 'vat_label', 'vat_value')
        }),
        ('Stan i dostępność', {
            'fields': ('store_total', 'unit_label', 'status_label', 'status_auto', 'hidden_search')
        }),
        ('Linki i metadane', {
            'fields': ('url', 'version_signature', 'last_update'),
            'classes': ('collapse',)
        }),
        ('Grupy i słowniki', {
            'fields': ('groups', 'dictionaries'),
            'classes': ('collapse',)
        }),
        ('Dane API (backup)', {
            'fields': ('category_path', 'api_category_id', 'producer_name', 'api_producer_id', 'producer_code'),
            'classes': ('collapse',)
        }),
        ('Mapowanie MPD', {
            'fields': ('mapped_product_uid',),
            'classes': ('collapse',)
        }),
    )

    def is_mapped_mpd(self, obj):
        return bool(obj.mapped_product_uid) if obj else False
    is_mapped_mpd.boolean = True
    is_mapped_mpd.short_description = 'MPD'

    def stock_history_link(self, obj):
        """Link do widoku historii stanów magazynowych produktu"""
        from django.urls import reverse
        url = reverse('admin:tabu-stock-history', args=[obj.pk])
        return format_html('<a href="{}">📈 Historia</a>', url)
    stock_history_link.short_description = 'Historia stanów'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('mpd-create/<int:product_id>/', self.admin_site.admin_view(self.mpd_create), name='tabu-mpd-create'),
            path('assign-mapping/<int:product_id>/<int:mpd_product_id>/', self.admin_site.admin_view(self.assign_mapping), name='tabu-assign-mapping'),
            path('stock-history/<int:product_id>/', self.admin_site.admin_view(self.stock_history_view), name='tabu-stock-history'),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        try:
            product = TabuProduct.objects.select_related('brand').get(pk=object_id)
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
            extra_context.update(mpd_context)
        except TabuProduct.DoesNotExist:
            extra_context['is_mapped'] = False
            extra_context['suggested_products'] = []
        except Exception as e:
            logger.exception("Błąd change_view Tabu: %s", e)
            extra_context['is_mapped'] = False
            extra_context['suggested_products'] = []

        return super().change_view(request, object_id, form_url, extra_context)

    @method_decorator(csrf_exempt)
    @method_decorator(require_http_methods(["POST"]))
    def mpd_create(self, request, product_id):
        """Tworzy nowy produkt w MPD na podstawie danych Tabu i formularza."""
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
            'mpd_paths': request.POST.getlist('mpd_paths'),
            'mpd_attributes': request.POST.getlist('mpd_attributes'),
            'fabric_component': request.POST.getlist('fabric_component[]'),
            'fabric_percentage': request.POST.getlist('fabric_percentage[]'),
            'upload_images': True,
        }
        from .services import create_mpd_product_from_tabu
        result = create_mpd_product_from_tabu(int(product_id), form_data)
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f'Utworzono produkt w MPD (ID: {result["mpd_product_id"]})',
                'mpd_product_id': result['mpd_product_id'],
            })
        status_code = 404 if (result.get('error_message') or '').find('nie istnieje') >= 0 else 400
        # Tylko znane komunikaty biznesowe — bez surowych wyjątków (py/stack-trace-exposure)
        err = result.get('error_message') or ''
        safe = {
            'Produkt Tabu nie istnieje',
            'Produkt jest już zmapowany do MPD',
            'Saga zakończona kompensacją',
        }
        if err not in safe:
            err = 'Nie udało się utworzyć produktu w MPD'
        return JsonResponse({'success': False, 'error': err}, status=status_code)

    @method_decorator(csrf_exempt)
    @method_decorator(require_http_methods(["POST"]))
    def assign_mapping(self, request, product_id, mpd_product_id):
        """Przypisuje istniejący produkt MPD do produktu Tabu (wzór: matterhorn1 assign_mapping)."""
        try:
            tabu_product = TabuProduct.objects.get(pk=product_id)
        except TabuProduct.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Produkt Tabu nie istnieje'}, status=404)
        try:
            from MPD.models import ProductVariants
            from tabu.services import create_mpd_variants_from_tabu, upload_tabu_images_to_mpd

            mpd_db = _get_mpd_db()
            if not ProductVariants.objects.using(mpd_db).filter(product_id=mpd_product_id).exists():
                return JsonResponse({'success': False, 'error': 'Produkt MPD nie istnieje'}, status=404)

            tabu_product.mapped_product_uid = mpd_product_id
            tabu_product.save(update_fields=['mapped_product_uid'])

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
            mapping_info = {}
            if size_category:
                producer_code = request.POST.get('producer_code', '').strip() or None
                main_color_id = request.POST.get('main_color_id')
                main_color_id = int(main_color_id) if main_color_id and str(main_color_id).isdigit() else None
                try:
                    mapping_info = create_mpd_variants_from_tabu(
                        mpd_product_id,
                        product_id,
                        size_category,
                        producer_code=producer_code,
                        main_color_id=main_color_id,
                        producer_color_name=producer_color_name,
                    )
                    logger.info("Wynik dodawania wariantów Tabu→MPD: %s", mapping_info)
                except Exception as e:
                    logger.exception("Błąd podczas dodawania wariantów Tabu→MPD: %s", e)
                    mapping_info = {'error': 'Wystąpił błąd'}

            # Upload zdjęć do bucketa i MPD (jak w Matterhorn1)
            try:
                upload_result = upload_tabu_images_to_mpd(
                    mpd_product_id, product_id, producer_color_name=producer_color_name
                )
                mapping_info['uploaded_images'] = upload_result.get('uploaded_images', 0)
                if upload_result.get('upload_error'):
                    mapping_info['upload_error'] = upload_result['upload_error']
                logger.info("Wynik uploadu zdjęć Tabu→MPD: %s", upload_result)
            except Exception as e:
                logger.exception("Błąd podczas uploadu zdjęć Tabu→MPD: %s", e)
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
            logger.exception("Błąd assign_mapping Tabu: %s", e)
            return JsonResponse({'success': False, 'error': 'Wystąpił błąd'}, status=500)

    def stock_history_view(self, request, product_id):
        """Widok historii stanów magazynowych dla pojedynczego produktu (wykres + tabelka per wariant)"""
        from collections import defaultdict
        from datetime import timedelta

        from django.shortcuts import get_object_or_404, render
        from django.utils import timezone

        product = get_object_or_404(TabuProduct, pk=product_id)

        days_param = request.GET.get('days', '90')
        days = None if days_param == 'all' else int(days_param)

        history_qs = StockHistory.objects.filter(product_api_id=product.api_id)
        if days:
            cutoff = timezone.now() - timedelta(days=days)
            history_qs = history_qs.filter(timestamp__gte=cutoff)
        records = list(history_qs.order_by('timestamp'))

        variants = {v.api_id: v for v in product.api_variants.all()}

        # Punkt startowy dla każdego wariantu = old_stock pierwszego zdarzenia w oknie
        # (albo aktualny stan, jeśli w oknie nie ma żadnych zdarzeń).
        running_stock = {
            vid: v.store for vid, v in variants.items()
        }
        first_seen = set()
        for r in records:
            if r.variant_api_id not in first_seen:
                first_seen.add(r.variant_api_id)
                if r.old_stock is not None:
                    running_stock[r.variant_api_id] = r.old_stock

        def variant_label(vid):
            v = variants.get(vid)
            if v:
                return v.symbol or f'{v.size} {v.color}'.strip() or str(vid)
            return str(vid)

        variant_series = defaultdict(list)
        variant_labels = {vid: variant_label(vid) for vid in variants}
        total_points = []
        for r in records:
            variant_labels.setdefault(r.variant_api_id, r.variant_symbol or str(r.variant_api_id))
            variant_series[r.variant_api_id].append({
                'x': r.timestamp.isoformat(),
                'y': r.new_stock,
            })
            if r.new_stock is not None:
                running_stock[r.variant_api_id] = r.new_stock
            total_points.append({
                'x': r.timestamp.isoformat(),
                'y': sum(v for v in running_stock.values() if v is not None),
            })

        chart_datasets = [
            {'label': variant_labels.get(vid, vid), 'data': pts}
            for vid, pts in sorted(variant_series.items(), key=lambda kv: variant_labels.get(kv[0], kv[0]))
        ]

        context = {
            **self.admin_site.each_context(request),
            'title': f'Historia stanów magazynowych — {product.name}',
            'product': product,
            'opts': self.model._meta,
            'days': days_param,
            'chart_datasets_json': json.dumps(chart_datasets),
            'total_series_json': json.dumps(total_points),
            'current_variants': sorted(variants.values(), key=lambda v: v.symbol),
            'records': list(reversed(records)),
            'has_history': bool(records),
        }
        return render(
            request,
            'admin/tabu/stock_history/product_detail.html',
            context,
        )

    def image_preview(self, obj):
        if obj and obj.image_url:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 200px; max-height: 200px;" /></a>',
                obj.image_url, obj.image_url
            )
        return '-'
    image_preview.short_description = 'Podgląd'

    def product_image_thumbnail(self, obj):
        """Wyświetl miniaturę zdjęcia produktu na liście."""
        original_url = getattr(obj, 'image_url', None) or getattr(obj, 'first_gallery_image_url', None)
        return render_product_thumbnail(original_url, fallback_host='tabu.com.pl')
    product_image_thumbnail.short_description = 'Zdjęcie'

    def get_queryset(self, request):
        first_gallery_image_subquery = (
            TabuProductImage.objects.filter(
                product_id=OuterRef('pk')
            )
            .order_by('-is_main', 'order', 'id')
            .values('image_url')[:1]
        )

        return (
            super()
            .get_queryset(request)
            .select_related('brand', 'category')
            .annotate(first_gallery_image_url=Subquery(first_gallery_image_subquery))
        )


@admin.register(TabuProductImage)
class TabuProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_preview', 'is_main', 'order']
    list_filter = ['is_main']
    search_fields = ['product__name', 'image_url']
    readonly_fields = ['api_image_id', 'image_preview']
    ordering = ['product', 'order']

    fieldsets = (
        ('Produkt', {
            'fields': ('product', 'api_image_id')
        }),
        ('Obraz', {
            'fields': ('image_preview', 'image_url', 'is_main', 'order')
        }),
    )

    def image_preview(self, obj):
        if obj and obj.image_url:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 80px; max-height: 80px;" /></a>',
                obj.image_url, obj.image_url
            )
        return '-'
    image_preview.short_description = 'Podgląd'


@admin.register(TabuProductVariant)
class TabuProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        'api_id', 'product', 'symbol', 'color', 'size', 'store', 'price_gross',
        'is_mapped', 'mapped_variant_uid',
    ]
    list_filter = ['is_mapped', 'product__brand', 'product__category']
    search_fields = ['symbol', 'ean', 'product__name']
    readonly_fields = ['api_id', 'mapped_variant_uid']
    raw_id_fields = ['product']

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('api_id', 'product', 'symbol', 'color', 'size', 'ean')
        }),
        ('Ceny i VAT', {
            'fields': ('price_net', 'price_gross', 'price_kind', 'vat_label', 'vat_id', 'vat_value')
        }),
        ('Stan magazynowy', {
            'fields': ('store', 'weight')
        }),
        ('Mapowanie do MPD', {
            'fields': ('is_mapped', 'mapped_variant_uid'),
            'classes': ('collapse',)
        }),
        ('Dane API (backup)', {
            'fields': ('items', 'stores', 'raw_data'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ApiSyncLog)
class ApiSyncLogAdmin(ReadOnlyLogAdminMixin, admin.ModelAdmin):
    list_display = [
        'sync_type', 'status', 'started_at', 'completed_at',
        'products_processed', 'products_success', 'products_failed',
        'stock_changes_display', 'error_message',
    ]
    list_filter = ['status', 'sync_type', 'started_at']
    search_fields = ['sync_type', 'error_message']
    readonly_fields = ['started_at', 'completed_at', 'raw_response']
    ordering = ['-started_at']

    def stock_changes_display(self, obj):
        """Liczba zmian stanów zapisanych w historii (z raw_response)."""
        if obj.raw_response and isinstance(obj.raw_response, dict):
            n = obj.raw_response.get('stock_changes_logged')
            if n is not None:
                return n
        return '-'
    stock_changes_display.short_description = 'Zmiany historii'


@admin.register(Saga)
class SagaAdmin(RouterScopedQuerysetMixin, admin.ModelAdmin):
    """Admin interface dla Saga operations"""

    db_alias_getter = staticmethod(_get_tabu_db)

    list_display = [
        'saga_id', 'saga_type', 'status', 'created_at',
        'completed_at', 'total_steps', 'completed_steps'
    ]
    list_filter = ['status', 'saga_type', 'created_at']
    search_fields = ['saga_id', 'saga_type', 'error_message']
    readonly_fields = [
        'saga_id', 'created_at', 'started_at', 'completed_at',
        'total_steps', 'completed_steps', 'failed_step'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('saga_id', 'saga_type', 'status')
        }),
        ('Metadane', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
        ('Statystyki', {
            'fields': ('total_steps', 'completed_steps', 'failed_step')
        }),
        ('Dane', {
            'fields': ('input_data', 'output_data'),
            'classes': ('collapse',)
        }),
        ('Błędy', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )


@admin.register(SagaStep)
class SagaStepAdmin(RouterScopedQuerysetMixin, admin.ModelAdmin):
    """Admin interface dla Saga steps"""

    db_alias_getter = staticmethod(_get_tabu_db)

    list_display = [
        'saga', 'step_order', 'step_name', 'status',
        'started_at', 'completed_at', 'compensation_attempted'
    ]
    list_filter = ['status', 'compensation_attempted', 'compensation_successful']
    search_fields = ['step_name', 'error_message']
    readonly_fields = [
        'saga', 'step_order', 'step_name', 'started_at',
        'completed_at', 'compensated_at', 'compensation_attempted',
        'compensation_successful'
    ]
    ordering = ['saga', 'step_order']

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('saga', 'step_order', 'step_name', 'status')
        }),
        ('Metadane', {
            'fields': ('started_at', 'completed_at', 'compensated_at')
        }),
        ('Kompensacja', {
            'fields': ('compensation_attempted', 'compensation_successful')
        }),
        ('Dane', {
            'fields': ('input_data', 'output_data'),
            'classes': ('collapse',)
        }),
        ('Błędy', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Nie pozwalaj na ręczne dodawanie kroków"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Nie pozwalaj na usuwanie kroków — w odróżnieniu od innych logów/audytu,
        kroki Sagi muszą zostać dla diagnostyki nieudanych operacji cross-DB."""
        return False


@admin.register(StockHistory)
class StockHistoryAdmin(ReadOnlyLogAdminMixin, StockHistoryAdminBase):
    list_display = ['product_name', 'variant_symbol', 'old_stock', 'new_stock', 'stock_change', 'change_type', 'timestamp']
    list_filter = ['change_type', 'timestamp']
    search_fields = ['product_name', 'variant_symbol']
    readonly_fields = ['timestamp']
    change_list_template = 'admin/tabu/stock_history/change_list.html'

    bestsellers_data_module = bestsellers_data
    bestsellers_template = 'admin/tabu/stock_history/bestsellers.html'
    bestsellers_url_name = 'tabu_stockhistory_bestsellers'
    bestsellers_title = 'Bestsellery — Tabu'
