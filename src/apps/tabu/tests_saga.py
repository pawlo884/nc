"""
Testy Sagi Tabu → MPD: sukces oraz kompensacja przy błędzie kroku 2.
"""
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from tabu.models import Brand, TabuProduct, TabuProductVariant
from tabu.services import create_mpd_product_from_tabu

from MPD.models import Products


def _mpd_db():
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def _tabu_db():
    return 'zzz_tabu' if 'zzz_tabu' in settings.DATABASES else 'tabu'


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TabuSagaTest(TestCase):
    """Testy flow Saga: tworzenie produktu MPD z Tabu z kompensacją."""

    databases = '__all__'

    def setUp(self):
        mpd_db = _mpd_db()
        tabu_db = _tabu_db()

        self.tabu_brand = Brand.objects.using(tabu_db).create(
            brand_id='TABU_SAGA_BRAND',
            name='Test Brand Saga',
        )
        self.tabu_product = TabuProduct.objects.using(tabu_db).create(
            api_id=900001,
            symbol='SAGA-TEST-001',
            name='Produkt testowy Saga Tabu',
            desc_short='Krótki opis',
            desc_long='Opis długi',
            last_update=timezone.now(),
            brand=self.tabu_brand,
            store_total=10,
            price_net=99.99,
        )
        self.tabu_variant = TabuProductVariant.objects.using(tabu_db).create(
            api_id=900101,
            product=self.tabu_product,
            symbol='SAGA-VAR-001',
            size='M',
            color='Czerwony',
            store=5,
            price_net=99.99,
            ean='5901234567890',
        )

    def test_saga_success(self):
        """Saga sukces: produkt w MPD, mapowanie w Tabu."""
        tabu_db = _tabu_db()
        mpd_db = _mpd_db()

        result = create_mpd_product_from_tabu(self.tabu_product.pk, form_data={})

        self.assertTrue(result['success'], result.get('error_message'))
        mpd_product_id = result['mpd_product_id']
        self.assertIsNotNone(mpd_product_id)

        self.assertTrue(
            Products.objects.using(mpd_db).filter(id=mpd_product_id).exists(),
            'Produkt MPD powinien istnieć',
        )
        self.tabu_product.refresh_from_db(using=tabu_db)
        self.assertEqual(
            self.tabu_product.mapped_product_uid,
            mpd_product_id,
            'Tabu produkt powinien mieć mapped_product_uid',
        )
        self.tabu_variant.refresh_from_db(using=tabu_db)
        self.assertIsNotNone(
            self.tabu_variant.mapped_variant_uid,
            'Wariant Tabu powinien mieć mapped_variant_uid',
        )

    def test_saga_compensation_when_step2_fails(self):
        """Gdy krok 2 (zapis w Tabu) rzuci błąd, kompensacja usuwa produkt z MPD."""
        tabu_db = _tabu_db()
        mpd_db = _mpd_db()

        count_before = Products.objects.using(mpd_db).count()

        with patch('tabu.services._saga_update_tabu_mapping', side_effect=Exception('Symulowany błąd zapisu Tabu')):
            result = create_mpd_product_from_tabu(self.tabu_product.pk, form_data={})

        self.assertFalse(result['success'])
        self.assertIn('Symulowany błąd zapisu Tabu', result.get('error_message', ''))

        count_after = Products.objects.using(mpd_db).count()
        self.assertEqual(
            count_before,
            count_after,
            'Kompensacja powinna usunąć produkt z MPD (liczba produktów bez zmian)',
        )
        self.tabu_product.refresh_from_db(using=tabu_db)
        self.assertIsNone(
            self.tabu_product.mapped_product_uid,
            'Tabu produkt nie powinien mieć mapped_product_uid po kompensacji',
        )
