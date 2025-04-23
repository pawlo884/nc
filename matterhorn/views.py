from django.db import connections
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Products
from django.core.paginator import Paginator
from .defs_import import add_new_product_to_matterhorn, export_to_products
from .models import ProductsProxy
from django.contrib import messages
from django.db import transaction


# Create your views here.
def home(request):
    return render(request, 'home.html', {'name': 'Matterhorn'})


def about(request):
    return render(request, 'about.html', {'name': 'about'})


def products(request):
    product_list = Products.objects.all().order_by('-id')

    # Filtrowanie na podstawie pól
    filters = {
        'id': request.GET.get('id'),
        'active': request.GET.get('active'),
        'name': request.GET.get('name'),
        'description': request.GET.get('description'),
        'creation_date': request.GET.get('creation_date'),
        'color': request.GET.get('color'),
        'category_name': request.GET.get('category_name'),
        'category_id': request.GET.get('category_id'),
        'category_path': request.GET.get('category_path'),
        'brand_id': request.GET.get('brand_id'),
        'brand': request.GET.get('brand'),
        'stock_total': request.GET.get('stock_total'),
        'url': request.GET.get('url'),
        'new_collection': request.GET.get('new_collection'),
        'size_table': request.GET.get('size_table'),
        'weight': request.GET.get('weight'),
        'size_table_txt': request.GET.get('size_table_txt'),
        'size_table_html': request.GET.get('size_table_html'),
        'price': request.GET.get('price'),
    }

    for key, value in filters.items():
        if value:
            product_list = product_list.filter(**{f"{key}__icontains": value})

    paginator = Paginator(product_list, 100)  # Show 100 products per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'products.html', {'page_obj': page_obj})


def edit_product(request, product_id):
    product = get_object_or_404(Products, id=product_id)
    if request.method == 'POST':
        product.active = request.POST.get('active')
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.creation_date = request.POST.get('creation_date')
        product.color = request.POST.get('color')
        product.category_name = request.POST.get('category_name')
        product.category_id = request.POST.get('category_id')
        product.category_path = request.POST.get('category_path')
        product.brand_id = request.POST.get('brand_id')
        product.brand = request.POST.get('brand')
        product.stock_total = request.POST.get('stock_total')
        product.url = request.POST.get('url')
        product.new_collection = request.POST.get('new_collection')
        product.size_table = request.POST.get('size_table')
        product.weight = request.POST.get('weight')
        product.size_table_txt = request.POST.get('size_table_txt')
        product.size_table_html = request.POST.get('size_table_html')
        price = request.POST.get('price')
        if price:
            price = price.replace(',', '.')
        product.price = price
        product.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


def add_new_product(request):
    # Sprawdź strefę czasową bazy danych
    with connections['matterhorn'].cursor() as cursor:
        cursor.execute("SHOW timezone;")
        db_timezone = cursor.fetchone()[0]
        print(f"Strefa czasowa bazy danych: {db_timezone}")
        
        cursor.execute("SELECT current_timestamp;")
        db_time = cursor.fetchone()[0]
        print(f"Aktualny czas w bazie danych: {db_time}")

    # Pobierz `product_id` z żądania
    product_id = request.GET.get('product_id')
    referrer = request.GET.get('referrer', '/')
    manual_confirm = request.GET.get('manual_confirm')
    confirmed_product_id = request.GET.get('confirmed_product_id')

    if product_id:
        # Pobierz produkt na podstawie `product_id`
        product = ProductsProxy.objects.filter(id=product_id).first()

        with connections["MPD"].cursor() as destination_cursor, connections["matterhorn"].cursor() as source_cursor:

            if confirmed_product_id:
                # Jeśli jest podany confirmed_product_id, aktualizuj istniejący produkt
                source_cursor.execute("""
                    UPDATE products 
                    SET mapped_product_id = %s,
                        last_updated = CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Warsaw'
                    WHERE id = %s;
                    
                    SELECT last_updated 
                    FROM products 
                    WHERE id = %s;
                """, (confirmed_product_id, product_id, product_id))
                
                new_time = source_cursor.fetchone()[0]
                print(f"Nowy czas last_updated: {new_time}")
                
                connections["matterhorn"].commit()
                messages.success(request, f"Produkt {product.name} przypisany do ID {confirmed_product_id}.")
            elif manual_confirm:
                # Jeśli jest manual_confirm, dodaj jako nowy produkt
                add_new_product_to_matterhorn(destination_cursor, source_cursor, product, request)
            else:
                # Sprawdź automatyczne przypisanie lub utwórz nowe
                export_to_products(None, request, [product])

    # Przekieruj do właściwej strony po zakończeniu
    return redirect(referrer)