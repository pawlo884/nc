from django.contrib import admin  # type: ignore
from django.utils.safestring import mark_safe
from django.utils.html import format_html, escape
from django.db.models import Exists, OuterRef
from django.contrib.admin import DateFieldListFilter, SimpleListFilter
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from .models import Brands, Collection, Products, Sizes, Sources, ProductVariants, ProductSet, ProductSetItem, StockAndPrices, StockHistory, Colors, ProductVariantsRetailPrice, ProductvariantsSources, Paths, ProductPaths, IaiProductCounter, FullChangeFile, Attributes, ProductAttribute, ProductImage, ProductSeries, Seasons, Categories, Vat, Units, FabricComponent, ProductFabric
from matterhorn1.defs_db import resolve_image_url
import decimal
# Register your models here.

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def admin_update_producer_code(request):
    """
    Endpoint do aktualizacji kodu producenta wariantu - dostępny w adminie
    """
    try:
        data = json.loads(request.body)
        variant_id = data.get('variant_id')
        producer_code = data.get('producer_code', '')

        if not variant_id:
            return JsonResponse({'status': 'error', 'message': 'Brak variant_id'}, status=400)

        # Znajdź wariant
        try:
            variant = ProductVariants.objects.using(
                'MPD').get(variant_id=variant_id)
        except ProductVariants.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Wariant nie istnieje'}, status=404)

        # Aktualizuj kod producenta w product_variants_sources (wszystkie źródła tego wariantu)
        updated = ProductvariantsSources.objects.using('MPD').filter(
            variant_id=variant_id
        ).update(producer_code=producer_code[:255] if producer_code else None)

        logger.info(
            f"Zaktualizowano kod producenta dla wariantu {variant_id} ({updated} źródeł): {producer_code}")

        return JsonResponse({
            'status': 'success',
            'message': 'Kod producenta został zaktualizowany',
            'variant_id': variant_id,
            'producer_code': producer_code
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format JSON'}, status=400)
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji kodu producenta: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Błąd serwera: {str(e)}'}, status=500)


# Dodaj URL do admina
original_get_urls = admin.site.get_urls
admin.site.get_urls = lambda: original_get_urls() + [
    path('mpd/update-producer-code/', admin_update_producer_code,
         name='admin_update_producer_code'),
]


# Usuwam ProductVariantsInline i wpis inlines = [ProductVariantsInline] z ProductsAdmin
# (pozostawiam tylko show_variants jako readonly_field)


class HasRetailPricesFilter(SimpleListFilter):
    title = 'ma ceny detaliczne'
    parameter_name = 'has_retail_prices'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Tak'),
            ('no', 'Nie'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(
                Exists(ProductVariants.objects.filter(
                    product=OuterRef('pk'),
                    productvariantsretailprice__isnull=False
                ))
            )
        elif self.value() == 'no':
            return queryset.filter(
                ~Exists(ProductVariants.objects.filter(
                    product=OuterRef('pk'),
                    productvariantsretailprice__isnull=False
                ))
            )


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_per_page = 30
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('name', 'short_description', 'description', 'brand', 'collection', 'series', 'season', 'unit', 'visibility')
        }),
        ('Warianty produktu', {
            'fields': ('show_variants',),
            'description': 'Przegląd wszystkich wariantów produktu z kolorami, rozmiarami i cenami'
        }),
        ('Atrybuty produktu', {
            'fields': ('show_attributes', 'edit_attributes'),
            'description': 'Zarządzanie atrybutami produktu - wyświetlanie i edycja'
        }),
        ('Skład materiałowy', {
            'fields': ('show_fabric_composition', 'edit_fabric_composition'),
            'description': 'Zarządzanie składem materiałowym produktu - komponenty i ich procenty'
        }),
        ('Zdjęcia produktu', {
            'fields': ('show_images',),
            'description': 'Zdjęcia produktu pogrupowane według kolorów'
        }),
        ('Powiązane produkty', {
            'fields': ('show_related_products',),
            'description': 'Zestawy i produkty z tej samej serii'
        }),
        ('Ceny detaliczne', {
            'fields': ('edit_retail_prices',),
            'description': 'Edycja cen detalicznych dla wszystkich wariantów'
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Informacje o dacie utworzenia i ostatniej aktualizacji'
        }),
    )
    list_display = ['id', 'name', 'description',
                    'brand', 'collection', 'season', 'updated_at', 'visibility']  # widok listy produktów
    list_filter = [
        'brand',
        'collection',
        'series',
        'season',
        'visibility',
        HasRetailPricesFilter,
        ('created_at', DateFieldListFilter),
        ('updated_at', DateFieldListFilter),
    ]
    search_fields = ['id', 'name', 'description',
                     'brand__name', 'series__name']
    readonly_fields = ['show_variants', 'show_attributes', 'edit_attributes', 'show_fabric_composition', 'edit_fabric_composition', 'show_images',
                       'show_related_products', 'edit_retail_prices', 'created_at', 'updated_at']
    change_form_template = 'admin/MPD/products/change_form.html'
    actions = ['make_visible', 'make_hidden']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD').select_related('brand', 'series', 'unit')

    def delete_model(self, request, obj):
        """Usuń pojedynczy produkt z użyciem bazy MPD"""
        obj.delete(using='MPD')

    def delete_queryset(self, request, queryset):
        """Usuń wiele produktów z użyciem bazy MPD"""
        for obj in queryset:
            obj.delete(using='MPD')

    @admin.action(description='Oznacz wybrane produkty jako widoczne')
    def make_visible(self, request, queryset):
        """Masowa akcja - oznacz produkty jako widoczne"""
        from django.utils import timezone
        updated = queryset.update(visibility=True, updated_at=timezone.now())
        self.message_user(
            request,
            f'{updated} produktów zostało oznaczonych jako widoczne.',
            level='SUCCESS'
        )

    @admin.action(description='Oznacz wybrane produkty jako niewidoczne')
    def make_hidden(self, request, queryset):
        """Masowa akcja - oznacz produkty jako niewidoczne"""
        from django.utils import timezone
        updated = queryset.update(visibility=False, updated_at=timezone.now())
        self.message_user(
            request,
            f'{updated} produktów zostało oznaczonych jako niewidoczne.',
            level='SUCCESS'
        )

    @admin.display(description="Edycja cen detalicznych")
    def edit_retail_prices(self, obj):
        variants = list(ProductVariants.objects.filter(product=obj)
                        .select_related('color', 'size'))
        if not variants:
            return "Brak wariantów produktu"
        variant_ids = [v.variant_id for v in variants]
        # Pobierz EANy i ceny detaliczne jednym zapytaniem
        sources_map = {s.variant.variant_id: s.ean for s in ProductvariantsSources.objects.filter(
            variant__variant_id__in=variant_ids).select_related('variant')}
        retail_map = {r.variant.variant_id: r.retail_price for r in ProductVariantsRetailPrice.objects.using(
            'MPD').filter(variant__variant_id__in=variant_ids).select_related('variant')}
        grouped = {}
        for variant in variants:
            color_name = variant.color.name if variant.color else "-"
            size_name = variant.size.name if variant.size else "-"
            variant_id = variant.variant_id
            ean = sources_map.get(variant_id, "-")
            retail_price = retail_map.get(variant_id, "")
            key = (color_name, size_name, ean)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(variant_id)
        html = "<form method='post'>"
        html += "<div style='margin-bottom:12px;'>"
        html += "<label>Ustaw cenę detaliczną dla wszystkich wariantów: </label>"
        html += "<input type='number' step='0.01' id='set_all_price' style='width:100px;'>"
        html += "<button type='button' onclick='setAllRetailPrices()' style='margin-left:8px;'>Ustaw dla wszystkich</button>"
        html += "</div>"
        html += "<table style='border-collapse:collapse; width:100%;'>"
        html += "<tr><th style='border:1px solid #ccc;padding:4px 8px;'>kolor</th><th style='border:1px solid #ccc;padding:4px 8px;'>rozmiar</th><th style='border:1px solid #ccc;padding:4px 8px;'>ean</th><th style='border:1px solid #ccc;padding:4px 8px;'>cena detaliczna</th><th style='border:1px solid #ccc;padding:4px 8px;'>VAT_id</th><th style='border:1px solid #ccc;padding:4px 8px;'>waluta</th></tr>"
        for (color_name, size_name, ean), variant_ids in grouped.items():
            retail_price = retail_map.get(variant_ids[0], "")
            html += "<tr>"
            html += f"<td style='border:1px solid #ccc;padding:4px 8px;'>{color_name}</td>"
            html += f"<td style='border:1px solid #ccc;padding:4px 8px;'>{size_name}</td>"
            html += f"<td style='border:1px solid #ccc;padding:4px 8px;'>{ean}</td>"
            html += f"<td style='border:1px solid #ccc;padding:4px 8px;'><input class='retail-price-input' type='number' step='0.01' name='retail_price_{variant_ids[0]}' value='{retail_price}' style='width:80px;'></td>"
            html += f"<td style='border:1px solid #ccc;padding:4px 8px;'><input type='text' name='vat_{variant_ids[0]}' value='' style='width:60px;'></td>"
            html += f"<td style='border:1px solid #ccc;padding:4px 8px;'><input type='text' name='currency_{variant_ids[0]}' value='' style='width:60px;'></td>"
            html += "</tr>"
        html += "</table>"
        html += "<br><input type='submit' name='save_retail_prices' value='Zapisz ceny detaliczne' style='background-color:#79aec8; color:white; padding:8px 16px; border:none; border-radius:4px; cursor:pointer;'>"
        html += "</form>"
        html += """
        <script>
        function setAllRetailPrices() {
            var value = document.getElementById('set_all_price').value;
            document.querySelectorAll('.retail-price-input').forEach(function(input) {
                input.value = value;
            });
        }
        </script>
        """
        return mark_safe(html)

    def save_model(self, request, obj, form, change):
        # Aktualizuj updated_at przed zapisaniem
        from django.utils import timezone
        obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)
        if 'save_retail_prices' in request.POST:
            variants = ProductVariants.objects.filter(product=obj)
            grouped = {}
            for variant in variants:
                color_name = variant.color.name if variant.color else "-"
                size_name = variant.size.name if variant.size else "-"
                variant_id = variant.variant_id
                variant_source = ProductvariantsSources.objects.filter(
                    variant__variant_id=variant_id).first()
                ean = variant_source.ean if variant_source and variant_source.ean else "-"
                key = (color_name, size_name, ean)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(variant_id)
            for key, variant_ids in grouped.items():
                field_name = f'retail_price_{variant_ids[0]}'
                vat_field = f'vat_{variant_ids[0]}'
                currency_field = f'currency_{variant_ids[0]}'
                if field_name in request.POST:
                    value = request.POST[field_name]
                    vat_value = request.POST.get(vat_field, '').strip()
                    currency_value = request.POST.get(
                        currency_field, '').strip()
                    try:
                        retail_price = decimal.Decimal(
                            value) if value.strip() else None
                        vat = decimal.Decimal(
                            vat_value) if vat_value else decimal.Decimal('1')
                        currency = currency_value if currency_value else 'PLN'
                        for variant_id in variant_ids:
                            # Sprawdź czy wariant istnieje w tabeli product_variants
                            variant_exists = ProductVariants.objects.using(
                                'MPD').filter(variant_id=variant_id).exists()
                            if not variant_exists:
                                continue
                            obj_rp = ProductVariantsRetailPrice.objects.using(
                                'MPD').filter(variant__variant_id=variant_id).first()
                            if obj_rp is None:
                                # Musimy znaleźć obiekt ProductVariants z tym variant_id
                                variant_obj = ProductVariants.objects.using(
                                    'MPD').filter(variant_id=variant_id).first()
                                if not variant_obj:
                                    continue
                                obj_rp = ProductVariantsRetailPrice(
                                    variant=variant_obj)
                            obj_rp.retail_price = retail_price
                            obj_rp.vat = vat
                            obj_rp.currency = currency
                            obj_rp.updated_at = timezone.now()
                            obj_rp.save(using='MPD')
                    except (ValueError, TypeError, decimal.InvalidOperation):
                        continue
            from django.contrib import messages
            messages.success(
                request, 'Ceny detaliczne zostały zapisane pomyślnie!')
            request.session['retail_prices_saved'] = True

    def response_change(self, request, obj):
        # Sprawdź czy ceny detaliczne zostały zapisane
        if request.session.get('retail_prices_saved'):
            del request.session['retail_prices_saved']
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            return HttpResponseRedirect(reverse('admin:MPD_products_change', args=[obj.pk]))
        return super().response_change(request, obj)

    @admin.display(description="Atrybuty produktu")
    def show_attributes(self, obj):
        """Wyświetla obecnie przypisane atrybuty produktu"""
        if not obj.id:
            return "Zapisz produkt aby móc zarządzać atrybutami"

        # Pobierz atrybuty przypisane do produktu
        product_attributes = ProductAttribute.objects.using('MPD').filter(
            product=obj
        ).select_related('attribute')

        if not product_attributes:
            return "Brak przypisanych atrybutów"

        html = "<table style='border-collapse:collapse; width:100%;'>"
        html += "<tr><th style='border:1px solid #ccc;padding:4px 8px;'>ID</th><th style='border:1px solid #ccc;padding:4px 8px;'>Nazwa atrybutu</th></tr>"

        for pa in product_attributes:
            html += "<tr>"
            html += f"<td style='border:1px solid #ccc;padding:4px 8px;'>{pa.attribute.id}</td>"
            html += f"<td style='border:1px solid #ccc;padding:4px 8px;'>{pa.attribute.name}</td>"
            html += "</tr>"

        html += "</table>"
        return mark_safe(html)

    @admin.display(description="Edycja atrybutów")
    def edit_attributes(self, obj):
        """Formularz do zarządzania atrybutami produktu"""
        if not obj.id:
            return "Zapisz produkt aby móc zarządzać atrybutami"

        # Pobierz wszystkie dostępne atrybuty
        all_attributes = Attributes.objects.using('MPD').all().order_by('name')

        # Pobierz atrybuty przypisane do produktu
        assigned_attributes = set(ProductAttribute.objects.using('MPD').filter(
            product=obj
        ).values_list('attribute_id', flat=True))

        print(
            f"DEBUG: Przypisane atrybuty dla produktu {obj.id}: {assigned_attributes}")

        html = "<div style='margin-bottom:12px;'>"
        html += "<label>Dodaj nowe atrybuty:</label><br>"
        html += "<select id='new_attribute_select' style='width:300px; margin-right:8px;'>"
        html += "<option value=''>Wybierz atrybut...</option>"

        for attr in all_attributes:
            if attr.id not in assigned_attributes:
                html += f"<option value='{attr.id}'>{attr.name}</option>"

        html += "</select>"
        html += "<button type='button' onclick='addAttribute()' style='background-color:#79aec8; color:white; padding:4px 8px; border:none; border-radius:4px; cursor:pointer;'>Dodaj</button>"
        html += "</div>"

        html += "<div id='attributes_list'>"
        html += "<h4>Przypisane atrybuty:</h4>"

        if assigned_attributes:
            html += "<table style='border-collapse:collapse; width:100%;'>"
            html += "<tr><th style='border:1px solid #ccc;padding:4px 8px;'>Nazwa</th><th style='border:1px solid #ccc;padding:4px 8px;'>Akcje</th></tr>"

            # Pobierz atrybuty bezpośrednio z relacji
            product_attributes = ProductAttribute.objects.using('MPD').filter(
                product=obj
            ).select_related('attribute')

            for pa in product_attributes:
                html += "<tr>"
                html += f"<td style='border:1px solid #ccc;padding:4px 8px;'>{pa.attribute.name}</td>"
                html += "<td style='border:1px solid #ccc;padding:4px 8px;'>"
                html += f"<button type='button' onclick='removeAttributeShow({pa.attribute.id}, {obj.id})' style='background-color:#dc3545; color:white; padding:2px 6px; border:none; border-radius:3px; cursor:pointer;'>Usuń</button>"
                html += "</td>"
                html += "</tr>"

            html += "</table>"
        else:
            html += "<p>Brak przypisanych atrybutów</p>"

        html += "</div>"

        html += f"""
        <script>
        function addAttribute() {{
            var select = document.getElementById('new_attribute_select');
            var attributeId = select.value;
            var attributeName = select.options[select.selectedIndex].text;
            
            if (!attributeId) {{
                alert('Wybierz atrybut do dodania');
                return;
            }}
            
            console.log('Dodawanie atrybutu:', attributeId);
            
            // Wyślij AJAX request
            fetch('/mpd/manage-product-attributes/', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || document.querySelector('meta[name=csrf-token]')?.content || ''
                }},
                body: JSON.stringify({{
                    product_id: {obj.id},
                    action: 'add',
                    attribute_ids: [parseInt(attributeId)]
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.status === 'success') {{
                    location.reload();
                }} else {{
                    alert('Błąd: ' + (data.message || 'Nie udało się dodać atrybutu'));
                }}
            }})
            .catch(error => {{
                console.error('Error:', error);
                alert('Błąd połączenia');
            }});
        }}
        
        function removeAttributeShow(attributeId, productId) {{
            fetch('/mpd/manage-product-attributes/', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                }},
                body: JSON.stringify({{
                    product_id: productId,
                    action: 'remove',
                    attribute_id: attributeId
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.status === 'success') {{
                    location.reload();
                }} else {{
                    alert('Błąd: ' + (data.message || 'Nie udało się usunąć atrybutu'));
                }}
            }})
            .catch(error => {{
                alert('Błąd połączenia: ' + error.message);
            }});
        }}
        </script>
        """

        return mark_safe(html)

    @admin.display(description="Skład materiałowy")
    def show_fabric_composition(self, obj):
        """Wyświetla obecny skład materiałowy produktu"""
        if not obj.id:
            return "Zapisz produkt aby móc zarządzać składem materiałowym"

        # Pobierz skład materiałowy produktu
        fabric_composition = ProductFabric.objects.using('MPD').filter(
            product=obj
        ).select_related('component')

        if not fabric_composition:
            return "Brak informacji o składzie materiałowym"

        html = "<table style='border-collapse:collapse; width:100%;'>"
        html += "<tr><th style='border:1px solid #ccc;padding:4px 8px;'>Komponent</th><th style='border:1px solid #ccc;padding:4px 8px;'>Procent</th></tr>"

        total_percentage = 0
        for fabric in fabric_composition:
            html += "<tr>"
            html += f"<td style='border:1px solid #ccc;padding:4px 8px;'>{fabric.component.name}</td>"
            html += f"<td style='border:1px solid #ccc;padding:4px 8px;'>{fabric.percentage}%</td>"
            html += "</tr>"
            total_percentage += fabric.percentage

        html += "</table>"

        # Dodaj informację o sumie procentów
        if total_percentage != 100:
            color = "#dc3545" if total_percentage > 100 else "#ffc107"
            html += f"<p style='color:{color}; font-weight:bold; margin-top:8px;'>Suma: {total_percentage}% {'(przekroczono 100%)' if total_percentage > 100 else '(niepełny skład)' if total_percentage < 100 else ''}</p>"
        else:
            html += "<p style='color:#28a745; font-weight:bold; margin-top:8px;'>Suma: 100% (pełny skład)</p>"

        return mark_safe(html)

    @admin.display(description="Edycja składu materiałowego")
    def edit_fabric_composition(self, obj):
        """Formularz do zarządzania składem materiałowym produktu"""
        if not obj.id:
            return "Zapisz produkt aby móc zarządzać składem materiałowym"

        # Pobierz wszystkie dostępne komponenty
        all_components = FabricComponent.objects.using(
            'MPD').all().order_by('name')

        # Pobierz obecny skład produktu
        current_fabric = ProductFabric.objects.using('MPD').filter(
            product=obj
        ).select_related('component')

        current_components = {
            pf.component.id: pf.percentage for pf in current_fabric}

        html = "<div style='margin-bottom:12px;'>"
        html += "<label>Dodaj nowy komponent:</label><br>"
        html += "<select id='new_component_select' style='width:200px; margin-right:8px;'>"
        html += "<option value=''>Wybierz komponent...</option>"

        for component in all_components:
            if component.id not in current_components:
                html += f"<option value='{component.id}'>{component.name}</option>"

        html += "</select>"
        html += "<input type='number' id='new_component_percentage' placeholder='Procent' min='1' max='100' style='width:80px; margin-right:8px;'>"
        html += "<button type='button' onclick='addFabricComponent()' style='background-color:#79aec8; color:white; padding:4px 8px; border:none; border-radius:4px; cursor:pointer;'>Dodaj</button>"
        html += "</div>"

        html += "<div id='fabric_composition_list'>"
        html += "<h4>Obecny skład materiałowy:</h4>"

        if current_fabric:
            html += "<table style='border-collapse:collapse; width:100%;'>"
            html += "<tr><th style='border:1px solid #ccc;padding:4px 8px;'>Komponent</th><th style='border:1px solid #ccc;padding:4px 8px;'>Procent</th><th style='border:1px solid #ccc;padding:4px 8px;'>Akcje</th></tr>"

            total_percentage = 0
            for fabric in current_fabric:
                html += "<tr>"
                html += f"<td style='border:1px solid #ccc;padding:4px 8px;'>{fabric.component.name}</td>"
                html += f"<td style='border:1px solid #ccc;padding:4px 8px;'>{fabric.percentage}%</td>"
                html += "<td style='border:1px solid #ccc;padding:4px 8px;'>"
                html += f"<button type='button' onclick='removeFabricComponent({fabric.component.id})' style='background-color:#dc3545; color:white; padding:2px 6px; border:none; border-radius:3px; cursor:pointer;'>Usuń</button>"
                html += "</td>"
                html += "</tr>"
                total_percentage += fabric.percentage

            html += "</table>"

            # Dodaj informację o sumie procentów
            if total_percentage != 100:
                color = "#dc3545" if total_percentage > 100 else "#ffc107"
                html += f"<p style='color:{color}; font-weight:bold; margin-top:8px;'>Suma: {total_percentage}% {'(przekroczono 100%)' if total_percentage > 100 else '(niepełny skład)' if total_percentage < 100 else ''}</p>"
            else:
                html += "<p style='color:#28a745; font-weight:bold; margin-top:8px;'>Suma: 100% (pełny skład)</p>"
        else:
            html += "<p>Brak informacji o składzie materiałowym</p>"

        html += "</div>"

        html += """
        <script>
        function addFabricComponent() {
            var select = document.getElementById('new_component_select');
            var percentageInput = document.getElementById('new_component_percentage');
            var componentId = select.value;
            var percentage = percentageInput.value;
            
            if (!componentId) {
                alert('Wybierz komponent');
                return;
            }
            
            if (!percentage || percentage < 1 || percentage > 100) {
                alert('Wprowadź prawidłowy procent (1-100)');
                return;
            }
            
            // Wyślij AJAX request
            fetch('/mpd/manage-product-fabric/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || document.querySelector('meta[name=csrf-token]')?.content || ''
                },
                body: JSON.stringify({
                    product_id: """ + str(obj.id) + """,
                    action: 'add',
                    component_id: parseInt(componentId),
                    percentage: parseInt(percentage)
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Odśwież stronę aby pokazać nowy komponent
                    location.reload();
                } else {
                    alert('Błąd: ' + (data.message || 'Nie udało się dodać komponentu'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Błąd połączenia');
            });
        }
        
        function removeFabricComponent(componentId) {
            if (!confirm('Czy na pewno chcesz usunąć ten komponent ze składu?')) {
                return;
            }
            
            // Wyślij AJAX request
            fetch('/mpd/manage-product-fabric/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || document.querySelector('meta[name=csrf-token]')?.content || ''
                },
                body: JSON.stringify({
                    product_id: """ + str(obj.id) + """,
                    action: 'remove',
                    component_id: componentId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Odśwież stronę aby usunąć komponent
                    location.reload();
                } else {
                    alert('Błąd: ' + (data.message || 'Nie udało się usunąć komponentu'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Błąd połączenia');
            });
        }
        </script>
        """

        return mark_safe(html)

    @admin.display(description="Warianty produktu")
    def show_variants(self, obj):
        # Zoptymalizowane zapytanie z select_related i prefetch_related
        variants = list(ProductVariants.objects.filter(product=obj)
                        .select_related('color', 'producer_color', 'size')
                        .prefetch_related('productvariantssources_set__source'))

        if not variants:
            return "Brak wariantów"

        variant_ids = [v.variant_id for v in variants]

        # Pobierz źródła, EANy i ceny detaliczne dla wszystkich wariantów jednym zapytaniem
        sources_qs = ProductvariantsSources.objects.filter(
            variant__variant_id__in=variant_ids).select_related('source')
        sources_map = {}
        for s in sources_qs:
            sources_map.setdefault(s.variant.variant_id, []).append(s)

        retail_map = {r.variant.variant_id: r.retail_price for r in ProductVariantsRetailPrice.objects.using(
            'MPD').filter(variant__variant_id__in=variant_ids)}

        # Pobierz stock_and_prices dla wszystkich variant_id i source_id
        from django.db import connections
        with connections['MPD'].cursor() as cursor:
            cursor.execute("""
                SELECT variant_id, source_id, stock, price, currency FROM stock_and_prices WHERE variant_id IN %s
            """, [tuple(variant_ids)])
            stock_rows = cursor.fetchall()
        stock_map = {}
        for variant_id, source_id, stock, price, currency in stock_rows:
            stock_map[(variant_id, source_id)] = (stock, price, currency)
        grouped = {}
        for v in variants:
            color = v.color.name if v.color else "-"
            producer_color = v.producer_color.name if v.producer_color else "-"
            size = v.size.name if v.size else "-"
            sources = sources_map.get(v.variant_id, [])
            sources_names = []
            eans = []
            for s in sources:
                stock = None
                if s.source:
                    stock_info = stock_map.get((v.variant_id, s.source.id))
                    stock = stock_info[0] if stock_info else None
                stock_str = f": {stock}" if stock is not None else ""
                sources_names.append(
                    f"{s.source.name if s.source else '-'}{stock_str}")
                eans.append(s.ean or '-')
            sources_display = "<br>".join(
                sources_names) if sources_names else "-"
            eans_display = "<br>".join(eans) if eans else "-"
            # Grupowanie po EAN – ten sam EAN = ten sam produkt (bez sources_display)
            canonical_ean = "|".join(
                sorted(set(e for e in eans if e and e != '-'))) or "-"
            key = (color, producer_color, size, canonical_ean)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append((v.variant_id, sources_display, eans_display))
        cell_style = "border:1px solid #ccc;padding:2px 6px;vertical-align:middle;"
        html = "<table style='border-collapse:collapse;'>"
        html += f"<tr><th style='{cell_style}'>Kolor</th><th style='{cell_style}'>Kolor producenta</th><th style='{cell_style}'>Rozmiar</th><th style='{cell_style}'>Kod producenta</th><th style='{cell_style}'>Stan (suma)</th><th style='{cell_style}'>Ceny</th><th style='{cell_style}'>Cena detaliczna</th><th style='{cell_style}'>Źródła</th><th style='{cell_style}'>EAN</th></tr>"
        for (color, producer_color, size, canonical_ean), group_items in grouped.items():
            variant_ids = [item[0] for item in group_items]
            sources_display = "<br>".join(
                item[1] for item in group_items if item[1] and item[1] != "-"
            ) or "-"
            # EAN: jedna wartość (wspólna dla wiersza), z klucza grupy
            eans_display = canonical_ean if canonical_ean != "-" else "-"
            # Zsumuj stock i pobierz ceny dla wszystkich variant_id
            total_stock = 0
            prices = []
            for variant_id in variant_ids:
                for s in sources_map.get(variant_id, []):
                    stock_info = stock_map.get(
                        (variant_id, s.source.id)) if s.source else None
                    if stock_info:
                        total_stock += stock_info[0] or 0
                        if stock_info[1] is not None and stock_info[1] > 0:
                            prices.append(
                                f"{s.source.name}: {stock_info[1]} {stock_info[2]}")
            prices_str = "<br>".join(prices) if prices else "-"
            retail_price_str = f"{retail_map.get(variant_ids[0], '-')} PLN" if retail_map.get(
                variant_ids[0]) is not None else "-"
            # Kod producenta wyłącznie z product_variants_sources.producer_code (bez other/mpn/variant_uid)
            producer_codes_lines = []
            for variant_id in variant_ids:
                for s in sources_map.get(variant_id, []):
                    code = (getattr(s, 'producer_code', None)
                            or '').strip() or None
                    if code:
                        producer_codes_lines.append(
                            f"{escape(s.source.name if s.source else '-')}: {escape(code)}"
                        )
            producer_code_cell = "<br>".join(
                producer_codes_lines) if producer_codes_lines else "-"

            html += f"<tr><td style='{cell_style}'>{color}</td><td style='{cell_style}'>{producer_color}</td><td style='{cell_style}'>{size}</td><td style='{cell_style}'>{producer_code_cell}</td><td style='{cell_style}'>{total_stock}</td><td style='{cell_style}'>{prices_str}</td><td style='{cell_style}'>{retail_price_str}</td><td style='{cell_style}'>{sources_display}</td><td style='{cell_style}'>{eans_display}</td></tr>"
        html += "</table>"

        return mark_safe(html)

    @admin.display(description="Zdjęcia produktu")
    def show_images(self, obj):
        print(f"\n=== DEBUG: show_images dla produktu {obj.id} ===")

        # Grupowanie zdjęć po nazwie koloru producenta lub zwykłego koloru (nie używamy variant_id)
        # Zoptymalizowane zapytanie z prefetch_related
        images = obj.images.all() if hasattr(obj, 'images') else []
        # Pobierz wszystkie unikalne kolory producenta i zwykłe kolory z wariantów produktu
        # Zoptymalizowane zapytania z select_related
        producer_colors = (
            ProductVariants.objects.filter(
                product=obj, producer_color__isnull=False)
            .select_related('producer_color')
            .values_list('producer_color__id', 'producer_color__name')
            .distinct()
        )
        normal_colors = (
            ProductVariants.objects.filter(product=obj, color__isnull=False)
            .select_related('color')
            .values_list('color__id', 'color__name')
            .distinct()
        )
        color_name_map = {str(cid): cname for cid,
                          cname in producer_colors if cname}
        color_name_map_lower = {cname.lower().replace(
            '/', '_').replace(' ', '_'): cid for cid, cname in producer_colors if cname}
        normal_color_name_map = {
            str(cid): cname for cid, cname in normal_colors if cname}
        normal_color_name_map_lower = {cname.lower().replace(
            '/', '_').replace(' ', '_'): cid for cid, cname in normal_colors if cname}
        print(f"DEBUG: Dostępne kolory producenta: {color_name_map}")
        print(f"DEBUG: Dostępne zwykłe kolory: {normal_color_name_map}")
        # Sortuj nazwy kolorów od najdłuższych do najkrótszych, aby najpierw dopasować np. 'light pink' przed 'pink'
        color_name_map_lower_sorted = sorted(
            color_name_map_lower.items(), key=lambda x: -len(x[0]))
        normal_color_name_map_lower_sorted = sorted(
            normal_color_name_map_lower.items(), key=lambda x: -len(x[0]))
        images_by_color = {cid: [] for cid in color_name_map}
        images_by_normal_color = {cid: [] for cid in normal_color_name_map}
        images_no_color = []
        for img in images:
            file_name = img.file_path.split('/')[-1].lower()
            matched = False
            # Najpierw próbuj dopasować do koloru producenta (od najdłuższych nazw)
            for cname, cid in color_name_map_lower_sorted:
                if cname in file_name:
                    images_by_color[str(cid)].append(img)
                    matched = True
                    break
            # Jeśli nie znaleziono, próbuj dopasować do zwykłego koloru (od najdłuższych nazw)
            if not matched:
                for cname, cid in normal_color_name_map_lower_sorted:
                    if cname in file_name:
                        images_by_normal_color[str(cid)].append(img)
                        matched = True
                        break
            if not matched:
                images_no_color.append(img)
        print(
            f"DEBUG: Zdjęcia pogrupowane po producer_color_id (nazwa pliku): {{cid: len(imgs) for cid, imgs in images_by_color.items()}}, po color_id: {{cid: len(imgs) for cid, imgs in images_by_normal_color.items()}}, zdjęcia bez koloru: {len(images_no_color)}")
        html = ""
        # Wyświetl zdjęcia z przypisanym kolorem producenta
        for cid, imgs in images_by_color.items():
            color_name = color_name_map.get(cid, f"ID {cid}")
            if imgs:
                html += f'<div style="margin-bottom: 12px;"><b>{color_name}</b><br>'
                for img in imgs:
                    url = resolve_image_url(img.file_path) or img.file_path
                    # Upewnij się, że URL jest bezwzględny (zaczyna się od http:// lub https://)
                    if url and not url.startswith(('http://', 'https://')):
                        # Jeśli to surowa ścieżka, nie używaj jej jako linku
                        logger.warning(
                            f"Nieprawidłowy URL obrazu dla produktu {obj.id}: {url}")
                        url = "#"
                    html += f'<a href="{url}" target="_blank" rel="noopener noreferrer"><img src="{url}" style="max-height:60px; margin:2px; border:1px solid #ccc;" /></a>'
                html += '</div>'
        # Wyświetl zdjęcia z przypisanym zwykłym kolorem
        for cid, imgs in images_by_normal_color.items():
            color_name = normal_color_name_map.get(cid, f"ID {cid}")
            if imgs:
                html += f'<div style="margin-bottom: 12px;"><b>{color_name}</b><br>'
                for img in imgs:
                    url = resolve_image_url(img.file_path) or img.file_path
                    # Upewnij się, że URL jest bezwzględny (zaczyna się od http:// lub https://)
                    if url and not url.startswith(('http://', 'https://')):
                        # Jeśli to surowa ścieżka, nie używaj jej jako linku
                        logger.warning(
                            f"Nieprawidłowy URL obrazu dla produktu {obj.id}: {url}")
                        url = "#"
                    html += f'<a href="{url}" target="_blank" rel="noopener noreferrer"><img src="{url}" style="max-height:60px; margin:2px; border:1px solid #ccc;" /></a>'
                html += '</div>'
        # Wyświetl zdjęcia bez przypisanego koloru
        if images_no_color:
            html += '<div style="margin-bottom: 12px;"><b>Inne zdjęcia</b><br>'
            for img in images_no_color:
                url = resolve_image_url(img.file_path) or img.file_path
                # Upewnij się, że URL jest bezwzględny (zaczyna się od http:// lub https://)
                if url and not url.startswith(('http://', 'https://')):
                    # Jeśli to surowa ścieżka, nie używaj jej jako linku
                    logger.warning(
                        f"Nieprawidłowy URL obrazu dla produktu {obj.id}: {url}")
                    url = "#"
                html += f'<a href="{url}" target="_blank" rel="noopener noreferrer"><img src="{url}" style="max-height:60px; margin:2px; border:1px solid #ccc;" /></a>'
            html += '</div>'
        if not html:
            return "Brak zdjęć produktu"
        return format_html(html)

    @admin.display(description="Powiązane produkty")
    def show_related_products(self, obj):
        html = ""
        # Zestawy, do których należy ten produkt
        # Zoptymalizowane zapytanie
        set_items = list(ProductSetItem.objects.filter(product_id=obj.id))
        set_ids = [si.product_set_id for si in set_items]
        if set_items:
            html += "<b>Zestawy, do których należy ten produkt:</b>"
            for set_id in set_ids:
                try:
                    set_obj = ProductSet.objects.select_related(
                        'mapped_product').get(id=set_id)
                    set_products = ProductSetItem.objects.filter(
                        product_set_id=set_id).exclude(product_id=obj.id)
                    html += f"<div style='margin-bottom:8px;'><span style='font-weight:600;'>Zestaw: {set_obj.name} (ID: {set_obj.id})</span></div>"
                    html += "<div style='display:flex; flex-direction:row; flex-wrap:wrap; gap:24px; align-items:flex-start; margin-bottom:16px; width:100%;'>"
                    for sp in set_products:
                        try:
                            prod = Products.objects.select_related(
                                'brand').prefetch_related('images').get(id=sp.product_id)
                            admin_url = f"/admin/MPD/products/{prod.id}/change/"
                            img_html = ""
                            images_rel = getattr(prod, 'images', None)
                            first_img = images_rel.first() if images_rel and hasattr(
                                images_rel, 'first') else None
                            if first_img:
                                img_url = resolve_image_url(
                                    first_img.file_path) or first_img.file_path
                                img_html = f'<a href="{admin_url}"><img src="{img_url}" style="max-height:40px; max-width:40px; margin-right:5px; border:1px solid #ccc; vertical-align:middle;" /></a>'
                            name_html = f'<a href="{admin_url}" style="vertical-align:middle;">{prod.name}</a>'
                            html += f"<div style='display:flex; align-items:center; gap:8px;'>{img_html}{name_html}</div>"
                        except Exception as e:
                            html += f"<div>Błąd pobierania produktu {sp.product_id}: {e}</div>"
                    html += "</div>"
                except Exception as e:
                    html += f"<div>Błąd pobierania zestawu {set_id}: {e}</div>"
        # Produkty z tej samej serii
        series = getattr(obj, 'series', None)
        series_products = []
        series_name = ""
        if series:
            series_name = series.name
            series_products = list(Products.objects.filter(
                series=series).exclude(id=obj.id))
        if series and series_products:
            html += f"<b>Produkty z tej samej serii ({series_name}):</b>"
            html += "<div style='display:flex; flex-direction:row; gap:24px; align-items:flex-start; margin-bottom:8px;'>"
            # Zoptymalizowane zapytanie dla produktów z serii
            series_products_optimized = Products.objects.filter(
                series=series).exclude(id=obj.id).select_related('brand').prefetch_related('images')
            for p in series_products_optimized:
                admin_url = f"/admin/MPD/products/{p.id}/change/"
                img_html = ""
                images_rel = getattr(p, 'images', None)
                first_img = images_rel.first() if images_rel and hasattr(
                    images_rel, 'first') else None
                if first_img:
                    img_url = resolve_image_url(
                        first_img.file_path) or first_img.file_path
                    img_html = f'<a href=\"{admin_url}\"><img src=\"{img_url}\" style=\"max-height:40px; max-width:40px; margin-right:5px; border:1px solid #ccc; vertical-align:middle;\" /></a>'
                name_html = f'<a href=\"{admin_url}\" style=\"vertical-align:middle;\">{p.name}</a>'
                html += f"<div style='display:flex; align-items:center; gap:8px;'>{img_html}{name_html}</div>"
            html += "</div>"
        if not html:
            html = "Brak powiązanych produktów"
        return mark_safe(html)

    def get_tree(self, product_id=None):
        """Generuje drzewo ścieżek w formacie HTML z wyróżnieniem przypisanych do produktu"""
        paths = list(Paths.objects.using('MPD').all())

        # Pobierz ścieżki przypisane do produktu
        assigned_path_ids = set()
        if product_id:
            product_paths = ProductPaths.objects.using(
                'MPD').filter(product_id=product_id)
            assigned_path_ids = set(pp.path_id for pp in product_paths)
        tree = {}
        by_id = {p.id: p for p in paths}
        for p in paths:
            parent = p.parent_id
            if parent and parent in by_id:
                tree.setdefault(parent, []).append(p)
            else:
                tree.setdefault(None, []).append(p)

        def build_html(parent=None):
            html = ''
            children = tree.get(parent, [])
            if children:
                html += '<ul style="list-style:none; margin:0; padding-left:18px">'
                for p in children:
                    has_children = p.id in tree
                    node_id = f'path-node-{p.id}'
                    is_assigned = p.id in assigned_path_ids

                    # Style dla przypisanych ścieżek
                    style = 'background-color: #d4edda; border: 1px solid #c3e6cb; padding: 2px 5px; border-radius: 3px; margin: 1px 0;' if is_assigned else ''
                    checked_attr = 'checked' if is_assigned else ''

                    # Checkbox do zarządzania przypisaniem
                    checkbox_html = f'<input type="checkbox" class="path-checkbox" data-path-id="{p.id}" {checked_attr} style="margin-right: 8px;">'

                    html += f'<li id="{node_id}" style="{style}">' \
                        + (f'<span class="toggle-btn" data-target="{node_id}-children" style="cursor:pointer; font-weight:bold;">[-]</span> ' if has_children else '') \
                        + checkbox_html \
                        + f'{p.name or "(brak nazwy)"} [{p.path or "-"}] [id={p.id}]'
                    if has_children:
                        html += f'<div id="{node_id}-children">' + \
                            build_html(p.id) + '</div>'
                    html += '</li>'
                html += '</ul>'
            return html
        return build_html()

    def render_change_form(self, request, context, *args, **kwargs):
        """Dodaje drzewo ścieżek do kontekstu formularza edycji produktu"""
        obj = kwargs.get('obj')
        product_id = obj.id if obj else None
        context['paths_tree'] = self.get_tree(product_id)
        return super().render_change_form(request, context, *args, **kwargs)


@admin.register(Brands)
class BrandsAdmin(admin.ModelAdmin):
    fields = ['name', 'logo_url', 'opis', 'url', 'iai_brand_id']
    list_display = ['id', 'name', 'url', 'iai_brand_id']
    search_fields = ['name']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


@admin.register(Sizes)
class SizesAdmin(admin.ModelAdmin):
    fields = ['name', 'category', 'unit', 'name_lower']
    list_display = ['id', 'name', 'category',
                    'unit', 'name_lower', 'iai_size_id']
    list_filter = ['name', 'category', 'unit', 'name_lower']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


@admin.register(Sources)
class SourceAdmin(admin.ModelAdmin):
    fields = ['name', 'location', 'type', 'long_name', 'short_name', 'showcase_image',
              'email', 'tel', 'fax', 'www', 'street', 'zipcode', 'city', 'country', 'province']
    list_display = ['id', 'name', 'location', 'type']
    search_fields = ['name']
    actions = ['link_products_from_source']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')

    @admin.action(description='Linkuj produkty z tej hurtowni (po EAN)')
    def link_products_from_source(self, request, queryset):
        from .tasks import link_all_products_to_new_source_task
        from .source_adapters.registry import get_adapter_for_source
        queued = 0
        for source in queryset:
            if get_adapter_for_source(source.id):
                link_all_products_to_new_source_task.delay(source.id)
                queued += 1
        self.message_user(
            request,
            f'Wysłano {queued} zadań do kolejki (dopinanie wariantów po EAN).'
        )


@admin.register(ProductSet)
class ProductSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'mapped_product', 'created_at', 'updated_at')
    search_fields = ('name', 'mapped_product__name')
    list_filter = ('created_at', 'updated_at')
    raw_id_fields = ('mapped_product',)
    show_full_result_count = False
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('mapped_product')


@admin.register(ProductSetItem)
class ProductSetItemAdmin(admin.ModelAdmin):
    list_display = ('quantity', 'created_at')
    list_filter = ('created_at',)


@admin.register(StockAndPrices)
class StockAndPricesAdmin(admin.ModelAdmin):
    list_display = ('id', 'variant_id', 'source_id', 'stock',
                    'price', 'currency', 'last_updated')
    search_fields = ('id', 'variant_id', 'source_id')
    list_filter = ('last_updated',)
    readonly_fields = ('id', 'variant_id', 'source_id',
                       'stock', 'price', 'currency', 'last_updated')


@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'stock_id', 'source_id',
                    'previous_stock', 'new_stock', 'change_date')
    list_filter = ('change_date',)
    search_fields = ('stock_id',)
    readonly_fields = ('id', 'stock_id', 'source_id',
                       'previous_stock', 'new_stock', 'change_date')


@admin.register(Colors)
class ColorsAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'hex_code', 'parent_id']
    search_fields = ['name', 'hex_code']
    list_filter = ['name']


class PathsAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'path', 'parent_id')
    search_fields = ('name', 'path')
    list_filter = ('parent_id',)
    change_form_template = 'admin/MPD/products/change_form.html'

    def get_tree(self):
        paths = list(Paths.objects.all())
        tree = {}
        by_id = {p.id: p for p in paths}
        for p in paths:
            parent = p.parent_id
            if parent and parent in by_id:
                tree.setdefault(parent, []).append(p)
            else:
                tree.setdefault(None, []).append(p)

        def build_html(parent=None):
            html = ''
            children = tree.get(parent, [])
            if children:
                html += '<ul style="list-style:none; margin:0; padding-left:18px">'
                for p in children:
                    has_children = p.id in tree
                    node_id = f'path-node-{p.id}'
                    html += f'<li id="{node_id}">' \
                        + (f'<span class="toggle-btn" data-target="{node_id}-children" style="cursor:pointer; font-weight:bold;">[-]</span> ' if has_children else '') \
                        + f'{p.name or "(brak nazwy)"} [{p.path or "-"}] [id={p.id}]'
                    if has_children:
                        html += f'<div id="{node_id}-children">' + \
                            build_html(p.id) + '</div>'
                    html += '</li>'
                html += '</ul>'
            return html
        return build_html()

    def render_change_form(self, request, context, *args, **kwargs):
        context['paths_tree'] = self.get_tree()
        return super().render_change_form(request, context, *args, **kwargs)


admin.site.register(Paths, PathsAdmin)


@admin.register(IaiProductCounter)
class IaiProductCounterAdmin(admin.ModelAdmin):
    list_display = ['id', 'counter_value']
    readonly_fields = ['id', 'counter_value']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FullChangeFile)
class FullChangeFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'filename', 'timestamp',
                    'created_at', 'file_size']
    list_filter = ['created_at']
    search_fields = ['filename', 'timestamp']
    readonly_fields = ['id', 'filename', 'timestamp', 'created_at',
                       'bucket_url', 'local_path', 'file_size']
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# @admin.register(Categories)
# class CategoriesAdmin(admin.ModelAdmin):
#     list_display = ['id', 'name', 'path', 'parent_id']
#     search_fields = ['name', 'path']
#     list_filter = ['name']


@admin.register(Attributes)
class AttributesAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']
    list_filter = ['name']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


@admin.register(ProductVariants)
class ProductVariantsAdmin(admin.ModelAdmin):
    list_display = ['variant_id', 'product', 'color', 'producer_color',
                    'size', 'updated_at']
    list_filter = ['color', 'producer_color', 'size', 'updated_at']
    search_fields = ['variant_id', 'product__name']
    raw_id_fields = ['product', 'color', 'producer_color', 'size']
    readonly_fields = ['variant_id', 'updated_at']
    fields = ['product', 'color', 'producer_color', 'size',
              'exported_to_iai']
    show_full_result_count = False
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD').select_related('product', 'color', 'producer_color', 'size')


@admin.register(ProductvariantsSources)
class ProductVariantsSourcesAdmin(admin.ModelAdmin):
    list_display = ['id', 'variant', 'source', 'ean', 'variant_uid', 'producer_code',
                    'gtin14', 'gtin13', 'gtin12', 'isbn10', 'gtin8', 'upce', 'mpn', 'other']
    list_filter = ['source']
    search_fields = ['ean', 'variant_uid', 'producer_code', 'gtin14', 'gtin13',
                     'gtin12', 'isbn10', 'gtin8', 'upce', 'mpn', 'other']
    raw_id_fields = ['variant', 'source']
    show_full_result_count = False
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD').select_related(
            'variant', 'variant__product', 'variant__color', 'variant__size', 'source'
        )


@admin.register(ProductVariantsRetailPrice)
class ProductVariantsRetailPriceAdmin(admin.ModelAdmin):
    list_display = ['variant', 'retail_price',
                    'vat', 'currency', 'net_price', 'updated_at']
    list_filter = ['currency', 'updated_at']
    search_fields = ['variant__variant_id', 'variant__product__name']
    raw_id_fields = ['variant']
    readonly_fields = ['updated_at']
    show_full_result_count = False
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD').select_related(
            'variant', 'variant__product', 'variant__color', 'variant__size'
        )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'product',
                    'image_thumbnail', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['product__name', 'file_path']
    raw_id_fields = ['product']
    readonly_fields = ['id', 'image_thumbnail', 'file_path', 'updated_at']
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('product',)
        }),
        ('Obraz', {
            'fields': ('file_path', 'image_thumbnail'),
            'description': 'Miniatura obrazu - kliknij, aby otworzyć pełny obraz'
        }),
        ('Metadane', {
            'fields': ('id', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')

    @admin.display(description='Obraz')
    def image_thumbnail(self, obj):
        """Wyświetl miniaturę obrazu z możliwością kliknięcia"""
        if obj.file_path:
            url = resolve_image_url(obj.file_path) or obj.file_path
            # Jeśli to już pełny URL, użyj go
            if not url.startswith(('http://', 'https://')):
                # Jeśli to bucket key, skonwertuj na URL
                url = resolve_image_url(obj.file_path) or obj.file_path

            if url and url.startswith(('http://', 'https://')):
                return format_html(
                    '<a href="{}" target="_blank" title="Kliknij, aby otworzyć pełny obraz">'
                    '<img src="{}" style="max-width:150px; max-height:150px; border:1px solid #ddd; border-radius:4px; cursor:pointer;" />'
                    '</a>',
                    url, url
                )
        return format_html('<span style="color:#999;">Brak obrazu</span>')

    def save_model(self, request, obj, form, change):
        # Upewnij się, że product_id jest liczbą, nie ścieżką
        if obj.product_id and not isinstance(obj.product_id, int):
            if isinstance(obj.product_id, str):
                # Jeśli to ścieżka, nie używaj jej jako ID
                if '/' in str(obj.product_id) or 'MPD_test' in str(obj.product_id) or 'MPD/' in str(obj.product_id):
                    from django.contrib import messages
                    messages.error(
                        request, f"Nieprawidłowe product_id: {obj.product_id}. Oczekiwano liczby, otrzymano ścieżkę.")
                    return
                try:
                    obj.product_id = int(obj.product_id)
                except (ValueError, TypeError):
                    from django.contrib import messages
                    messages.error(
                        request, f"Nieprawidłowe product_id: {obj.product_id}.")
                    return
        obj.save(using='MPD')


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'brand', 'sort_order']
    list_filter = ['brand']
    search_fields = ['name', 'brand__name']
    ordering = ['brand', 'sort_order', 'name']


@admin.register(ProductSeries)
class ProductSeriesAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'brand']
    list_filter = ['brand']
    search_fields = ['name', 'brand__name']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


@admin.register(Seasons)
class SeasonsAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


# Model Categories nie jest już rejestrowany w admin (nieużywany)
# Zostanie wyrejestrowany na końcu pliku jeśli był wcześniej zarejestrowany


@admin.register(Vat)
class VatAdmin(admin.ModelAdmin):
    list_display = ['id', 'vat_rate']
    search_fields = ['vat_rate']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


@admin.register(ProductPaths)
class ProductPathsAdmin(admin.ModelAdmin):
    list_display = ['id', 'product_id', 'path_id']
    search_fields = ['product_id', 'path_id']
    list_filter = ['path_id']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


@admin.register(Units)
class UnitsAdmin(admin.ModelAdmin):
    list_display = ['id', 'unit_id', 'name']
    search_fields = ['name', 'unit_id']
    list_filter = ['unit_id']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


@admin.register(FabricComponent)
class FabricComponentAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(ProductFabric)
class ProductFabricAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'component', 'percentage']
    list_filter = ['component', 'percentage']
    search_fields = ['product__name', 'component__name']
    raw_id_fields = ['product', 'component']
    show_full_result_count = False
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD').select_related('product', 'component')


# Wyrejestruj model Categories z admin (nieużywany)
try:
    from django.contrib.admin.sites import NotRegistered
    try:
        admin.site.unregister(Categories)
    except NotRegistered:
        pass
except ImportError:
    pass
