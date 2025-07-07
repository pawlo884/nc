from django.contrib import admin  # type: ignore
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from .models import Brands, Products, Sizes, Sources, ProductVariants, ProductSet, ProductSetItem, StockAndPrices, StockHistory, Colors, Categories
from django.db import connections
# Register your models here.


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_per_page = 30
    fields = ['name', 'short_description', 'description', 'brand', 'show_variants',
              'show_images', 'show_related_products', 'edit_retail_prices']  # karta produktu
    list_display = ['id', 'name', 'description',
                    'brand', 'updated_at']  # widok listy produktów
    list_filter = ['brand']
    search_fields = ['id', 'name', 'description', 'brand__name']
    readonly_fields = ['show_variants', 'show_images',
                       'show_related_products', 'edit_retail_prices']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')

    @admin.display(description="Edycja cen detalicznych")
    def edit_retail_prices(self, obj):
        variants = ProductVariants.objects.filter(product=obj)
        if not variants:
            return "Brak wariantów produktu"

        # Grupowanie po (kolor, rozmiar, ean)
        grouped = {}
        for variant in variants:
            color_name = variant.color.name if variant.color else "-"
            size_name = variant.size.name if variant.size else "-"
            ean = variant.ean or "-"
            key = (color_name, size_name, ean)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(variant.variant_id)

        html = "<form method='post'>"
        # Dodaj pole do ustawiania ceny dla wszystkich wariantów
        html += "<div style='margin-bottom:12px;'>"
        html += "<label>Ustaw cenę detaliczną dla wszystkich wariantów: </label>"
        html += "<input type='number' step='0.01' id='set_all_price' style='width:100px;'>"
        html += "<button type='button' onclick='setAllRetailPrices()' style='margin-left:8px;'>Ustaw dla wszystkich</button>"
        html += "</div>"
        html += "<table style='border-collapse:collapse; width:100%;'>"
        html += "<tr><th style='border:1px solid #ccc;padding:4px 8px;'>kolor</th><th style='border:1px solid #ccc;padding:4px 8px;'>rozmiar</th><th style='border:1px solid #ccc;padding:4px 8px;'>ean</th><th style='border:1px solid #ccc;padding:4px 8px;'>źródło</th><th style='border:1px solid #ccc;padding:4px 8px;'>cena</th></tr>"

        for (color_name, size_name, ean), variant_ids in grouped.items():
            sources = []
            prices = []
            with connections['MPD'].cursor() as cursor:
                cursor.execute("""
                    SELECT s.name, sp.retail_price
                    FROM stock_and_prices sp
                    JOIN sources s ON sp.source_id = s.id
                    WHERE sp.variant_id IN %s
                    ORDER BY s.name
                """, [tuple(variant_ids)])
                for source_name, retail_price in cursor.fetchall():
                    sources.append(source_name)
                    if retail_price is not None:
                        prices.append(retail_price)
            sources_str = "<br>".join(sources) if sources else "-"
            first_price = prices[0] if prices else "0"
            html += "<tr>"
            html += "<td style='border:1px solid #ccc;padding:4px 8px;'>{}</td>".format(
                color_name)
            html += "<td style='border:1px solid #ccc;padding:4px 8px;'>{}</td>".format(
                size_name)
            html += "<td style='border:1px solid #ccc;padding:4px 8px;'>{}</td>".format(
                ean)
            html += "<td style='border:1px solid #ccc;padding:4px 8px;'>{}</td>".format(
                sources_str)
            html += "<td style='border:1px solid #ccc;padding:4px 8px;'><input class='retail-price-input' type='number' step='0.01' name='retail_price_{}' value='{}' style='width:80px;'></td>".format(
                variant_ids[0], first_price)
            html += "</tr>"
        html += "</table>"
        html += "<br><input type='submit' name='save_retail_prices' value='Zapisz ceny detaliczne' style='background-color:#79aec8; color:white; padding:8px 16px; border:none; border-radius:4px; cursor:pointer;'>"
        html += "</form>"
        # Dodaj JS do masowego ustawiania cen
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
        super().save_model(request, obj, form, change)
        if 'save_retail_prices' in request.POST:
            # Zbierz mapowanie variant_id -> (kolor, rozmiar, ean)
            variants = ProductVariants.objects.filter(product=obj)
            grouped = {}
            for variant in variants:
                color_name = variant.color.name if variant.color else "-"
                size_name = variant.size.name if variant.size else "-"
                ean = variant.ean or "-"
                key = (color_name, size_name, ean)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(variant.variant_id)
            for key, variant_ids in grouped.items():
                field_name = f'retail_price_{variant_ids[0]}'
                if field_name in request.POST:
                    value = request.POST[field_name]
                    try:
                        retail_price = float(value) if value.strip() else None
                        with connections['MPD'].cursor() as cursor:
                            if retail_price is not None:
                                cursor.execute("""
                                    UPDATE stock_and_prices 
                                    SET retail_price = %s 
                                    WHERE variant_id IN %s
                                """, [retail_price, tuple(variant_ids)])
                            else:
                                cursor.execute("""
                                    UPDATE stock_and_prices 
                                    SET retail_price = NULL 
                                    WHERE variant_id IN %s
                                """, [tuple(variant_ids)])
                    except (ValueError, TypeError):
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
        variants = ProductVariants.objects.filter(product=obj)
        if not variants:
            return "Brak wariantów"
        # Grupowanie po (kolor, kolor producenta, rozmiar, ean)
        grouped = {}
        for v in variants:
            color = v.color.name if v.color else "-"
            producer_color = v.producer_color.name if v.producer_color else "-"
            size = v.size.name if v.size else "-"
            ean = v.ean or "-"
            key = (color, producer_color, size, ean)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(v.variant_id)
        html = "<table style='border-collapse:collapse;'>"
        html += "<tr><th style='border:1px solid #ccc;padding:2px 6px;'>Kolor</th><th style='border:1px solid #ccc;padding:2px 6px;'>Kolor producenta</th><th style='border:1px solid #ccc;padding:2px 6px;'>Rozmiar</th><th style='border:1px solid #ccc;padding:2px 6px;'>Stan (suma)</th><th style='border:1px solid #ccc;padding:2px 6px;'>Ceny</th><th style='border:1px solid #ccc;padding:2px 6px;'>Cena detaliczna</th><th style='border:1px solid #ccc;padding:2px 6px;'>Źródła</th><th style='border:1px solid #ccc;padding:2px 6px;'>EAN</th></tr>"
        for (color, producer_color, size, ean), variant_ids in grouped.items():
            # Pobierz dane ze wszystkich źródeł dla tej grupy
            with connections['MPD'].cursor() as cursor:
                cursor.execute("""
                    SELECT s.name, SUM(sp.stock) as total_stock, sp.price, sp.retail_price, sp.currency
                    FROM stock_and_prices sp
                    JOIN sources s ON sp.source_id = s.id
                    WHERE sp.variant_id IN %s
                    GROUP BY s.name, sp.price, sp.retail_price, sp.currency
                """, [tuple(variant_ids)])
                rows = cursor.fetchall()
            # Suma stanów
            total_stock = sum([row[1] for row in rows]) if rows else 0
            # Ceny
            prices = [f"{row[2]} {row[4]}" for row in rows if row[2]
                      is not None and row[2] > 0]
            prices_str = "<br>".join(prices) if prices else "-"
            # Cena detaliczna - tylko jedna (pierwsza niepusta)
            retail_price = next(
                (row[3] for row in rows if row[3] is not None and row[3] > 0), None)
            retail_price_str = f"{retail_price} PLN" if retail_price else "-"
            # Źródła
            sources_str = ", ".join(
                [f"{row[0]}: {row[1]}" for row in rows]) if rows else "-"
            html += f"<tr><td style='border:1px solid #ccc;padding:2px 6px;'>{color}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{producer_color}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{size}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{total_stock}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{prices_str}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{retail_price_str}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{sources_str}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{ean}</td></tr>"
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
    list_display = ['id', 'name', 'category', 'unit', 'name_lower'] 
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


@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'path', 'parent_id']
    search_fields = ['name', 'path']
    list_filter = ['name']
