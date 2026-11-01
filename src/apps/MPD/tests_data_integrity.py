"""Integralność danych MPD: PROTECT na słownikach, updated_at zdjęć, VAT."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from MPD.models import (
    Brands, ProductImage, Products, ProductVariants, Sizes, Units, Vat,
)
from MPD.vat import (
    resolve_vat, resolve_vat_id, resolve_vat_id_or_default, vat_rate,
)


class DictionaryProtectTest(TestCase):
    """Usunięcie wpisu słownika nie może kasować produktów/wariantów."""

    def setUp(self):
        self.brand = Brands.objects.create(name='Marka')
        self.unit = Units.objects.create(unit_id=901, name='szt.')
        self.size = Sizes.objects.create(name='M')
        self.product = Products.objects.create(
            name='Produkt', brand=self.brand, unit=self.unit)
        self.variant = ProductVariants.objects.create(
            product=self.product, size=self.size)

    def test_brand_delete_blocked(self):
        with self.assertRaises(ProtectedError):
            self.brand.delete()
        self.assertTrue(Products.objects.filter(pk=self.product.pk).exists())

    def test_unit_delete_blocked(self):
        with self.assertRaises(ProtectedError):
            self.unit.delete()

    def test_size_delete_blocked(self):
        with self.assertRaises(ProtectedError):
            self.size.delete()
        self.assertTrue(ProductVariants.objects.filter(pk=self.variant.pk).exists())

    def test_unused_brand_can_be_deleted(self):
        Brands.objects.create(name='Pusta').delete()


class ProductImageUpdatedAtTest(TestCase):
    """Eksport przyrostowy filtruje po updated_at, więc musi się zmieniać."""

    def test_updated_at_changes_on_save(self):
        product = Products.objects.create(name='P')
        image = ProductImage.objects.create(product=product, file_path='a.jpg')
        old = timezone.now() - timedelta(days=1)
        ProductImage.objects.filter(pk=image.pk).update(updated_at=old)

        image.refresh_from_db()
        image.file_path = 'b.jpg'
        image.save()
        image.refresh_from_db()

        self.assertGreater(image.updated_at, old)


class VatResolutionTest(TestCase):
    """Jedna reguła interpretacji kolumny product_variants_retail_price.vat."""

    databases = {'default', 'MPD'}

    def setUp(self):
        self.vat23 = Vat.objects.using('MPD').create(vat_rate=Decimal('23.00'))
        self.vat8 = Vat.objects.using('MPD').create(vat_rate=Decimal('8.00'))

    def test_stored_id_resolves_to_rate(self):
        self.assertEqual(resolve_vat(self.vat8.id), (self.vat8.id, Decimal('8.00')))
        self.assertEqual(vat_rate(Decimal(self.vat8.id)), Decimal('8.00'))

    def test_legacy_rate_without_matching_id(self):
        legacy = Decimal('5.50')
        self.assertEqual(resolve_vat(legacy), (None, legacy))

    def test_empty_value(self):
        self.assertEqual(resolve_vat(None), (None, None))
        self.assertIsNone(vat_rate(''))

    def test_resolve_id_accepts_id_or_rate(self):
        self.assertEqual(resolve_vat_id(self.vat8.id), self.vat8.id)
        reduced = Vat.objects.using('MPD').create(vat_rate=Decimal('5.50'))
        self.assertEqual(resolve_vat_id('5.5'), reduced.id)

    def test_resolve_id_garbage_falls_back_to_existing_row(self):
        self.assertIn(resolve_vat_id('abc'), {self.vat23.id, self.vat8.id})

    def test_missing_value_defaults_to_23_percent(self):
        self.assertEqual(resolve_vat_id_or_default(None), self.vat23.id)
