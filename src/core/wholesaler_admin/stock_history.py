from django.contrib import admin
from django.shortcuts import render
from django.urls import path


class StockHistoryAdminBase(admin.ModelAdmin):
    """Wspólna część admina StockHistory: routing i widok dashboardu bestsellerów.
    Podklasa ustawia `bestsellers_data_module` + `bestsellers_template` +
    `bestsellers_url_name`. Dodatkowe widoki specyficzne dla appki (popularne
    produkty, statystyki, czyszczenie historii) NIE są częścią tej bazy — dopisuje
    się je na podklasie, wołając super().get_urls() żeby zachować routing 'bestsellers/'."""

    list_per_page = 50
    ordering = ['-timestamp']

    bestsellers_data_module = None   # np. matterhorn1.bestsellers_data / tabu.bestsellers_data
    bestsellers_template = None      # np. 'admin/matterhorn1/stock_history/bestsellers.html'
    bestsellers_url_name = None      # np. 'matterhorn1_stockhistory_bestsellers'
    bestsellers_title = 'Bestsellery'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bestsellers/', self.admin_site.admin_view(self.bestsellers_view),
                 name=self.bestsellers_url_name),
        ]
        return custom_urls + urls

    def bestsellers_view(self, request):
        days = int(request.GET.get('days', 90))
        if days not in (30, 90, 180):
            days = 90
        data = self.bestsellers_data_module.get_dashboard_data(days=days)
        context = {
            **self.admin_site.each_context(request),
            'data': data,
            'days': days,
            'opts': self.model._meta,
            'title': self.bestsellers_title,
        }
        return render(request, self.bestsellers_template, context)
