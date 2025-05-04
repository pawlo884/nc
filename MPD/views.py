from django.shortcuts import render
from .models import Products, Brands
from django.http import JsonResponse
from django.db import connections
# Create your views here.

def products(request):
    products = Products.objects.all()
    
    # Pobierz warianty, stany magazynowe i ceny dla każdego produktu
    for product in products:
        with connections['MPD'].cursor() as cursor:
            cursor.execute("""
                SELECT pv.variant_id, pv.size_id, s.name as size_name, sp.stock, sp.price
                FROM product_variants pv
                JOIN sizes s ON pv.size_id = s.id
                LEFT JOIN stock_and_prices sp ON pv.variant_id = sp.variant_id AND sp.source_id = 2
                WHERE pv.product_id = %s
                ORDER BY s.name
            """, [product.id])
            variants = cursor.fetchall()
            setattr(product, 'variants', [{
                'variant_id': row[0],
                'size_id': row[1],
                'size_name': row[2],
                'stock': row[3],
                'price': row[4]
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