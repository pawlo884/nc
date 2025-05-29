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
    fields = ['name', 'description', 'brand', 'show_variants',
              'show_images', 'show_related_products']
    list_display = ['id', 'name', 'description', 'brand', 'updated_at']
    list_filter = ['brand']
    search_fields = ['id', 'name', 'description', 'brand__name']
    readonly_fields = ['show_variants', 'show_images', 'show_related_products']

    def get_queryset(self, request):
        return super().get_queryset(request).using('MPD')

    @admin.display(description="Warianty produktu")
    def show_variants(self, obj):
        variants = ProductVariants.objects.filter(product=obj)
        if not variants:
            return "Brak wariantów"
        html = "<table style='border-collapse:collapse;'>"
        html += "<tr><th style='border:1px solid #ccc;padding:2px 6px;'>Kolor</th><th style='border:1px solid #ccc;padding:2px 6px;'>Kolor producenta</th><th style='border:1px solid #ccc;padding:2px 6px;'>Rozmiar</th><th style='border:1px solid #ccc;padding:2px 6px;'>Stan (suma)</th><th style='border:1px solid #ccc;padding:2px 6px;'>Źródła</th><th style='border:1px solid #ccc;padding:2px 6px;'>EAN</th></tr>"
        for v in variants:
            size_name = v.size.name if v.size else ""
            producer_color_name = v.producer_color.name if v.producer_color else "-"
            with connections['MPD'].cursor() as cursor:
                cursor.execute("""
                    SELECT s.name, SUM(sp.stock) as total_stock
                    FROM stock_and_prices sp
                    JOIN sources s ON sp.source_id = s.id
                    WHERE sp.variant_id = %s
                    GROUP BY s.name
                """, [v.variant_id])
                stock_data = cursor.fetchall()
            total_stock = sum([row[1]
                              for row in stock_data]) if stock_data else 0
            sources_str = ", ".join(
                [f"{row[0]}: {row[1]}" for row in stock_data]) if stock_data else "-"
            html += f"<tr><td style='border:1px solid #ccc;padding:2px 6px;'>{v.color}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{producer_color_name}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{size_name}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{total_stock}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{sources_str}</td><td style='border:1px solid #ccc;padding:2px 6px;'>{v.ean}</td></tr>"
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
    fields = ['name', 'logo_url', 'opis']
    list_display = ['id', 'name']
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
    fields = ['name', 'location', 'type']
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
