from django.shortcuts import render
from .models import Products, ProductSet, ProductSetItem, ProductPaths
from django.http import JsonResponse
from django.db import connections
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import ProductSetSerializer, ProductSetItemSerializer
from collections import defaultdict
from .export_to_xml import GatewayXMLExporter, FullXMLExporter, LightXMLExporter, ProducersXMLExporter, StocksXMLExporter, UnitsXMLExporter, FullChangeXMLExporter, CategoriesXMLExporter, SizesXMLExporter
import logging
from django.http import HttpResponse
import requests
from matterhorn.defs_db import DO_SPACES_BUCKET, DO_SPACES_REGION
from django.urls import reverse

from django.views.decorators.csrf import csrf_exempt
import json

logger = logging.getLogger(__name__)

# Create your views here.


def products(request):
    products = list(Products.objects.all())
    product_ids = [p.id for p in products]
    variants_by_product = {}
    if product_ids:
        variants_by_product = defaultdict(list)
        with connections['MPD'].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    pv.product_id,
                    pv.variant_id,
                    pv.size_id,
                    s.name as size_name,
                    c.id as color_id,
                    c.name as color_name,
                    c.hex_code,
                    sp.stock,
                    sp.price
                FROM product_variants pv
                LEFT JOIN sizes s ON pv.size_id = s.id
                LEFT JOIN colors c ON pv.color_id = c.id
                LEFT JOIN stock_and_prices sp ON pv.variant_id = sp.variant_id AND sp.source_id = 2
                WHERE pv.product_id IN %s
                ORDER BY pv.product_id, s.name, c.name
            """, [tuple(product_ids)])
            variants = cursor.fetchall()
            for row in variants:
                variants_by_product[row[0]].append({
                    'variant_id': row[1],
                    'size_id': row[2],
                    'size_name': row[3],
                    'color_id': row[4],
                    'color_name': row[5],
                    'hex_code': row[6],
                    'stock': row[7],
                    'price': row[8]
                })
    for product in products:
        setattr(product, 'variants', variants_by_product.get(product.id, []))
    return render(request, 'MPD/mpd.html', {'products': products})


def test_connection(request):
    try:
        with connections['MPD'].cursor() as cursor:
            # Sprawdźmy schemat tabel
            cursor.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('brands', 'products', 'sizes')
                AND table_schema = 'public'
            """)
            tables = cursor.fetchall()

            # Sprawdźmy uprawnienia do tabel
            cursor.execute("""
                SELECT grantee, privilege_type, table_name
                FROM information_schema.role_table_grants 
                WHERE table_name IN ('brands', 'products', 'sizes')
                AND table_schema = 'public'
            """)
            permissions = cursor.fetchall()

            return JsonResponse({
                'status': 'success',
                'message': 'Połączenie z bazą MPD działa poprawnie',
                'tables': tables,
                'permissions': permissions
            })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def test_table_structure(request):
    try:
        with connections['MPD'].cursor() as cursor:
            # Sprawdź strukturę tabeli products
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default,
                       (SELECT string_agg(constraint_type, ', ')
                        FROM information_schema.table_constraints tc
                        INNER JOIN information_schema.constraint_column_usage ccu 
                        ON tc.constraint_name = ccu.constraint_name
                        WHERE ccu.table_name = c.table_name 
                        AND ccu.column_name = c.column_name) as constraints
                FROM information_schema.columns c
                WHERE table_name = 'products'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()

            return JsonResponse({
                'status': 'success',
                'table_structure': [
                    {
                        'column': col[0],
                        'type': col[1],
                        'nullable': col[2],
                        'default': col[3],
                        'constraints': col[4]
                    } for col in columns
                ]
            })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class ProductSetViewSet(viewsets.ModelViewSet):
    queryset = ProductSet.objects.all()
    serializer_class = ProductSetSerializer

    @action(detail=True, methods=['post'])
    def add_product(self, request, pk=None):
        set = self.get_object()
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        try:
            product = Products.objects.get(id=product_id)
            ProductSetItem.objects.create(
                set=set,
                mapped_product=product,
                quantity=quantity
            )
            return Response({'status': 'product added to set'})
        except Products.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def remove_product(self, request, pk=None):
        set = self.get_object()
        product_id = request.data.get('product_id')

        try:
            item = ProductSetItem.objects.get(
                set=set,
                mapped_product_id=product_id
            )
            item.delete()
            return Response({'status': 'product removed from set'})
        except ProductSetItem.DoesNotExist:
            return Response(
                {'error': 'Product not found in set'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        set = self.get_object()
        items = ProductSetItem.objects.filter(set=set)
        serializer = ProductSetItemSerializer(items, many=True)
        return Response(serializer.data)


def export_xml(request, source_name):
    try:
        # Zawsze używa Matterhorn (id=2), ignoruje source_name
        exporter = GatewayXMLExporter()
        result = exporter.export()
        if result['bucket_url']:
            return JsonResponse({'status': 'success', 'url': result['bucket_url']})
        return JsonResponse({'status': 'error', 'message': 'Nie udało się wygenerować pliku XML'}, status=500)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def export_full_xml(request):
    """Widok do eksportu pełnego XML"""
    return JsonResponse({'status': 'error', 'message': 'Ten endpoint nie jest już obsługiwany. Użyj /generate-full-xml/.'}, status=410)


XML_FILES = [
    "full", "full_change", "light", "categories", "sizes", "producers", "units", "parameters", "stocks", "series", "warranties", "preset"
]

BUCKET_URL = f"https://{DO_SPACES_BUCKET}.{DO_SPACES_REGION}.digitaloceanspaces.com/MPD_test/xml/matterhorn/"
XML_FILE_MAP = {
    "full": "full.xml",
    "full_change": "full_change.xml",
    "light": "lightoferta.xml",
    "categories": "categories.xml",
    "sizes": "sizes.xml",
    "producers": "producers.xml",
    "units": "units.xml",
    "parameters": "parameters.xml",
    "stocks": "stocks.xml",
    "series": "series.xml",
    "warranties": "warranties.xml",
    "preset": "preset.xml"
}


def get_xml_file(request, xml_type):
    if xml_type not in XML_FILE_MAP:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy typ XML'}, status=404)
    file_url = BUCKET_URL + XML_FILE_MAP[xml_type]
    try:
        resp = requests.get(file_url)
        if resp.status_code == 200:
            response = HttpResponse(
                resp.content, content_type='application/xml')
            response['Content-Disposition'] = f'attachment; filename="{XML_FILE_MAP[xml_type]}"'
            return response
        else:
            return JsonResponse({'status': 'error', 'message': 'Nie znaleziono pliku XML'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def get_gateway_xml(request):
    source_name = request.GET.get('source')
    if not source_name:
        return JsonResponse({'status': 'error', 'message': 'Brak parametru source'}, status=400)
    file_url = BUCKET_URL + "gateway.xml"
    try:
        resp = requests.get(file_url)
        if resp.status_code == 200:
            response = HttpResponse(
                resp.content, content_type='application/xml')
            response['Content-Disposition'] = 'attachment; filename="gateway.xml"'
            return response
        else:
            return JsonResponse({'status': 'error', 'message': 'Nie znaleziono pliku XML'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def update_all_gateways():
    """Automatycznie aktualizuje plik gateway.xml dla Matterhorn (id=2)"""
    try:
        gateway_exporter = GatewayXMLExporter()
        gateway_exporter.export()
        logger.info("Zaktualizowano gateway.xml dla Matterhorn")
    except Exception as e:
        logger.warning(f"Błąd aktualizacji gateway.xml: {str(e)}")


@csrf_exempt
def generate_full_xml(request):
    exporter = FullXMLExporter()
    # Używa metody z zapisem rekordu do bazy - eksport przyrostowy (tylko nowe produkty)
    exporter_result = exporter.export_incremental()

    # Automatycznie zaktualizuj wszystkie gateway.xml (dodatkowe zabezpieczenie)
    update_all_gateways()

    # Zapisz lokalnie dla debugowania
    import os
    local_path = 'MPD_test/xml/matterhorn/full.xml'
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    with open(exporter_result['local_path'], 'rb') as f:
        content = f.read()

    # Zapisz kopię lokalnie
    with open(local_path, 'wb') as f:
        f.write(content)

    logger.info(f"Full.xml wygenerowany i zapisany lokalnie: {local_path}")

    return HttpResponse(content, content_type='application/xml')


@csrf_exempt
def generate_full_change_xml(request):
    exporter = FullChangeXMLExporter()
    exporter_result = exporter.export()

    # Automatycznie zaktualizuj wszystkie gateway.xml
    update_all_gateways()

    with open(exporter_result['local_path'], 'rb') as f:
        content = f.read()

    # Zapisz lokalnie dla debugowania
    import os
    local_path = 'MPD_test/xml/matterhorn/full_change.xml'
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    with open(local_path, 'wb') as f:
        f.write(content)

    logger.info(
        f"Full_change.xml wygenerowany i zapisany lokalnie: {local_path}")

    return HttpResponse(content, content_type='application/xml')


@csrf_exempt
def generate_gateway_xml(request, source_name):
    try:
        # Zawsze używa Matterhorn (id=2), ignoruje source_name
        exporter = GatewayXMLExporter()
        exporter_result = exporter.export()
        # Pobierz wygenerowany plik lokalny i zwróć jako XML
        with open(exporter_result['local_path'], 'rb') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/xml')
    except Exception:
        return HttpResponse('<empty/>', content_type='application/xml')


@csrf_exempt
def generate_light_xml(request):
    exporter = LightXMLExporter()
    exporter_result = exporter.export()

    # Automatycznie zaktualizuj wszystkie gateway.xml
    update_all_gateways()

    with open(exporter_result['local_path'], 'rb') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/xml')


@csrf_exempt
def generate_producers_xml(request):
    exporter = ProducersXMLExporter()
    exporter_result = exporter.export()

    # Automatycznie zaktualizuj wszystkie gateway.xml
    update_all_gateways()

    with open(exporter_result['local_path'], 'rb') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/xml')


@csrf_exempt
def generate_stocks_xml(request):
    exporter = StocksXMLExporter()
    exporter_result = exporter.export()

    # Automatycznie zaktualizuj wszystkie gateway.xml
    update_all_gateways()

    with open(exporter_result['local_path'], 'rb') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/xml')


@csrf_exempt
def generate_units_xml(request):
    exporter = UnitsXMLExporter()
    exporter_result = exporter.export()

    # Automatycznie zaktualizuj wszystkie gateway.xml
    update_all_gateways()

    with open(exporter_result['local_path'], 'rb') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/xml')


@csrf_exempt
def empty_xml(request):
    return HttpResponse('<empty/>', content_type='application/xml')


@csrf_exempt
def generate_categories_xml(request):
    """Generuje XML z kategoriami zgodnie ze schematem categories.xsd"""
    exporter = CategoriesXMLExporter()
    exporter_result = exporter.export()

    # Automatycznie zaktualizuj wszystkie gateway.xml
    update_all_gateways()

    with open(exporter_result['local_path'], 'rb') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/xml')


@csrf_exempt
def generate_sizes_xml(request):
    """Generuje XML z rozmiarami zgodnie ze schematem sizes.xsd"""
    exporter = SizesXMLExporter()
    exporter_result = exporter.export()

    # Automatycznie zaktualizuj wszystkie gateway.xml
    update_all_gateways()

    with open(exporter_result['local_path'], 'rb') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/xml')


@csrf_exempt
def generate_parameters_xml(request):
    """Generuje XML z parametrami - tymczasowo puste"""
    return HttpResponse('<parameters file_format="IOF" version="3.0" generated_by="nc" language="pol"><!-- Puste parametry --></parameters>', content_type='application/xml')


@csrf_exempt
def generate_series_xml(request):
    """Generuje XML z seriami - tymczasowo puste"""
    return HttpResponse('<series file_format="IOF" version="3.0" generated_by="nc" language="pol"><!-- Puste serie --></series>', content_type='application/xml')


@csrf_exempt
def generate_warranties_xml(request):
    """Generuje XML z gwarancjami - tymczasowo puste"""
    return HttpResponse('<warranties file_format="IOF" version="3.0" generated_by="nc" language="pol"><!-- Puste gwarancje --></warranties>', content_type='application/xml')


@csrf_exempt
def generate_preset_xml(request):
    """Generuje XML z presetami - tymczasowo puste"""
    return HttpResponse('<preset file_format="IOF" version="3.0" generated_by="nc" language="pol"><!-- Puste presety --></preset>', content_type='application/xml')


@csrf_exempt
def generate_gateway_xml_api(request):
    """Generuje gateway.xml z endpointami API"""
    try:
        # Zawsze używa Matterhorn (id=2)
        exporter = GatewayXMLExporter()

        # Przekaż czas żądania HTTP do eksportera (timezone-aware)
        request_time = timezone.now()

        xml_content = exporter.generate_xml(request_time=request_time)

        # Zapisz lokalnie dla debugowania
        import os
        local_path = 'MPD_test/xml/matterhorn/gateway.xml'
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        logger.info(
            f"Gateway.xml wygenerowany i zapisany lokalnie: {local_path}")

        return HttpResponse(xml_content, content_type='application/xml')
    except Exception as e:
        logger.error(f"Błąd podczas generowania gateway.xml: {str(e)}")
        return HttpResponse('<gateway><error>Błąd generowania</error></gateway>', content_type='application/xml')


def xml_links(request):
    links = []
    # full.xml
    url = reverse('generate_full_xml')
    links.append(('full', url))
    # full_change.xml
    url = reverse('generate_full_change_xml')
    links.append(('full_change', url))
    # light.xml
    url = reverse('generate_light_xml')
    links.append(('light', url))
    # producers.xml
    url = reverse('generate_producers_xml')
    links.append(('producers', url))
    # stocks.xml
    url = reverse('generate_stocks_xml')
    links.append(('stocks', url))
    # units.xml
    url = reverse('generate_units_xml')
    links.append(('units', url))
    # gateway.xml (tylko dla Matterhorn id=2)
    try:
        # Użyj dowolnej nazwy dla URL-a, GatewayXMLExporter i tak użyje id=2
        gateway_url = reverse('generate_gateway_xml', args=['matterhorn'])
        links.append(('gateway', gateway_url))
    except Exception:
        pass  # Brak linku w przypadku błędu
    # pozostałe typy (puste)
    for xml_type in [k for k in XML_FILE_MAP if k not in ['full', 'full_change', 'light', 'producers', 'stocks', 'units']]:
        url = reverse('empty_xml') + f'?type={xml_type}'
        links.append((xml_type, url))
    html = '<h2>Dostępne pliki XML:</h2><ul>'
    for xml_type, url in links:
        html += f'<li><a href="{url}" target="_blank">{xml_type}</a></li>'
    html += '</ul>'
    return HttpResponse(html)


@csrf_exempt
def manage_product_paths(request):
    """
    Endpoint do zarządzania przypisaniami ścieżek do produktów
    Obsługuje przypisywanie i usuwanie przypisań ścieżek
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Tylko metoda POST jest obsługiwana'}, status=405)

    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        path_id = data.get('path_id')
        action = data.get('action')  # 'assign' lub 'unassign'

        if not all([product_id, path_id, action]):
            return JsonResponse({'status': 'error', 'message': 'Brak wymaganych parametrów'}, status=400)

        if action not in ['assign', 'unassign']:
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa akcja'}, status=400)

        # Sprawdź czy produkt istnieje
        try:
            product = Products.objects.using('MPD').get(id=product_id)
        except Products.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Produkt nie istnieje'}, status=404)

        if action == 'assign':
            # Przypisz ścieżkę do produktu (jeśli jeszcze nie jest przypisana)
            product_path, created = ProductPaths.objects.using('MPD').get_or_create(
                product_id=product_id,
                path_id=path_id
            )
            if created:
                message = f'Ścieżka {path_id} została przypisana do produktu {product.name}'
            else:
                message = f'Ścieżka {path_id} była już przypisana do produktu {product.name}'

        elif action == 'unassign':
            # Usuń przypisanie ścieżki do produktu
            deleted_count, _ = ProductPaths.objects.using('MPD').filter(
                product_id=product_id,
                path_id=path_id
            ).delete()
            if deleted_count > 0:
                message = f'Ścieżka {path_id} została odłączona od produktu {product.name}'
            else:
                message = f'Ścieżka {path_id} nie była przypisana do produktu {product.name}'

        logger.info(f"Zarządzanie ścieżkami produktu: {message}")

        return JsonResponse({
            'status': 'success',
            'message': message,
            'product_id': product_id,
            'path_id': path_id,
            'action': action
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format JSON'}, status=400)
    except Exception as e:
        logger.error(f"Błąd podczas zarządzania ścieżkami produktu: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Błąd serwera'}, status=500)
