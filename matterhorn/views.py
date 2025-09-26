from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Products
from django.core.paginator import Paginator


# Create your views here.
def home(request):
    return render(request, 'home.html', {'name': 'Matterhorn'})


def about(request):
    return render(request, 'about.html', {'name': 'about'})


def products(request):
    product_list = Products.objects.select_related().prefetch_related(
        'images', 'variants', 'other_colors').order_by('-id')

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
