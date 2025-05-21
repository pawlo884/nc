from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.


class StockAndPrices(models.Model):
    product_id = models.CharField(max_length=100, primary_key=True)
    product_name = models.CharField(max_length=255)
    current_stock = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'stock_and_prices'
        verbose_name = 'Stan magazynowy'
        verbose_name_plural = 'Stany magazynowe'

    def __str__(self):
        return f"{self.product_name} - {self.current_stock} szt."


class StockHistory(models.Model):
    product = models.ForeignKey(
        StockAndPrices, on_delete=models.CASCADE, related_name='stock_history')
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    change_date = models.DateTimeField(default=timezone.now)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    change_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'stock_history'
        verbose_name = 'Historia stanu magazynowego'
        verbose_name_plural = 'Historia stanów magazynowych'
        ordering = ['-change_date']

    def __str__(self):
        return f"{self.product.product_name} - zmiana z {self.previous_stock} na {self.new_stock}"
