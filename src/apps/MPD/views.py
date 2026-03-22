from django.shortcuts import render
from .models import Products, ProductSet, ProductSetItem, ProductPaths, ProductAttribute
from .models import Brands, Colors, Sizes, ProductVariants, ProductVariantsRetailPrice, ProductvariantsSources
from .models import FabricComponent, ProductFabric, Attributes
from django.http import JsonResponse
from django.db import connections, transaction
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import ProductSetSerializer, ProductSetItemSerializer
from collections import defaultdict
from .export_to_xml import GatewayXMLExporter, FullXMLExporter, LightXMLExporter, ProducersXMLExporter, StocksXMLExporter, UnitsXMLExporter, FullChangeXMLExporter, CategoriesXMLExporter, SizesXMLExporter
import logging
from django.http import HttpResponse
import requests
from matterhorn1.defs_db import BUCKET_PUBLIC_BASE_URL, resolve_image_url
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


def product_mapping(request):
    """
    Widok do mapowania produktów z matterhorn1 do MPD
    """
    return render(request, 'MPD/product_mapping.html')


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
                product_set=set,
                product=product,
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
                product_set=set,
                product_id=product_id
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
        items = ProductSetItem.objects.filter(product_set=set)
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

XML_BUCKET_PREFIX = "MPD_test/xml/"
if BUCKET_PUBLIC_BASE_URL:
    BUCKET_URL = f"{BUCKET_PUBLIC_BASE_URL.rstrip('/')}/{XML_BUCKET_PREFIX}"
else:
    BUCKET_URL = None
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
    if not BUCKET_URL:
        return JsonResponse({'status': 'error', 'message': 'Brak konfiguracji MinIO/S3 dla plików XML'}, status=500)
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
    if not BUCKET_URL:
        return JsonResponse({'status': 'error', 'message': 'Brak konfiguracji MinIO/S3 dla plików XML'}, status=500)
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
    local_path = 'misc/MPD_test/xml/full.xml'
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

    # Sprawdź czy eksport został pominięty (brak produktów do wyeksportowania)
    if exporter_result.get('skipped', False) or exporter_result.get('local_path') is None:
        return JsonResponse({
            'status': 'skipped',
            'message': 'Brak produktów do wyeksportowania w full_change.xml',
            'bucket_url': None
        })

    # Automatycznie zaktualizuj wszystkie gateway.xml
    update_all_gateways()

    with open(exporter_result['local_path'], 'rb') as f:
        content = f.read()

    # Zapisz lokalnie dla debugowania
    import os
    local_path = 'misc/MPD_test/xml/full_change.xml'
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
        local_path = 'misc/MPD_test/xml/gateway.xml'
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


@csrf_exempt
def manage_product_fabric(request):
    """
    Endpoint do zarządzania składem materiałowym produktów
    Obsługuje dodawanie i usuwanie komponentów materiałowych
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Tylko metoda POST jest obsługiwana'}, status=405)

    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        action = data.get('action')  # 'add' lub 'remove'

        if not all([product_id, action]):
            return JsonResponse({'status': 'error', 'message': 'Brak wymaganych parametrów'}, status=400)

        if action not in ['add', 'remove']:
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa akcja'}, status=400)

        # Konwertuj product_id na int
        try:
            product_id = int(product_id)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format ID produktu'}, status=400)

        # Sprawdź czy produkt istnieje
        try:
            product = Products.objects.using('MPD').get(id=product_id)
        except Products.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Produkt nie istnieje'}, status=404)

        if action == 'add':
            # Dodaj komponent do składu produktu
            component_id = data.get('component_id')
            percentage = data.get('percentage')

            if not component_id or not percentage:
                return JsonResponse({'status': 'error', 'message': 'Brak ID komponentu lub procentu'}, status=400)

            # Konwertuj na int
            try:
                component_id = int(component_id)
                percentage = int(percentage)
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format ID komponentu lub procentu'}, status=400)

            # Sprawdź czy komponent istnieje
            try:
                component = FabricComponent.objects.using(
                    'MPD').get(id=component_id)
            except FabricComponent.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Komponent nie istnieje'}, status=404)

            # Sprawdź czy komponent nie jest już przypisany do produktu
            if ProductFabric.objects.using('MPD').filter(product_id=product_id, component_id=component_id).exists():
                return JsonResponse({'status': 'error', 'message': 'Komponent jest już przypisany do tego produktu'}, status=400)

            # Utwórz nowy wpis składu
            ProductFabric.objects.using('MPD').create(
                product_id=product_id,
                component_id=component_id,
                percentage=percentage
            )

            message = f'Dodano komponent {component.name} ({percentage}%) do składu produktu {product.name}'

        elif action == 'remove':
            # Usuń komponent ze składu produktu
            component_id = data.get('component_id')
            if not component_id:
                return JsonResponse({'status': 'error', 'message': 'Brak ID komponentu do usunięcia'}, status=400)

            # Konwertuj na int
            try:
                component_id = int(component_id)
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format ID komponentu'}, status=400)

            # Pobierz nazwę komponentu przed usunięciem
            try:
                component = FabricComponent.objects.using(
                    'MPD').get(id=component_id)
                component_name = component.name
            except FabricComponent.DoesNotExist:
                component_name = f"ID {component_id}"

            # Usuń komponent ze składu
            deleted_count, _ = ProductFabric.objects.using('MPD').filter(
                product_id=product_id,
                component_id=component_id
            ).delete()

            if deleted_count > 0:
                message = f'Usunięto komponent {component_name} ze składu produktu {product.name}'
            else:
                message = f'Komponent {component_name} nie był przypisany do produktu {product.name}'

        logger.info(f"Zarządzanie składem materiałowym: {message}")

        return JsonResponse({
            'status': 'success',
            'message': message,
            'product_id': product_id,
            'action': action
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format JSON'}, status=400)
    except Exception as e:
        logger.error(
            f"Błąd podczas zarządzania składem materiałowym: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Błąd serwera'}, status=500)


@csrf_exempt
def manage_product_attributes(request):
    """
    Endpoint do zarządzania atrybutami produktów
    Obsługuje dodawanie i usuwanie atrybutów
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Tylko metoda POST jest obsługiwana'}, status=405)

    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        action = data.get('action')  # 'add' lub 'remove'

        if not all([product_id, action]):
            return JsonResponse({'status': 'error', 'message': 'Brak wymaganych parametrów'}, status=400)

        if action not in ['add', 'remove']:
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa akcja'}, status=400)

        # Konwertuj product_id na int
        try:
            product_id = int(product_id)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format ID produktu'}, status=400)

        # Sprawdź czy produkt istnieje
        try:
            product = Products.objects.using('MPD').get(id=product_id)
        except Products.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Produkt nie istnieje'}, status=404)

        if action == 'add':
            # Dodaj atrybuty do produktu
            attribute_ids = data.get('attribute_ids', [])
            if not attribute_ids:
                return JsonResponse({'status': 'error', 'message': 'Brak atrybutów do dodania'}, status=400)

            added_count = 0
            for attribute_id in attribute_ids:
                product_attribute, created = ProductAttribute.objects.using('MPD').get_or_create(
                    product_id=product_id,
                    attribute_id=attribute_id
                )
                if created:
                    added_count += 1

            message = f'Dodano {added_count} atrybutów do produktu {product.name}'

        elif action == 'remove':
            # Usuń atrybut z produktu
            attribute_id = data.get('attribute_id')
            if not attribute_id:
                return JsonResponse({'status': 'error', 'message': 'Brak ID atrybutu do usunięcia'}, status=400)

            # Konwertuj na int jeśli to string
            try:
                attribute_id = int(attribute_id)
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format ID atrybutu'}, status=400)

            logger.info(
                f"Usuwanie atrybutu: product_id={product_id}, attribute_id={attribute_id}")
            logger.info(f"Dane żądania: {data}")

            # Sprawdź czy atrybut istnieje przed usunięciem
            try:
                attribute = Attributes.objects.using(
                    'MPD').get(id=attribute_id)
                attribute_name = attribute.name
            except Attributes.DoesNotExist:
                attribute_name = f"ID {attribute_id}"

            # Sprawdź czy atrybut jest przypisany do produktu
            existing_relation = ProductAttribute.objects.using('MPD').filter(
                product_id=product_id,
                attribute_id=attribute_id
            ).first()

            if not existing_relation:
                logger.warning(
                    f"Atrybut {attribute_id} nie jest przypisany do produktu {product_id}")
                return JsonResponse({'status': 'error', 'message': f'Atrybut {attribute_name} nie jest przypisany do tego produktu'}, status=404)

            deleted_count, _ = ProductAttribute.objects.using('MPD').filter(
                product_id=product_id,
                attribute_id=attribute_id
            ).delete()

            logger.info(f"Usunięto {deleted_count} rekordów atrybutu")

            if deleted_count > 0:
                message = f'Usunięto atrybut {attribute_name} z produktu {product.name}'
            else:
                message = f'Atrybut {attribute_name} nie był przypisany do produktu {product.name}'

        logger.info(f"Zarządzanie atrybutami produktu: {message}")

        return JsonResponse({
            'status': 'success',
            'message': message,
            'product_id': product_id,
            'action': action
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format JSON'}, status=400)
    except Exception as e:
        logger.error(f"Błąd podczas zarządzania atrybutami produktu: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Błąd serwera'}, status=500)


@csrf_exempt
def create_product(request):
    """
    Endpoint do tworzenia nowego produktu w MPD
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Tylko metoda POST jest obsługiwana'}, status=405)

    try:
        data = json.loads(request.body)

        # Wymagane pola
        name = data.get('name')
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Nazwa produktu jest wymagana'}, status=400)

        # Opcjonalne pola
        description = data.get('description', '')
        short_description = data.get('short_description', '')
        brand_id = data.get('brand_id')
        unit_id = data.get('unit_id')
        series_id = data.get('series_id')
        visibility = data.get('visibility', True)

        # Utwórz produkt
        product = Products.objects.using('MPD').create(
            name=name,
            description=description,
            short_description=short_description,
            brand_id=brand_id,
            unit_id=unit_id,
            series_id=series_id,
            visibility=visibility
        )

        # Dodaj warianty jeśli podano
        variants = data.get('variants', [])
        created_variants = []

        for variant_data in variants:
            from .models import ProductVariants, Colors
            from .models import ProductVariantsRetailPrice

            # Pobierz lub utwórz kolor
            color_id = variant_data.get('color_id')
            producer_color_id = variant_data.get('producer_color_id')

            if variant_data.get('producer_color_name'):
                producer_color, _ = Colors.objects.using('MPD').get_or_create(
                    name=variant_data['producer_color_name']
                )
                producer_color_id = producer_color.id

            # Pobierz rozmiar
            size_id = variant_data.get('size_id')

            # Utwórz wariant
            variant = ProductVariants.objects.using('MPD').create(
                product=product,
                color_id=color_id,
                producer_color_id=producer_color_id,
                size_id=size_id,
            )

            # Dodaj cenę jeśli podano
            if variant_data.get('price'):
                ProductVariantsRetailPrice.objects.using('MPD').create(
                    variant=variant,
                    retail_price=variant_data['price'],
                    vat=variant_data.get('vat', 23.0),
                    currency=variant_data.get('currency', 'PLN'),
                    net_price=variant_data.get('net_price')
                )

            created_variants.append(variant.variant_id)

        # Dodaj ścieżki jeśli podano
        path_ids = data.get('path_ids', [])
        for path_id in path_ids:
            ProductPaths.objects.using('MPD').create(
                product_id=product.id,
                path_id=path_id
            )

        # Dodaj atrybuty jeśli podano
        attribute_ids = data.get('attribute_ids', [])
        for attribute_id in attribute_ids:
            ProductAttribute.objects.using('MPD').create(
                product=product,
                attribute_id=attribute_id
            )

        # Task linkowania - sygnał MPD (ProductvariantsSources post_save) gdy dodano źródła
        logger.info("Utworzono produkt MPD: %s (ID: %s)",
                    product.name, product.id)

        return JsonResponse({
            'status': 'success',
            'message': 'Produkt został utworzony pomyślnie',
            'product_id': product.id,
            'product_name': product.name,
            'variants_created': len(created_variants),
            'variants': created_variants
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format JSON'}, status=400)
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia produktu MPD: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Błąd serwera: {str(e)}'}, status=500)


@csrf_exempt
def update_product(request, product_id):
    """
    Endpoint do aktualizacji produktu w MPD
    """
    if request.method not in ['PUT', 'PATCH']:
        return JsonResponse({'status': 'error', 'message': 'Tylko metody PUT/PATCH są obsługiwane'}, status=405)

    try:
        data = json.loads(request.body)

        # Sprawdź czy produkt istnieje
        try:
            product = Products.objects.using('MPD').get(id=product_id)
        except Products.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Produkt nie istnieje'}, status=404)

        # Aktualizuj podstawowe pola produktu
        if 'name' in data:
            product.name = data['name']
        if 'description' in data:
            product.description = data['description']
        if 'short_description' in data:
            product.short_description = data['short_description']
        if 'brand_id' in data:
            product.brand_id = data['brand_id']
        if 'unit_id' in data:
            product.unit_id = data['unit_id']
        if 'series_id' in data:
            product.series_id = data['series_id']
        if 'visibility' in data:
            product.visibility = data['visibility']

        product.save(using='MPD')

        # Aktualizuj ścieżki jeśli podano
        if 'path_ids' in data:
            # Usuń istniejące ścieżki
            ProductPaths.objects.using('MPD').filter(
                product_id=product_id).delete()
            # Dodaj nowe
            for path_id in data['path_ids']:
                ProductPaths.objects.using('MPD').create(
                    product_id=product_id,
                    path_id=path_id
                )

        # Aktualizuj atrybuty jeśli podano
        if 'attribute_ids' in data:
            # Usuń istniejące atrybuty
            ProductAttribute.objects.using('MPD').filter(
                product_id=product_id).delete()
            # Dodaj nowe
            for attribute_id in data['attribute_ids']:
                ProductAttribute.objects.using('MPD').create(
                    product_id=product_id,
                    attribute_id=attribute_id
                )

        # Aktualizuj warianty jeśli podano
        if 'variants' in data:
            # Usuń istniejące warianty
            ProductVariants.objects.using('MPD').filter(
                product_id=product_id).delete()

            # Dodaj nowe warianty
            for variant_data in data['variants']:
                # Pobierz lub utwórz kolor
                color_id = variant_data.get('color_id')
                producer_color_id = variant_data.get('producer_color_id')

                if variant_data.get('producer_color_name'):
                    producer_color, _ = Colors.objects.using('MPD').get_or_create(
                        name=variant_data['producer_color_name']
                    )
                    producer_color_id = producer_color.id

                # Pobierz rozmiar
                size_id = variant_data.get('size_id')

                # Utwórz wariant
                variant = ProductVariants.objects.using('MPD').create(
                    product=product,
                    color_id=color_id,
                    producer_color_id=producer_color_id,
                    size_id=size_id,
                )

                # Dodaj cenę jeśli podano
                if variant_data.get('price'):
                    ProductVariantsRetailPrice.objects.using('MPD').create(
                        variant=variant,
                        retail_price=variant_data['price'],
                        vat=variant_data.get('vat', 23.0),
                        currency=variant_data.get('currency', 'PLN'),
                        net_price=variant_data.get('net_price')
                    )

        logger.info("Zaktualizowano produkt MPD: %s (ID: %s)",
                    product.name, product.id)

        return JsonResponse({
            'status': 'success',
            'message': 'Produkt został zaktualizowany pomyślnie',
            'product_id': product.id,
            'product_name': product.name
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format JSON'}, status=400)
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji produktu MPD: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Błąd serwera: {str(e)}'}, status=500)


@csrf_exempt
def get_product(request, product_id):
    """
    Endpoint do pobierania danych produktu z MPD
    """
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Tylko metoda GET jest obsługiwana'}, status=405)

    try:
        # Sprawdź czy produkt istnieje
        try:
            product = Products.objects.using('MPD').get(id=product_id)
        except Products.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Produkt nie istnieje'}, status=404)

        # Pobierz warianty
        variants = []
        for variant in product.productvariants_set.all():
            first_pvs = ProductvariantsSources.objects.using('MPD').filter(
                variant_id=variant.variant_id
            ).values_list('producer_code', flat=True).first()
            variant_data = {
                'variant_id': variant.variant_id,
                'color_id': variant.color_id,
                'producer_color_id': variant.producer_color_id,
                'size_id': variant.size_id,
                'producer_code': first_pvs or '',
                'exported_to_iai': variant.exported_to_iai
            }

            # Pobierz cenę jeśli istnieje
            try:
                price = variant.productvariantsretailprice
                variant_data['price'] = {
                    'retail_price': float(price.retail_price) if price.retail_price else None,
                    'vat': float(price.vat) if price.vat else None,
                    'currency': price.currency,
                    'net_price': float(price.net_price) if price.net_price else None
                }
            except Exception:
                variant_data['price'] = None

            variants.append(variant_data)

        # Pobierz ścieżki
        paths = list(ProductPaths.objects.using('MPD').filter(
            product_id=product_id).values_list('path_id', flat=True))

        # Pobierz atrybuty
        attributes = list(ProductAttribute.objects.using('MPD').filter(
            product_id=product_id).values_list('attribute_id', flat=True))

        return JsonResponse({
            'status': 'success',
            'product': {
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'short_description': product.short_description,
                'brand_id': product.brand_id,
                'unit_id': product.unit_id,
                'series_id': product.series_id,
                'visibility': product.visibility,
                'created_at': product.created_at.isoformat() if product.created_at else None,
                'updated_at': product.updated_at.isoformat() if product.updated_at else None,
                'variants': variants,
                'paths': paths,
                'attributes': attributes
            }
        })

    except Exception as e:
        logger.error(f"Błąd podczas pobierania produktu MPD: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Błąd serwera: {str(e)}'}, status=500)


@csrf_exempt
def bulk_create_products(request):
    """
    Endpoint do bulk tworzenia produktów w MPD
    """
    logger.info("🚀 MPD bulk_create_products: Rozpoczynam przetwarzanie")

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Tylko metoda POST jest obsługiwana'}, status=405)

    try:
        logger.info("📥 MPD bulk_create_products: Parsuję dane JSON")
        data = json.loads(request.body)
        products_data = data.get('products', [])

        if not products_data:
            logger.warning(
                "⚠️ MPD bulk_create_products: Brak danych produktów")
            return JsonResponse({'status': 'error', 'message': 'Brak danych produktów'}, status=400)

        logger.info(
            f"📊 MPD bulk_create_products: Przetwarzam {len(products_data)} produktów")

        created_products = []
        errors = []

        for i, product_data in enumerate(products_data, 1):
            try:
                logger.info(
                    f"🔄 MPD bulk_create_products: Przetwarzam produkt {i}/{len(products_data)}: {product_data.get('name', 'Unknown')}")

                # Wymagane pola
                name = product_data.get('name')
                matterhorn_product_id = product_data.get('matterhorn_product_id')
                if not name:
                    logger.warning(
                        f"⚠️ MPD bulk_create_products: Brak nazwy produktu {i}")
                    errors.append("Brak nazwy produktu")
                    continue

                # KROK 6: Nazwa + Opis + Krótki opis + Atrybuty + Marka + Grupa rozmiarowa + Series + Jednostka
                description = product_data.get('description', '')
                short_description = product_data.get(
                    'short_description', '')
                brand_name = product_data.get('brand_name', '')
                series_name = product_data.get('series_name', '')
                unit_id = product_data.get('unit_id')
                visibility = product_data.get('visibility', True)

                # Debug: sprawdź unit_id
                logger.info(
                    f"MPD bulk_create: unit_id={unit_id} (type: {type(unit_id)})")

                # Pobierz lub utwórz markę
                brand_id = None
                if brand_name:
                    brand, _ = Brands.objects.using(
                        'MPD').get_or_create(name=brand_name)
                    brand_id = brand.id

                # Pobierz lub utwórz series
                series_id = None
                if series_name:
                    from MPD.models import ProductSeries
                    series, _ = ProductSeries.objects.using(
                        'MPD').get_or_create(name=series_name)
                    series_id = series.id

                # Utwórz produkt z nazwą, opisem, krótkim opisem, marką, series i jednostką
                logger.info(
                    "💾 MPD bulk_create_products: Tworzę produkt w bazie danych")
                product = Products.objects.using('MPD').create(
                    name=name,
                    description=description or '',
                    short_description=short_description or '',
                    brand_id=brand_id,
                    unit_id=unit_id,
                    series_id=series_id,
                    visibility=visibility
                )
                logger.info(
                    f"✅ MPD bulk_create_products: Utworzono produkt {product.id}")

                # Debug: sprawdź zapisany produkt
                logger.info(
                    f"Created product {product.id} with unit_id={product.unit_id}")

                # Warianty wyłączone na razie
                created_variants = []

                created_products.append({
                    'id': product.id,
                    'mpd_product_id': product.id,
                    'matterhorn_product_id': matterhorn_product_id,
                    'name': product.name,
                    'variants': created_variants
                })

            except Exception as e:
                errors.append(
                    f"Błąd tworzenia produktu {product_data.get('name', 'Unknown')}: {str(e)}")
                continue

        logger.info("🏁 MPD bulk_create_products: Zakończono przetwarzanie")
        logger.info(
            f"📊 MPD bulk_create_products: Wynik - utworzono={len(created_products)}, błędy={len(errors)}")
        logger.info(
            f"✅ MPD bulk_create_products: Utworzone produkty: {created_products}")
        if errors:
            logger.warning(f"❌ MPD bulk_create_products: Błędy: {errors}")

        return JsonResponse({
            'status': 'success',
            'created_products': created_products,
            'errors': errors,
            'total_created': len(created_products)
        })

    except Exception as e:
        logger.error(f"❌ MPD bulk_create_products: Błąd: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def bulk_map_from_matterhorn1(request):
    """
    Endpoint do bulk mapowania produktów z matterhorn1 do MPD
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Tylko metoda POST jest obsługiwana'}, status=405)

    try:
        data = json.loads(request.body)
        products_data = data.get('products', [])

        if not products_data:
            return JsonResponse({'status': 'error', 'message': 'Brak danych produktów'}, status=400)

        # Importuj modele matterhorn1
        from matterhorn1.models import Product as MatterhornProduct

        created_products = []
        errors = []

        with transaction.atomic():
            for product_data in products_data:
                try:
                    matterhorn_product_id = product_data.get(
                        'matterhorn_product_id')
                    if not matterhorn_product_id:
                        errors.append(
                            {'error': 'Brak matterhorn_product_id', 'data': product_data})
                        continue

                    # Pobierz produkt z matterhorn1
                    try:
                        matterhorn_product = MatterhornProduct.objects.get(
                            product_uid=matterhorn_product_id)
                    except MatterhornProduct.DoesNotExist:
                        errors.append(
                            {'error': f'Produkt matterhorn1 o ID {matterhorn_product_id} nie istnieje', 'data': product_data})
                        continue

                    # Sprawdź czy marka istnieje w MPD, jeśli nie - utwórz
                    brand = None
                    if matterhorn_product.brand:
                        brand, created = Brands.objects.using('MPD').get_or_create(
                            name=matterhorn_product.brand.name,
                            defaults={
                                'logo_url': '',
                                'opis': '',
                                'url': '',
                                'iai_brand_id': None
                            }
                        )
                        if created:
                            logger.info(
                                f"Utworzono nową markę w MPD: {brand.name}")

                    # Utwórz produkt w MPD
                    mpd_product = Products.objects.using('MPD').create(
                        name=product_data.get('name', matterhorn_product.name),
                        description=product_data.get(
                            'description', matterhorn_product.description),
                        short_description=product_data.get(
                            'short_description', ''),
                        brand=brand,
                        visibility=product_data.get('visibility', True)
                    )

                    # Zaktualizuj mapped_product_uid w matterhorn1
                    matterhorn_product.mapped_product_uid = mpd_product.id
                    matterhorn_product.save()

                    # Utwórz warianty jeśli istnieją
                    created_variants = []
                    for variant_data in product_data.get('variants', []):
                        # Pobierz lub utwórz kolor
                        color = None
                        if variant_data.get('color_name'):
                            color, created = Colors.objects.using('MPD').get_or_create(
                                name=variant_data['color_name'],
                                defaults={
                                    'hex_code': variant_data.get('hex_code', '')}
                            )

                        # Pobierz rozmiar
                        size = None
                        if variant_data.get('size_name'):
                            size, created = Sizes.objects.using('MPD').get_or_create(
                                name=variant_data['size_name'],
                                defaults={'category': 'default'}
                            )

                        # Utwórz wariant
                        variant = ProductVariants.objects.using('MPD').create(
                            product=mpd_product,
                            color=color,
                            size=size,
                        )

                        # Dodaj cenę jeśli podano
                        if variant_data.get('price'):
                            ProductVariantsRetailPrice.objects.using('MPD').create(
                                variant=variant,
                                retail_price=variant_data['price'],
                                vat=variant_data.get('vat', 23.0),
                                currency=variant_data.get('currency', 'PLN'),
                                net_price=variant_data.get('net_price')
                            )

                        created_variants.append(variant.variant_id)

                    # Dodaj ścieżki jeśli podano
                    for path_id in product_data.get('path_ids', []):
                        ProductPaths.objects.using('MPD').create(
                            product_id=mpd_product.id,
                            path_id=path_id
                        )

                    # Dodaj atrybuty jeśli podano
                    for attribute_id in product_data.get('attribute_ids', []):
                        ProductAttribute.objects.using('MPD').create(
                            product_id=mpd_product.id,
                            attribute_id=attribute_id
                        )

                    created_products.append({
                        'mpd_product_id': mpd_product.id,
                        'matterhorn_product_id': matterhorn_product_id,
                        'name': mpd_product.name,
                        'variants_created': len(created_variants)
                    })
                    # Task linkowania - sygnał MPD gdy bulk_map doda ProductvariantsSources

                except Exception as e:
                    errors.append({
                        'error': f'Błąd podczas tworzenia produktu: {str(e)}',
                        'data': product_data
                    })
                    logger.error(f"Błąd podczas mapowania produktu: {str(e)}")

        logger.info(
            f"Zamapowano {len(created_products)} produktów z matterhorn1 do MPD")

        return JsonResponse({
            'status': 'success',
            'message': f'Zamapowano {len(created_products)} produktów',
            'created_products': created_products,
            'errors': errors,
            'total_processed': len(products_data),
            'success_count': len(created_products),
            'error_count': len(errors)
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy format JSON'}, status=400)
    except Exception as e:
        logger.error(f"Błąd podczas bulk mapowania produktów: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Błąd serwera: {str(e)}'}, status=500)


@csrf_exempt
def get_matterhorn1_products(request):
    """
    Endpoint do pobierania produktów z matterhorn1 do mapowania
    """
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Tylko metoda GET jest obsługiwana'}, status=405)

    try:
        # Importuj modele matterhorn1
        from matterhorn1.models import Product as MatterhornProduct

        # Pobierz parametry
        search = request.GET.get('search', '')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))

        # Pobierz produkty
        products = MatterhornProduct.objects.select_related(
            'brand', 'category').all()

        # Filtruj jeśli podano wyszukiwanie
        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(brand__name__icontains=search) |
                Q(category__name__icontains=search)
            )

        # Paginacja
        from django.core.paginator import Paginator
        paginator = Paginator(products, per_page)
        page_obj = paginator.get_page(page)

        # Przygotuj dane
        products_data = []
        for product in page_obj:
            # Pobierz warianty
            variants = []
            for variant in product.variants.all():
                variants.append({
                    'variant_uid': variant.variant_uid,
                    'name': variant.name,
                    'stock': variant.stock,
                    'ean': variant.ean
                })

            # Pobierz obrazy
            images = []
            for image in product.images.all():
                images.append({
                    'image_url': resolve_image_url(image.file_path) or image.file_path
                })

            products_data.append({
                'product_id': product.product_id,
                'name': product.name,
                'description': product.description,
                'active': product.active,
                'color': product.color,
                'new_collection': product.new_collection,
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
                'mapped_product_uid': product.mapped_product_uid
            })

        return JsonResponse({
            'status': 'success',
            'products': products_data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_products': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })

    except Exception as e:
        logger.error(
            f"Błąd podczas pobierania produktów matterhorn1: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Błąd serwera: {str(e)}'}, status=500)


@csrf_exempt
def update_producer_code(request):
    """
    Endpoint do aktualizacji kodu producenta wariantu
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Tylko metoda POST jest obsługiwana'}, status=405)

    try:
        data = json.loads(request.body)
        variant_id = data.get('variant_id')
        producer_code = data.get('producer_code', '')

        if not variant_id:
            return JsonResponse({'status': 'error', 'message': 'Brak variant_id'}, status=400)

        # Znajdź wariant (sprawdzenie istnienia przez .get)
        try:
            ProductVariants.objects.using('MPD').get(variant_id=variant_id)
        except ProductVariants.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Wariant nie istnieje'}, status=404)

        # Aktualizuj kod producenta w product_variants_sources (wszystkie źródła tego wariantu)
        ProductvariantsSources.objects.using('MPD').filter(
            variant_id=variant_id
        ).update(producer_code=producer_code[:255] if producer_code else None)

        logger.info(
            f"Zaktualizowano kod producenta dla wariantu {variant_id}: {producer_code}")

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
