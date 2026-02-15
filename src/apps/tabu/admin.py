import logging
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.http import JsonResponse
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connections
from django.utils import timezone
from django.utils.html import format_html

from .models import Brand, Category, ApiSyncLog, TabuProduct, TabuProductImage, TabuProductVariant, StockHistory


logger = logging.getLogger(__name__)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand_id', 'last_api_sync', 'created_at']
    list_filter = ['created_at', 'updated_at', 'last_api_sync']
    search_fields = ['name', 'brand_id']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_id', 'parent', 'created_at']
    list_filter = ['created_at', 'updated_at', 'parent']
    search_fields = ['name', 'category_id', 'path']
    readonly_fields = ['created_at', 'updated_at', 'last_api_sync']


class TabuBrandFilter(SimpleListFilter):
    title = 'Marka'
    parameter_name = 'brand'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        if request.GET.get('category'):
            try:
                qs = qs.filter(category_id=int(request.GET['category']))
            except (ValueError, TypeError):
                pass
        brands = Brand.objects.filter(
            id__in=qs.exclude(brand__isnull=True).values_list('brand_id', flat=True).distinct()
        ).order_by('name')
        return [(str(b.id), b.name) for b in brands]

    def queryset(self, request, queryset):
        if self.value():
            try:
                return queryset.filter(brand_id=int(self.value()))
            except (ValueError, TypeError):
                return queryset
        return queryset


class TabuCategoryFilter(SimpleListFilter):
    title = 'Kategoria'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        if request.GET.get('brand'):
            try:
                qs = qs.filter(brand_id=int(request.GET['brand']))
            except (ValueError, TypeError):
                pass
        categories = Category.objects.filter(
            id__in=qs.exclude(category__isnull=True).values_list('category_id', flat=True).distinct()
        ).order_by('name')
        return [(str(c.id), c.name) for c in categories]

    def queryset(self, request, queryset):
        if self.value():
            try:
                return queryset.filter(category_id=int(self.value()))
            except (ValueError, TypeError):
                return queryset
        return queryset


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
        'api_id', 'name', 'brand', 'category', 'symbol', 'price_gross',
        'store_total', 'is_mapped_mpd', 'last_update'
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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('mpd-create/<int:product_id>/', self.admin_site.admin_view(self.mpd_create), name='tabu-mpd-create'),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        try:
            product = TabuProduct.objects.select_related('brand').get(pk=object_id)
            is_mapped = bool(product.mapped_product_uid)

            # Pobierz dane MPD (kolory, ścieżki, atrybuty, marki, jednostki, rozmiary, fabric)
            with connections['MPD'].cursor() as cursor:
                cursor.execute("SELECT id, name FROM colors WHERE parent_id IS NULL ORDER BY name")
                main_colors = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

                cursor.execute("SELECT id, name, parent_id FROM colors WHERE parent_id IS NOT NULL ORDER BY name")
                producer_colors = [{'id': row[0], 'name': row[1], 'parent_id': row[2]} for row in cursor.fetchall()]

                cursor.execute("SELECT id, name, path FROM path ORDER BY name")
                mpd_paths = [{'id': row[0], 'name': row[1], 'path': row[2] or ''} for row in cursor.fetchall()]

                cursor.execute("SELECT id, name FROM attributes ORDER BY name")
                mpd_attributes = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

                cursor.execute("SELECT id, name FROM brands ORDER BY name")
                mpd_brands = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

                cursor.execute("SELECT unit_id, name FROM units ORDER BY name")
                units = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT category FROM sizes WHERE category IS NOT NULL ORDER BY category")
                size_categories = [row[0] for row in cursor.fetchall()]

                cursor.execute("SELECT id, name FROM fabric_component ORDER BY name")
                fabric_components = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

            selected_paths = []
            selected_attributes = []
            mpd_data = {}
            producer_color_name = ''
            producer_code = ''
            series_name = ''
            selected_unit_id = None

            if is_mapped:
                with connections['MPD'].cursor() as cursor:
                    cursor.execute(
                        "SELECT p.name, p.description, p.short_description, b.name FROM products p "
                        "LEFT JOIN brands b ON p.brand_id = b.id WHERE p.id = %s",
                        [product.mapped_product_uid]
                    )
                    r = cursor.fetchone()
                    if r:
                        mpd_data = {'name': r[0] or '', 'description': r[1] or '', 'short_description': r[2] or '', 'brand': r[3] or ''}

                    cursor.execute(
                        "SELECT c.name, pv.producer_code FROM product_variants pv "
                        "LEFT JOIN colors c ON pv.producer_color_id = c.id WHERE pv.product_id = %s LIMIT 1",
                        [product.mapped_product_uid]
                    )
                    r = cursor.fetchone()
                    if r:
                        producer_color_name = r[0] or ''
                        producer_code = r[1] or ''

                    cursor.execute(
                        "SELECT ps.name FROM products p LEFT JOIN product_series ps ON p.series_id = ps.id WHERE p.id = %s",
                        [product.mapped_product_uid]
                    )
                    r = cursor.fetchone()
                    if r:
                        series_name = r[0] or ''

                    cursor.execute("SELECT path_id FROM product_path WHERE product_id = %s", [product.mapped_product_uid])
                    selected_paths = [row[0] for row in cursor.fetchall()]

                    cursor.execute("SELECT attribute_id FROM product_attributes WHERE product_id = %s", [product.mapped_product_uid])
                    selected_attributes = [row[0] for row in cursor.fetchall()]

                    cursor.execute("SELECT unit FROM products WHERE id = %s", [product.mapped_product_uid])
                    r = cursor.fetchone()
                    if r and r[0] is not None:
                        selected_unit_id = r[0]

            extra_context.update({
                'is_mapped': is_mapped,
                'mpd_data': mpd_data,
                'main_colors': main_colors,
                'producer_colors': producer_colors,
                'mpd_paths': mpd_paths,
                'mpd_attributes': mpd_attributes,
                'mpd_brands': mpd_brands,
                'units': units,
                'size_categories': size_categories,
                'fabric_components': fabric_components,
                'selected_paths': selected_paths,
                'selected_attributes': selected_attributes,
                'producer_color_name': producer_color_name,
                'producer_code': producer_code,
                'series_name': series_name,
                'selected_unit_id': selected_unit_id,
            })
        except TabuProduct.DoesNotExist:
            extra_context['is_mapped'] = False
            extra_context['mpd_data'] = {}
            extra_context['main_colors'] = []
            extra_context['producer_colors'] = []
            extra_context['mpd_paths'] = []
            extra_context['mpd_attributes'] = []
            extra_context['mpd_brands'] = []
            extra_context['units'] = []
            extra_context['size_categories'] = []
            extra_context['fabric_components'] = []
            extra_context['selected_paths'] = []
            extra_context['selected_attributes'] = []
        except Exception as e:
            logger.exception("Błąd change_view Tabu: %s", e)
            extra_context['is_mapped'] = False
            extra_context['mpd_data'] = {}
            extra_context['main_colors'] = []
            extra_context['producer_colors'] = []
            extra_context['mpd_paths'] = []
            extra_context['mpd_attributes'] = []
            extra_context['mpd_brands'] = []
            extra_context['units'] = []
            extra_context['size_categories'] = []
            extra_context['fabric_components'] = []
            extra_context['selected_paths'] = []
            extra_context['selected_attributes'] = []

        return super().change_view(request, object_id, form_url, extra_context)

    @method_decorator(csrf_exempt)
    @method_decorator(require_http_methods(["POST"]))
    def mpd_create(self, request, product_id):
        """Tworzy nowy produkt w MPD na podstawie danych Tabu i formularza."""
        try:
            tabu_product = TabuProduct.objects.select_related('brand').get(pk=product_id)
        except TabuProduct.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Produkt Tabu nie istnieje'}, status=404)

        if tabu_product.mapped_product_uid:
            return JsonResponse({'success': False, 'error': 'Produkt jest już zmapowany do MPD'}, status=400)

        try:
            from decimal import Decimal
            from django.utils import timezone

            from MPD.models import (
                Products, Brands, ProductVariants, Colors, Sizes, Sources,
                ProductPaths, ProductAttribute, ProductFabric, ProductSeries,
                ProductvariantsSources, StockAndPrices, ProductImage
            )
            from matterhorn1.defs_db import upload_image_to_bucket_and_get_url

            # Dane z formularza (fallback na Tabu)
            name = request.POST.get('mpd_name') or tabu_product.name or 'Produkt z Tabu'
            short_desc = request.POST.get('mpd_short_description') or tabu_product.desc_short or ''
            description = request.POST.get('mpd_description') or tabu_product.desc_long or ''

            # Marka
            brand_id = None
            brand_name = request.POST.get('mpd_brand') or (tabu_product.brand.name if tabu_product.brand else '')
            if brand_name:
                brand_name = brand_name.strip()[:255]
                brand = Brands.objects.using('MPD').filter(name=brand_name).first()
                if not brand:
                    brand = Brands.objects.using('MPD').create(name=brand_name)
                brand_id = brand.id

            # Seria
            series_id = None
            series_name = request.POST.get('series_name', '').strip()
            if series_name:
                series, _ = ProductSeries.objects.using('MPD').get_or_create(
                    name=series_name[:255],
                    defaults={'name': series_name[:255]}
                )
                series_id = series.id

            # Jednostka (Products.unit FK używa unit_id z tabeli units)
            unit_id = None
            unit_val = request.POST.get('unit_id')
            if unit_val and unit_val.isdigit():
                unit_id = int(unit_val)

            # Utwórz produkt w MPD
            mpd_product = Products.objects.using('MPD').create(
                name=name[:255],
                description=description,
                short_description=short_desc[:500],
                brand_id=brand_id,
                series_id=series_id,
                unit_id=unit_id,
                visibility=False,
            )

            # Ścieżki
            for path_id in request.POST.getlist('mpd_paths'):
                if path_id.isdigit():
                    ProductPaths.objects.using('MPD').get_or_create(
                        product_id=mpd_product.id,
                        path_id=int(path_id),
                        defaults={'product_id': mpd_product.id, 'path_id': int(path_id)}
                    )

            # Atrybuty
            for attr_id in request.POST.getlist('mpd_attributes'):
                if attr_id.isdigit():
                    ProductAttribute.objects.using('MPD').get_or_create(
                        product=mpd_product,
                        attribute_id=int(attr_id),
                        defaults={'product': mpd_product, 'attribute_id': int(attr_id)}
                    )

            # Skład materiałowy
            fabric_ids = request.POST.getlist('fabric_component[]')
            fabric_pcts = request.POST.getlist('fabric_percentage[]')
            for comp_id, pct in zip(fabric_ids, fabric_pcts):
                if comp_id and pct and comp_id.isdigit() and pct.isdigit():
                    pct_val = int(pct)
                    if 0 < pct_val <= 100:
                        ProductFabric.objects.using('MPD').update_or_create(
                            product=mpd_product,
                            component_id=int(comp_id),
                            defaults={'percentage': pct_val}
                        )

            # Kolory z formularza (dla pierwszego wariantu)
            main_color_id = request.POST.get('main_color_id')
            producer_color_name = request.POST.get('producer_color_name', '').strip()
            producer_code = request.POST.get('producer_code', '') or ''

            main_color = None
            if main_color_id and main_color_id.isdigit():
                try:
                    main_color = Colors.objects.using('MPD').get(id=int(main_color_id))
                except Colors.DoesNotExist:
                    pass

            producer_color = None
            if producer_color_name:
                producer_color, _ = Colors.objects.using('MPD').get_or_create(
                    name=producer_color_name[:50],
                    defaults={'name': producer_color_name[:50]}
                )

            # Źródło Tabu dla ProductvariantsSources (source_id jest wymagane w DB)
            tabu_source, _ = Sources.objects.using('MPD').get_or_create(
                name='Tabu API',
                defaults={'type': 'api', 'location': 'https://b2b.tabu.com.pl'}
            )

            # Warianty z Tabu (rozmiar, EAN, stan, ceny hurtowe)
            variants = tabu_product.api_variants.all()
            for v in variants:
                color_obj = main_color if main_color else None
                if not color_obj and v.color:
                    color_obj, _ = Colors.objects.using('MPD').get_or_create(
                        name=v.color[:50],
                        defaults={'name': v.color[:50]}
                    )
                pc = producer_code or (v.symbol or '')[:255]
                if not pc and v.symbol:
                    pc = (v.symbol or '')[:255]

                # Rozmiar z Tabu -> MPD Sizes
                size_obj = None
                if v.size:
                    size_obj, _ = Sizes.objects.using('MPD').get_or_create(
                        name=v.size[:255],
                        defaults={'name': v.size[:255]}
                    )

                pv = ProductVariants.objects.using('MPD').create(
                    product=mpd_product,
                    color=color_obj,
                    producer_color=producer_color,
                    size=size_obj,
                    producer_code=pc,
                    iai_product_id=v.api_id,
                )

                # ProductvariantsSources (wymagane dla StockAndPrices - FK variant_id+source_id)
                pvs, _ = ProductvariantsSources.objects.using('MPD').get_or_create(
                    variant=pv,
                    source=tabu_source,
                    defaults={'ean': v.ean[:50] if v.ean else ''}
                )

                # Stan magazynowy + ceny hurtowe z Tabu (StockAndPrices)
                stock_val = v.store if v.store is not None else 0
                StockAndPrices.objects.using('MPD').get_or_create(
                    variant=pv,
                    source=tabu_source,
                    defaults={
                        'stock': stock_val,
                        'price': v.price_net or Decimal('0'),
                        'currency': 'PLN',
                        'last_updated': timezone.now(),
                    }
                )
                # Cena detaliczna = moja cena - użytkownik ustawia ręcznie w MPD

            # Jeśli brak wariantów - utwórz jeden domyślny
            if not variants:
                pv = ProductVariants.objects.using('MPD').create(
                    product=mpd_product,
                    color=main_color,
                    producer_color=producer_color,
                    producer_code=producer_code[:255] or (tabu_product.symbol[:255] if tabu_product.symbol else ''),
                    iai_product_id=tabu_product.api_id,
                )
                ProductvariantsSources.objects.using('MPD').get_or_create(
                    variant=pv,
                    source=tabu_source,
                    defaults={'ean': tabu_product.ean[:50] if tabu_product.ean else ''}
                )
                StockAndPrices.objects.using('MPD').get_or_create(
                    variant=pv,
                    source=tabu_source,
                    defaults={
                        'stock': tabu_product.store_total or 0,
                        'price': tabu_product.price_net or Decimal('0'),
                        'currency': 'PLN',
                        'last_updated': timezone.now(),
                    }
                )
                # Cena detaliczna = moja cena - użytkownik ustawia ręcznie w MPD

            # Zdjęcia z Tabu → MPD (upload do bucketa + ProductImage)
            images_to_upload = []
            if tabu_product.image_url and tabu_product.image_url.strip():
                images_to_upload.append((tabu_product.image_url.strip(), 1))
            seen_urls = {u for u, _ in images_to_upload}
            for img in tabu_product.gallery_images.order_by('order', 'api_image_id'):
                if img.image_url and img.image_url.strip() and img.image_url.strip() not in seen_urls:
                    images_to_upload.append((img.image_url.strip(), len(images_to_upload) + 1))
                    seen_urls.add(img.image_url.strip())
            for idx, (img_url, order_num) in enumerate(images_to_upload, 1):
                bucket_key = upload_image_to_bucket_and_get_url(
                    image_path=img_url,
                    product_id=mpd_product.id,
                    producer_color_name=producer_color_name or '',
                    image_number=order_num,
                )
                if bucket_key:
                    ProductImage.objects.using('MPD').get_or_create(
                        product=mpd_product,
                        file_path=bucket_key,
                        defaults={'product': mpd_product, 'file_path': bucket_key}
                    )

            # Zapisz mapowanie w Tabu
            tabu_product.mapped_product_uid = mpd_product.id
            tabu_product.save(update_fields=['mapped_product_uid'])

            logger.info("Utworzono produkt MPD %s z Tabu produktu %s", mpd_product.id, product_id)
            return JsonResponse({
                'success': True,
                'message': f'Utworzono produkt w MPD (ID: {mpd_product.id})',
                'mpd_product_id': mpd_product.id,
            })

        except Exception as e:
            logger.exception("Błąd tworzenia produktu MPD z Tabu: %s", e)
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def image_preview(self, obj):
        if obj and obj.image_url:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 200px; max-height: 200px;" /></a>',
                obj.image_url, obj.image_url
            )
        return '-'
    image_preview.short_description = 'Podgląd'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('brand', 'category')


@admin.register(TabuProductVariant)
class TabuProductVariantAdmin(admin.ModelAdmin):
    list_display = ['api_id', 'product', 'symbol', 'color', 'size', 'store', 'price_gross']
    list_filter = ['product__brand', 'product__category']
    search_fields = ['symbol', 'ean', 'product__name']
    readonly_fields = ['api_id']
    raw_id_fields = ['product']


@admin.register(ApiSyncLog)
class ApiSyncLogAdmin(admin.ModelAdmin):
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


@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'variant_symbol', 'old_stock', 'new_stock', 'stock_change', 'change_type', 'timestamp']
    list_filter = ['change_type', 'timestamp']
    search_fields = ['product_name', 'variant_symbol']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    list_per_page = 50
