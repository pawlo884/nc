"""
Testy Sagi Mada → MPD: sukces oraz kompensacja przy błędzie kroku 2,
plus jawne ustawianie producer_color_id przy uploadzie zdjęć.
"""
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from mada.models import Brand, MadaProduct, MadaProductImage, MadaProductVariant, Saga, SagaStep
from mada.services import create_mpd_product_from_mada

from MPD.models import Products


def _mpd_db():
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def _mada_db():
    return 'zzz_mada' if 'zzz_mada' in settings.DATABASES else 'mada'


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class MadaSagaTest(TestCase):
    """Testy flow Saga: tworzenie produktu MPD z Mada z kompensacją."""

    databases = '__all__'

    def setUp(self):
        mada_db = _mada_db()

        self.mada_brand = Brand.objects.using(mada_db).create(
            producer_id='MADA_SAGA_BRAND', name='Test Brand Saga Mada',
        )
        self.mada_product = MadaProduct.objects.using(mada_db).create(
            api_id=800001,
            name='Produkt testowy Saga Mada',
            desc='Opis Mada',
            brand=self.mada_brand,
            price=Decimal('129.99'),
        )
        self.mada_variant = MadaProductVariant.objects.using(mada_db).create(
            product=self.mada_product,
            variant_key='5901234567890',
            size='M',
            color='Czerwony',
            ean='5901234567890',
            stock=5,
        )

    def test_saga_success(self):
        mada_db = _mada_db()
        mpd_db = _mpd_db()

        result = create_mpd_product_from_mada(self.mada_product.pk, form_data={})

        self.assertTrue(result['success'], result.get('error_message'))
        mpd_product_id = result['mpd_product_id']
        self.assertIsNotNone(mpd_product_id)
        self.assertTrue(Products.objects.using(mpd_db).filter(id=mpd_product_id).exists())

        self.mada_product.refresh_from_db(using=mada_db)
        self.assertEqual(self.mada_product.mapped_product_uid, mpd_product_id)
        self.mada_variant.refresh_from_db(using=mada_db)
        self.assertIsNotNone(self.mada_variant.mapped_variant_uid)
        self.assertTrue(self.mada_variant.is_mapped)

        saga_row = Saga.objects.using(mada_db).latest('created_at')
        self.assertEqual(saga_row.status, 'completed')
        self.assertEqual(saga_row.total_steps, 2)
        self.assertEqual(saga_row.completed_steps, 2)

        steps = list(
            SagaStep.objects.using(mada_db).filter(saga=saga_row).order_by('step_order')
        )
        self.assertEqual([s.step_name for s in steps], ['create_mpd', 'update_mada_mapping'])
        self.assertTrue(all(s.status == 'completed' for s in steps))

    def test_saga_compensation_when_step2_fails(self):
        mada_db = _mada_db()
        mpd_db = _mpd_db()

        count_before = Products.objects.using(mpd_db).count()

        with patch('mada.services._saga_update_mada_mapping', side_effect=Exception('Symulowany błąd zapisu Mada')):
            result = create_mpd_product_from_mada(self.mada_product.pk, form_data={})

        self.assertFalse(result['success'])
        self.assertIn('Symulowany błąd zapisu Mada', result.get('error_message', ''))

        self.assertEqual(count_before, Products.objects.using(mpd_db).count())
        self.mada_product.refresh_from_db(using=mada_db)
        self.assertIsNone(self.mada_product.mapped_product_uid)

        saga_row = Saga.objects.using(mada_db).latest('created_at')
        self.assertEqual(saga_row.status, 'compensated')
        self.assertEqual(saga_row.failed_step, 'update_mada_mapping')


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class MadaSagaAdminTest(TestCase):
    """Sagi/Kroki Sagi powinny być widoczne w panelu admina mada (parytet z matterhorn1/tabu)."""

    databases = '__all__'

    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username='mada_saga_admin', email='mada_saga_admin@example.com', password='pass1234',
        )
        self.client.force_login(self.superuser)

    def test_saga_changelist_reachable(self):
        response = self.client.get(reverse('admin:mada_saga_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_sagastep_changelist_reachable(self):
        response = self.client.get(reverse('admin:mada_sagastep_changelist'))
        self.assertEqual(response.status_code, 200)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class MadaImageUploadProducerColorTest(TestCase):
    """upload_mada_images_to_mpd ustawia producer_color_id na product_images."""

    databases = '__all__'

    def setUp(self):
        from MPD.models import Brands, Colors, Products
        mpd_db = _mpd_db()
        mada_db = _mada_db()

        Colors.objects.using(mpd_db).create(name='Czarny główny mada')
        self.pc = Colors.objects.using(mpd_db).create(name='Grafit M999')
        brand = Brands.objects.using(mpd_db).create(name='B mada')
        self.mpd_product = Products.objects.using(mpd_db).create(name='Img PC Test Mada', brand=brand)

        self.mada_product = MadaProduct.objects.using(mada_db).create(
            api_id=830001, name='Mada img pc', price=Decimal('0'),
        )
        MadaProductImage.objects.using(mada_db).create(
            product=self.mada_product, api_image_id='1', image_url='https://mada.example/main.jpg', order=0,
        )

    def test_producer_color_set_from_name(self):
        from mada.services import upload_mada_images_to_mpd
        from MPD.models import ProductImage

        with patch(
            'matterhorn1.defs_db.upload_image_to_bucket_and_get_url',
            return_value='MPD_test/x/x_1_Grafit.jpg',
        ):
            res = upload_mada_images_to_mpd(
                self.mpd_product.id, self.mada_product.id, producer_color_name='Grafit M999',
            )
        self.assertEqual(res['uploaded_images'], 1)
        img = ProductImage.objects.using(_mpd_db()).get(product_id=self.mpd_product.id)
        self.assertEqual(img.producer_color_id, self.pc.id)

    def test_producer_color_null_when_name_unknown(self):
        from mada.services import upload_mada_images_to_mpd
        from MPD.models import ProductImage

        with patch(
            'matterhorn1.defs_db.upload_image_to_bucket_and_get_url',
            return_value='MPD_test/x/x_1.jpg',
        ):
            upload_mada_images_to_mpd(
                self.mpd_product.id, self.mada_product.id, producer_color_name='NieMaTakiego',
            )
        img = ProductImage.objects.using(_mpd_db()).get(product_id=self.mpd_product.id)
        self.assertIsNone(img.producer_color_id)
