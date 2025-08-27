from django.contrib import admin  # type: ignore
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from .models import Brands, Products, Sizes, Sources, ProductVariants, ProductSet, ProductSetItem, StockAndPrices, StockHistory, Colors, ProductVariantsRetailPrice, ProductvariantsSources, Paths, ProductPaths, IaiProductCounter, FullChangeFile
import decimal
# Register your models here.


# Usuwam ProductVariantsInline i wpis inlines = [ProductVariantsInline] z ProductsAdmin
# (pozostawiam tylko show_variants jako readonly_field)


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_per_page = 30
    fields = ['visibility', 'name', 'short_description', 'description', 'brand', 'show_variants',
              'show_images', 'show_related_products', 'edit_retail_prices']  # karta produktu
    list_display = ['id', 'name', 'description',
                    'brand', 'updated_at', 'visibility']  # widok listy produktów
    list_filter = ['brand']
    search_fields = ['id', 'name', 'description', 'brand__name']
    readonly_fields = ['show_variants', 'show_images',
                       'show_related_products', 'edit_retail_prices']
    change_form_template = 'admin/MPD/products/change_form.html'

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')

    @admin.display(description="Edycja cen detalicznych")
    def edit_retail_prices(self, obj):
        variants = list(ProductVariants.objects.filter(product=obj))
        if not variants:
            return "Brak wariantów produktu"
        variant_ids = [v.variant_id for v in variants]
        # Pobierz EANy i ceny detaliczne jednym zapytaniem
        sources_map = {s.variant.variant_id: s.ean for s in ProductvariantsSources.objects.filter(
            variant__variant_id__in=variant_ids)}
        retail_map = {r.variant.variant_id: r.retail_price for r in ProductVariantsRetailPrice.objects.using(
            'MPD').filter(variant__variant_id__in=variant_ids)}
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
        html += "<tr><th style='border:1px solid #ccc;padding:4px 8px;'>kolor</th><th style='border:1px solid #ccc;padding:4px 8px;'>rozmiar</th><th style='border:1px solid #ccc;padding:4px 8px;'>ean</th><th style='border:1px solid #ccc;padding:4px 8px;'>cena detaliczna</th><th style='border:1px solid #ccc;padding:4px 8px;'>VAT</th><th style='border:1px solid #ccc;padding:4px 8px;'>waluta</th></tr>"
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

    @admin.display(description="Warianty produktu")
    def show_variants(self, obj):
        variants = list(ProductVariants.objects.filter(product=obj))
        if not variants:
            return "Brak wariantów"
        variant_ids = [v.variant_id for v in variants]
        # Pobierz źródła, EANy i ceny detaliczne dla wszystkich wariantów jednym zapytaniem
        sources_qs = ProductvariantsSources.objects.filter(
            variant__variant_id__in=variant_ids)
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
            key = (color, producer_color, size, sources_display, eans_display)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(v.variant_id)
        html = "<table style='border-collapse:collapse;'>"
        html += "<tr><th style='border:1px solid #ccc;padding:2px 6px;'>Kolor</th><th style='border:1px solid #ccc;padding:2px 6px;'>Kolor producenta</th><th style='border:1px solid #ccc;padding:2px 6px;'>Rozmiar</th><th style='border:1px solid #ccc;padding:2px 6px;'>Stan (suma)</th><th style='border:1px solid #ccc;padding:2px 6px;'>Ceny</th><th style='border:1px solid #ccc;padding:2px 6px;'>Cena detaliczna</th><th style='border:1px solid #ccc;padding:2px 6px;'>Źródła</th><th style='border:1px solid #ccc;padding:2px 6px;'>EAN</th></tr>"
        for (color, producer_color, size, sources_display, eans_display), variant_ids in grouped.items():
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
            html += f"<tr><td style='border:1px solid #ccc;padding:2px 6px;'>{color}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{producer_color}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{size}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{total_stock}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{prices_str}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{retail_price_str}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{sources_display}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{eans_display}</td></tr>"
        html += "</table>"
        return mark_safe(html)

    @admin.display(description="Zdjęcia produktu")
    def show_images(self, obj):
        print(f"\n=== DEBUG: show_images dla produktu {obj.id} ===")

        # Grupowanie zdjęć po nazwie koloru producenta lub zwykłego koloru (nie używamy variant_id)
        images = obj.images.all() if hasattr(obj, 'images') else []
        # Pobierz wszystkie unikalne kolory producenta i zwykłe kolory z wariantów produktu
        producer_colors = (
            ProductVariants.objects.filter(
                product=obj, producer_color__isnull=False)
            .values_list('producer_color__id', 'producer_color__name')
            .distinct()
        )
        normal_colors = (
            ProductVariants.objects.filter(product=obj, color__isnull=False)
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
                    url = img.file_path
                    html += f'<a href="{url}" target="_blank"><img src="{url}" style="max-height:60px; margin:2px; border:1px solid #ccc;" /></a>'
                html += '</div>'
        # Wyświetl zdjęcia z przypisanym zwykłym kolorem
        for cid, imgs in images_by_normal_color.items():
            color_name = normal_color_name_map.get(cid, f"ID {cid}")
            if imgs:
                html += f'<div style="margin-bottom: 12px;"><b>{color_name}</b><br>'
                for img in imgs:
                    url = img.file_path
                    html += f'<a href="{url}" target="_blank"><img src="{url}" style="max-height:60px; margin:2px; border:1px solid #ccc;" /></a>'
                html += '</div>'
        # Wyświetl zdjęcia bez przypisanego koloru
        if images_no_color:
            html += '<div style="margin-bottom: 12px;"><b>Inne zdjęcia</b><br>'
            for img in images_no_color:
                url = img.file_path
                html += f'<a href="{url}" target="_blank"><img src="{url}" style="max-height:60px; margin:2px; border:1px solid #ccc;" /></a>'
            html += '</div>'
        if not html:
            return "Brak zdjęć produktu"
        return format_html(html)

    @admin.display(description="Powiązane produkty")
    def show_related_products(self, obj):
        html = ""
        # Zestawy, do których należy ten produkt
        set_items = list(ProductSetItem.objects.filter(product_id=obj.id))
        set_ids = [si.product_set_id for si in set_items]
        if set_items:
            html += "<b>Zestawy, do których należy ten produkt:</b>"
            for set_id in set_ids:
                try:
                    set_obj = ProductSet.objects.get(id=set_id)
                    set_products = ProductSetItem.objects.filter(
                        product_set_id=set_id).exclude(product_id=obj.id)
                    html += f"<div style='margin-bottom:8px;'><span style='font-weight:600;'>Zestaw: {set_obj.name} (ID: {set_obj.id})</span></div>"
                    html += "<div style='display:flex; flex-direction:row; flex-wrap:wrap; gap:24px; align-items:flex-start; margin-bottom:16px; width:100%;'>"
                    for sp in set_products:
                        try:
                            prod = Products.objects.get(id=sp.product_id)
                            admin_url = f"/admin/MPD/products/{prod.id}/change/"
                            img_html = ""
                            images_rel = getattr(prod, 'images', None)
                            first_img = images_rel.first() if images_rel and hasattr(
                                images_rel, 'first') else None
                            if first_img:
                                img_html = f'<a href="{admin_url}"><img src="{first_img.file_path}" style="max-height:40px; max-width:40px; margin-right:5px; border:1px solid #ccc; vertical-align:middle;" /></a>'
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
            for p in series_products:
                admin_url = f"/admin/MPD/products/{p.id}/change/"
                img_html = ""
                images_rel = getattr(p, 'images', None)
                first_img = images_rel.first() if images_rel and hasattr(
                    images_rel, 'first') else None
                if first_img:
                    img_html = f'<a href=\"{admin_url}\"><img src=\"{first_img.file_path}\" style=\"max-height:40px; max-width:40px; margin-right:5px; border:1px solid #ccc; vertical-align:middle;\" /></a>'
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
    fields = ['name', 'logo_url', 'opis', 'url']
    list_display = ['id', 'name', 'url']
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

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')


@admin.register(ProductSet)
class ProductSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'mapped_product', 'created_at', 'updated_at')
    search_fields = ('name', 'mapped_product__name')
    list_filter = ('created_at', 'updated_at')
    raw_id_fields = ('mapped_product',)


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
                    'created_at', 'file_size', 'created_at_record']
    list_filter = ['created_at', 'created_at_record']
    search_fields = ['filename', 'timestamp']
    readonly_fields = ['id', 'filename', 'timestamp', 'created_at',
                       'bucket_url', 'local_path', 'file_size', 'created_at_record']
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
