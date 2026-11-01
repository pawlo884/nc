"""Krok upload_product_images: klucze z bucketa muszą iść do uploadu jako URL."""
from unittest import mock

from django.test import TestCase

from matterhorn1.models import Product, ProductImage
from matterhorn1.saga import SagaService
from MPD.models import Products


class UploadProductImagesTest(TestCase):
    databases = {'default', 'MPD', 'matterhorn1'}

    def test_bucket_key_is_resolved_before_upload(self):
        mh = Product.objects.using('matterhorn1').create(product_uid=1087313, name='Jessia 1229')
        ProductImage.objects.using('matterhorn1').create(
            product=mh, image_url='db_images/custom900x1200_1087313.jpg', order=1)
        mpd = Products.objects.using('MPD').create(name='Jessia 1229')

        with mock.patch('matterhorn1.saga.resolve_image_url',
                        side_effect=lambda k: f'https://cdn.example/{k}'), \
                mock.patch('matterhorn1.defs_db.upload_image_to_bucket_and_get_url',
                           return_value=None) as upload:
            SagaService._upload_product_images(mpd.id, mh.id)

        self.assertEqual(
            upload.call_args.kwargs['image_path'],
            'https://cdn.example/db_images/custom900x1200_1087313.jpg')
