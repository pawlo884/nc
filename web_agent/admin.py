"""
Konfiguracja admin dla aplikacji web_agent.
"""
from django.contrib import admin
from django import forms
from django.urls import path, reverse
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils.html import format_html
from django.core.management import call_command
from .models import AutomationRun, ProductProcessingLog, BrandConfig, ProducerColor
from matterhorn1.models import Brand, Category
import threading
import logging

logger = logging.getLogger(__name__)


class AutomationRunForm(forms.ModelForm):
    """Custom form z dropdownami dla marki i kategorii"""

    brand_name = forms.ChoiceField(
        required=False,
        label='Marka',
        help_text='Wybierz markę z listy',
        choices=[('', '---------')]
    )

    category_name = forms.ChoiceField(
        required=False,
        label='Kategoria',
        help_text='Wybierz kategorię z listy',
        choices=[('', '---------')]
    )

    active_filter = forms.ChoiceField(
        required=False,
        label='Filtr Active',
        choices=[
            ('', '---------'),
            ('true', 'Tak'),
            ('false', 'Nie'),
        ],
        help_text='Filtruj produkty aktywne'
    )

    is_mapped_filter = forms.ChoiceField(
        required=False,
        label='Filtr Is Mapped',
        choices=[
            ('', '---------'),
            ('true', 'Tak'),
            ('false', 'Nie'),
        ],
        help_text='Filtruj produkty zmapowane do MPD'
    )

    max_products = forms.IntegerField(
        required=False,
        initial=1,
        min_value=1,
        max_value=100,
        label='Maksymalna liczba produktów',
        help_text='Ile produktów przetworzyć (1-100)'
    )

    automation_type = forms.ChoiceField(
        required=True,
        label='Typ automatyzacji',
        choices=[
            ('browser', 'Z przeglądarką (Selenium)'),
            ('background', 'W tle (bez przeglądarki)'),
        ],
        initial='background',
        help_text='Wybierz typ automatyzacji'
    )

    class Meta:
        model = AutomationRun
        fields = ['status', 'brand_id', 'category_id', 'filters']
        widgets = {
            'brand_id': forms.HiddenInput(),
            'category_id': forms.HiddenInput(),
            'filters': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pobierz dostępne marki
        try:
            brands = Brand.objects.all().order_by('name')
            brand_choices = [('', '---------')] + \
                [(brand.name, brand.name) for brand in brands]
            self.fields['brand_name'].choices = brand_choices

            # Ustaw aktualną wartość jeśli istnieje
            if self.instance and self.instance.brand_id:
                try:
                    brand = Brand.objects.get(brand_id=self.instance.brand_id)
                    self.fields['brand_name'].initial = brand.name
                except Brand.DoesNotExist:  # noqa: F841
                    pass
        except Exception:  # noqa: F841
            self.fields['brand_name'].choices = [('', 'Błąd pobierania marek')]

        # Pobierz dostępne kategorie
        try:
            categories = Category.objects.all().order_by('name')
            category_choices = [('', '---------')] + \
                [(cat.name, cat.name) for cat in categories]
            self.fields['category_name'].choices = category_choices

            # Ustaw aktualną wartość jeśli istnieje
            if self.instance and self.instance.category_id:
                try:
                    category = Category.objects.get(
                        category_id=self.instance.category_id)
                    self.fields['category_name'].initial = category.name
                except Category.DoesNotExist:  # noqa: F841
                    pass
        except Exception:  # noqa: F841
            self.fields['category_name'].choices = [
                ('', 'Błąd pobierania kategorii')]

        # Ustaw wartości filtrów z JSON
        if self.instance and self.instance.filters:
            filters = self.instance.filters
            if 'active' in filters:
                self.fields['active_filter'].initial = 'true' if filters['active'] else 'false'
            if 'is_mapped' in filters:
                self.fields['is_mapped_filter'].initial = 'true' if filters['is_mapped'] else 'false'


@admin.register(AutomationRun)
class AutomationRunAdmin(admin.ModelAdmin):
    """Admin dla AutomationRun z możliwością uruchomienia automatyzacji"""
    form = AutomationRunForm
    list_display = [
        'id', 'started_at', 'completed_at', 'status',
        'products_processed', 'products_success', 'products_failed',
        'get_brand_name', 'get_category_name'
    ]
    list_filter = ['status', 'started_at', 'brand_id', 'category_id']
    search_fields = ['id', 'error_message']
    readonly_fields = ['started_at', 'completed_at', 'run_automation_button']
    date_hierarchy = 'started_at'

    fieldsets = (
        ('Uruchomienie automatyzacji', {
            'fields': ('run_automation_button',),
            'description': 'Użyj przycisku poniżej, aby uruchomić automatyzację z wybranymi parametrami'
        }),
        ('Parametry automatyzacji', {
            'fields': (
                'automation_type', 'brand_name', 'category_name',
                'active_filter', 'is_mapped_filter', 'max_products'
            ),
            'description': 'Wybierz parametry dla automatyzacji'
        }),
        ('Podstawowe informacje', {
            'fields': ('status', 'started_at', 'completed_at')
        }),
        ('Statystyki', {
            'fields': ('products_processed', 'products_success', 'products_failed')
        }),
        ('Filtry (techniczne)', {
            'fields': ('brand_id', 'category_id', 'filters'),
            'classes': ('collapse',)
        }),
        ('Błędy', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

    def get_brand_name(self, obj):
        """Wyświetl nazwę marki zamiast ID"""
        if obj.brand_id:
            try:
                brand = Brand.objects.get(brand_id=obj.brand_id)
                return brand.name
            except Brand.DoesNotExist:
                return f"ID: {obj.brand_id}"
        return "-"
    get_brand_name.short_description = 'Marka'

    def get_category_name(self, obj):
        """Wyświetl nazwę kategorii zamiast ID"""
        if obj.category_id:
            try:
                category = Category.objects.get(category_id=obj.category_id)
                return category.name
            except Category.DoesNotExist:
                return f"ID: {obj.category_id}"
        return "-"
    get_category_name.short_description = 'Kategoria'

    def run_automation_button(self, obj):
        """Przycisk do uruchomienia automatyzacji (tylko w widoku szczegółów)"""
        if obj.pk:
            url = reverse('admin:web_agent_automationrun_run', args=[obj.pk])
            return format_html(
                '''
                <button type="button" onclick="runAutomationFromForm({}, '{}')" 
                        class="button" 
                        style="background-color: #417690; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer;">
                    🚀 Uruchom automatyzację
                </button>
                <script>
                function runAutomationFromForm(runId, url) {{
                    // Pobierz wartości z formularza
                    var brandName = document.getElementById('id_brand_name') ? document.getElementById('id_brand_name').value : '';
                    var categoryName = document.getElementById('id_category_name') ? document.getElementById('id_category_name').value : '';
                    var activeFilter = document.getElementById('id_active_filter') ? document.getElementById('id_active_filter').value : '';
                    var isMappedFilter = document.getElementById('id_is_mapped_filter') ? document.getElementById('id_is_mapped_filter').value : '';
                    var maxProducts = document.getElementById('id_max_products') ? document.getElementById('id_max_products').value : '1';
                    var automationType = document.getElementById('id_automation_type') ? document.getElementById('id_automation_type').value : 'background';
                    
                    // Utwórz formularz i wyślij POST
                    var form = document.createElement('form');
                    form.method = 'POST';
                    form.action = url;
                    
                    // Dodaj CSRF token
                    var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
                    if (csrfToken) {{
                        var csrfInput = document.createElement('input');
                        csrfInput.type = 'hidden';
                        csrfInput.name = 'csrfmiddlewaretoken';
                        csrfInput.value = csrfToken.value;
                        form.appendChild(csrfInput);
                    }}
                    
                    // Dodaj parametry
                    var params = [
                        ['brand_name', brandName],
                        ['category_name', categoryName],
                        ['active_filter', activeFilter],
                        ['is_mapped_filter', isMappedFilter],
                        ['max_products', maxProducts],
                        ['automation_type', automationType]
                    ];
                    
                    params.forEach(function(pair) {{
                        if (pair[1]) {{
                            var input = document.createElement('input');
                            input.type = 'hidden';
                            input.name = pair[0];
                            input.value = pair[1];
                            form.appendChild(input);
                        }}
                    }});
                    
                    document.body.appendChild(form);
                    form.submit();
                }}
                </script>
                ''',
                obj.pk,
                url
            )
        return "Zapisz najpierw, aby uruchomić automatyzację"
    run_automation_button.short_description = 'Akcja'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:automation_run_id>/run/',
                self.admin_site.admin_view(self.run_automation),
                name='web_agent_automationrun_run',
            ),
            path(
                'run-automation/',
                self.admin_site.admin_view(self.run_automation_form),
                name='web_agent_automationrun_run_form',
            ),
        ]
        return custom_urls + urls

    def run_automation(self, request, automation_run_id):
        """Uruchom automatyzację dla wybranego AutomationRun"""
        if request.method != 'POST':
            messages.error(request, 'Metoda POST wymagana')
            return redirect('admin:web_agent_automationrun_change', automation_run_id)

        try:
            automation_run = AutomationRun.objects.get(id=automation_run_id)

            # Pobierz parametry z formularza (POST)
            brand_name = request.POST.get('brand_name', '')
            category_name = request.POST.get('category_name', '')
            active_filter = request.POST.get('active_filter', '')
            is_mapped_filter = request.POST.get('is_mapped_filter', '')
            max_products = request.POST.get('max_products', '1')
            automation_type = request.POST.get('automation_type', 'background')

            # Przygotuj argumenty dla management command
            command_args = {}
            if brand_name:
                command_args['brand'] = brand_name
            if category_name:
                command_args['category'] = category_name
            if active_filter:
                command_args['active'] = active_filter
            if is_mapped_filter:
                command_args['is_mapped'] = is_mapped_filter
            if max_products:
                command_args['max'] = int(max_products)

            # Uruchom komendę w tle
            def run_command():
                try:
                    if automation_type == 'background':
                        call_command('run_background_automation',
                                     **command_args)
                    else:
                        call_command('run_automation', **command_args)
                except Exception as e:
                    logger.error(
                        "Błąd podczas uruchamiania automatyzacji: %s", str(e))
                    try:
                        automation_run.refresh_from_db()
                        automation_run.status = 'failed'
                        automation_run.error_message = str(e)
                        automation_run.save()
                    except Exception:
                        pass

            thread = threading.Thread(target=run_command)
            thread.daemon = True
            thread.start()

            messages.success(
                request,
                f'Automatyzacja została uruchomiona w tle (typ: {automation_type}). '
                f'Sprawdź status w AutomationRun #{automation_run_id}'
            )

        except AutomationRun.DoesNotExist:
            messages.error(request, 'Nie znaleziono AutomationRun')
        except Exception as e:
            messages.error(request, f'Błąd: {str(e)}')
            logger.error("Błąd w run_automation: %s", str(e))

        return redirect('admin:web_agent_automationrun_change', automation_run_id)

    def run_automation_form(self, request):
        """Widok z formularzem do uruchomienia automatyzacji"""
        if request.method == 'POST':
            # Pobierz parametry z formularza
            brand_name = request.POST.get('brand_name', '')
            category_name = request.POST.get('category_name', '')
            active_filter = request.POST.get('active_filter', '')
            is_mapped_filter = request.POST.get('is_mapped_filter', '')
            max_products = request.POST.get('max_products', '1')
            automation_type = request.POST.get('automation_type', 'background')

            # Utwórz nowy AutomationRun
            automation_run = AutomationRun.objects.create(
                status='running',
                products_processed=0,
                products_success=0,
                products_failed=0
            )

            # Ustaw brand_id i category_id
            if brand_name:
                try:
                    brand = Brand.objects.get(name=brand_name)
                    automation_run.brand_id = int(brand.brand_id)
                except Brand.DoesNotExist:
                    pass

            if category_name:
                try:
                    category = Category.objects.filter(
                        name__icontains=category_name).first()
                    if category:
                        automation_run.category_id = int(category.category_id)
                except Exception:
                    pass

            # Ustaw filtry
            filters = {}
            if active_filter:
                filters['active'] = active_filter.lower() in (
                    'true', '1', 'yes', 'tak')
            if is_mapped_filter:
                filters['is_mapped'] = is_mapped_filter.lower() in (
                    'true', '1', 'yes', 'tak')
            automation_run.filters = filters
            automation_run.save()

            # Przygotuj argumenty dla management command
            command_args = {}
            if brand_name:
                command_args['brand'] = brand_name
            if category_name:
                command_args['category'] = category_name
            if active_filter:
                command_args['active'] = active_filter
            if is_mapped_filter:
                command_args['is_mapped'] = is_mapped_filter
            if max_products:
                command_args['max'] = int(max_products)

            # Uruchom komendę w tle
            def run_command():
                try:
                    if automation_type == 'background':
                        call_command('run_background_automation',
                                     **command_args)
                    else:
                        call_command('run_automation', **command_args)
                except Exception as e:
                    logger.error(
                        "Błąd podczas uruchamiania automatyzacji: %s", str(e))
                    try:
                        automation_run.refresh_from_db()
                        automation_run.status = 'failed'
                        automation_run.error_message = str(e)
                        automation_run.save()
                    except Exception:
                        pass

            thread = threading.Thread(target=run_command)
            thread.daemon = True
            thread.start()

            messages.success(
                request,
                f'Automatyzacja została uruchomiona w tle (typ: {automation_type}). '
                f'Sprawdź status w AutomationRun #{automation_run.id}'
            )
            return redirect('admin:web_agent_automationrun_changelist')

        # Pobierz dostępne marki i kategorie
        brands = Brand.objects.all().order_by('name')
        categories = Category.objects.all().order_by('name')

        brand_choices = [('', '---------')] + \
            [(brand.name, brand.name) for brand in brands]
        category_choices = [('', '---------')] + \
            [(cat.name, cat.name) for cat in categories]

        context = {
            'brand_choices': brand_choices,
            'category_choices': category_choices,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        return render(request, 'admin/web_agent/automationrun/run_automation_form.html', context)

    def changelist_view(self, request, extra_context=None):
        """Dodaj przycisk do uruchomienia automatyzacji na górze"""
        extra_context = extra_context or {}
        extra_context['run_automation_url'] = reverse(
            'admin:web_agent_automationrun_run_form')
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        """Zapisz model z wartościami z formularza"""
        # Pobierz wartości z formularza
        brand_name = form.cleaned_data.get('brand_name', '')
        category_name = form.cleaned_data.get('category_name', '')
        active_filter = form.cleaned_data.get('active_filter', '')
        is_mapped_filter = form.cleaned_data.get('is_mapped_filter', '')

        # Ustaw brand_id
        if brand_name:
            try:
                brand = Brand.objects.get(name=brand_name)
                obj.brand_id = int(brand.brand_id)
            except Brand.DoesNotExist:
                pass

        # Ustaw category_id
        if category_name:
            try:
                category = Category.objects.filter(
                    name__icontains=category_name).first()
                if category:
                    obj.category_id = int(category.category_id)
            except Exception:  # noqa: F841
                pass

        # Ustaw filtry
        filters = {}
        if active_filter:
            filters['active'] = active_filter.lower() in (
                'true', '1', 'yes', 'tak')
        if is_mapped_filter:
            filters['is_mapped'] = is_mapped_filter.lower() in (
                'true', '1', 'yes', 'tak')

        obj.filters = filters

        super().save_model(request, obj, form, change)


@admin.register(ProductProcessingLog)
class ProductProcessingLogAdmin(admin.ModelAdmin):
    """Admin dla ProductProcessingLog"""
    list_display = [
        'id', 'automation_run', 'product_id', 'product_name',
        'status', 'mpd_product_id', 'processed_at'
    ]
    list_filter = ['status', 'automation_run', 'processed_at']
    search_fields = ['product_id', 'product_name', 'error_message']
    readonly_fields = ['processed_at']
    date_hierarchy = 'processed_at'

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('automation_run', 'product_id', 'product_name', 'status')
        }),
        ('Wynik', {
            'fields': ('mpd_product_id', 'error_message', 'processed_at')
        }),
        ('Dane przetwarzania', {
            'fields': ('processing_data',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProducerColor)
class ProducerColorAdmin(admin.ModelAdmin):
    list_display = ['brand_name', 'color_name',
                    'usage_count', 'created_at', 'updated_at']
    list_filter = ['brand_name', 'created_at']
    search_fields = ['brand_name', 'color_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['brand_name', 'color_name']

    fieldsets = (
        ('Informacje podstawowe', {
            'fields': ('brand_id', 'brand_name', 'color_name', 'normalized_color')
        }),
        ('Statystyki', {
            'fields': ('usage_count',)
        }),
        ('Daty', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(BrandConfig)
class BrandConfigAdmin(admin.ModelAdmin):
    """Admin dla BrandConfig"""
    list_display = [
        'brand_name', 'brand_id', 'default_active_filter',
        'default_is_mapped_filter', 'similarity_threshold', 'updated_at'
    ]
    list_filter = ['default_active_filter',
                   'default_is_mapped_filter', 'created_at', 'updated_at']
    search_fields = ['brand_name', 'brand_id']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'updated_at'

    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('brand_id', 'brand_name')
        }),
        ('Domyślne filtry', {
            'fields': ('default_active_filter', 'default_is_mapped_filter')
        }),
        ('Mapowanie kolorów', {
            'fields': ('color_mapping',),
            'description': 'Mapowanie kolorów producenta w formacie JSON: {"Dark Brown": "Ciemny Brąz", "Beige": "Beż"}'
        }),
        ('Atrybuty i wyszukiwanie', {
            'fields': ('attributes', 'similarity_threshold'),
            'description': 'Lista atrybutów do wyszukiwania w opisie produktu oraz próg podobieństwa dla cosine similarity'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
