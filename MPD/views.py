from django.shortcuts import render
from .models import Products, Brands, ProductSet, ProductSetItem
from django.http import JsonResponse
from django.db import connections
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

# Create your views here.

def products(request):
    products = Products.objects.all()
    
    # Pobierz warianty, stany magazynowe i ceny dla każdego produktu
    for product in products:
        with connections['MPD'].cursor() as cursor:
            cursor.execute("""
                SELECT 
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
                WHERE pv.product_id = %s
                ORDER BY s.name, c.name
            """, [product.id])
            variants = cursor.fetchall()
            setattr(product, 'variants', [{
                'variant_id': row[0],
                'size_id': row[1],
                'size_name': row[2],
                'color_id': row[3],
                'color_name': row[4],
                'hex_code': row[5],
                'stock': row[6],
                'price': row[7]
            } for row in variants])
    
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
            item = ProductSetItem.objects.create(
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