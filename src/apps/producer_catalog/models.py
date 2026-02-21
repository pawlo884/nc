"""
Mini baza produktów zeskrapowanych ze stron producentów (np. avalingerie.pl).
Produkty, rozmiary, opisy, ceny + historia cen do pilnowania.
"""
from django.db import models
from decimal import Decimal


class ProducerSource(models.Model):
    """Źródło – strona producenta do scrapowania."""
    name = models.CharField('Nazwa', max_length=255)
    slug = models.SlugField('Slug', max_length=50, unique=True, help_text='np. ava')
    base_url = models.URLField('URL bazowy', max_length=500)
    is_active = models.BooleanField('Aktywne', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'producer_catalog_source'
        verbose_name = 'Źródło producenta'
        verbose_name_plural = 'Źródła producentów'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProducerProduct(models.Model):
    """Produkt z katalogu producenta (jedna strona produktu)."""
    source = models.ForeignKey(
        ProducerSource,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Źródło',
    )
    url = models.URLField('URL produktu', max_length=1000, db_index=True)
    external_id = models.CharField(
        'ID zewnętrzne',
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text='ID produktu u producenta (np. z URL)',
    )
    name = models.CharField('Nazwa', max_length=500)
    description = models.TextField('Opis', blank=True)
    image_url = models.URLField('URL obrazka', max_length=1000, blank=True)
    scraped_at = models.DateTimeField('Ostatni scrape', null=True, blank=True)
    raw_data = models.JSONField('Surowe dane', default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'producer_catalog_product'
        verbose_name = 'Produkt producenta'
        verbose_name_plural = 'Produkty producenta'
        ordering = ['source', 'name']
        unique_together = [['source', 'url']]

    def __str__(self):
        return f'{self.name} ({self.source.slug})'


class ProducerProductVariant(models.Model):
    """Wariant produktu – rozmiar + cena (do pilnowania cen)."""
    product = models.ForeignKey(
        ProducerProduct,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Produkt',
    )
    size_name = models.CharField('Rozmiar', max_length=100)
    price_brutto = models.DecimalField(
        'Cena brutto',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    price_netto = models.DecimalField(
        'Cena netto',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField('Waluta', max_length=10, default='PLN')
    stock_info = models.CharField('Stan', max_length=100, blank=True)
    scraped_at = models.DateTimeField('Ostatni scrape', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'producer_catalog_variant'
        verbose_name = 'Wariant producenta'
        verbose_name_plural = 'Warianty producenta'
        ordering = ['product', 'size_name']
        unique_together = [['product', 'size_name']]

    def __str__(self):
        return f'{self.product.name} – {self.size_name}'


class ProducerPriceHistory(models.Model):
    """Historia cen – do pilnowania zmian."""
    variant = models.ForeignKey(
        ProducerProductVariant,
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name='Wariant',
    )
    price_brutto = models.DecimalField(
        'Cena brutto',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    price_netto = models.DecimalField(
        'Cena netto',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField('Waluta', max_length=10, default='PLN')
    recorded_at = models.DateTimeField('Zapisano', auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'producer_catalog_price_history'
        verbose_name = 'Historia ceny'
        verbose_name_plural = 'Historia cen'
        ordering = ['-recorded_at']

    def __str__(self):
        return f'{self.variant} @ {self.price_brutto} ({self.recorded_at})'
