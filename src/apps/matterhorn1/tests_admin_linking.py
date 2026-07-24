"""
Test: ProductAdmin._auto_map_variants (używane przez bulk_map_to_mpd i
auto_map_variants) faktycznie zleca task linkowania z innych hurtowni po EAN
po zatwierdzeniu transakcji — wcześniej komentarz w kodzie mówił, że zrobi to
"sygnał MPD", który dla już-istniejącego produktu MPD nigdy się nie odpalał.
"""
from unittest.mock import patch

from django.conf import settings
from django.contrib import admin
from django.test import TestCase, override_settings

from matterhorn1.admin import ProductAdmin
from matterhorn1.models import Brand, Product, ProductVariant

from MPD.models import Colors, Products, Sizes, Sources


def _mpd_db():
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def _mh_db():
    return 'zzz_matterhorn1' if 'zzz_matterhorn1' in settings.DATABASES else 'matterhorn1'


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class AutoMapVariantsDispatchesLinkTaskTest(TestCase):
    """_auto_map_variants powinno zlecić link_variants_from_other_sources_task po commicie."""

    databases = '__all__'

    def setUp(self):
        mh_db, mpd_db = _mh_db(), _mpd_db()

        Sources.objects.using(mpd_db).create(name='Matterhorn API', type='api')
        Colors.objects.using(mpd_db).create(name='Czarny')
        Sizes.objects.using(mpd_db).create(name='L', category='default')

        self.mpd_product = Products.objects.using(mpd_db).create(name='MPD Auto Map Test')

        brand = Brand.objects.using(mh_db).create(brand_id='AUTOMAP_BR', name='AutoMap Brand')
        self.product = Product.objects.using(mh_db).create(
            product_uid=910001,
            name='Produkt do auto-mapowania',
            brand=brand,
            color='Czarny',
            mapped_product_uid=self.mpd_product.id,
            is_mapped=True,
        )
        self.variant = ProductVariant.objects.using(mh_db).create(
            product=self.product,
            variant_uid='910101',
            name='L',
            stock=3,
            ean='5901234500011',
        )

    def test_auto_map_variants_dispatches_link_task_after_commit(self):
        model_admin = ProductAdmin(Product, admin.site)

        # TestCase owija każdy test w transakcję, która nigdy się faktycznie nie
        # zatwierdza (rollback na koniec) — transaction.on_commit() normalnie by tu
        # więc nigdy nie odpalił. captureOnCommitCallbacks(execute=True) symuluje
        # commit i wykonuje zakolejkowane callbacki, tak jak zrobiłby to prawdziwy request.
        with patch('MPD.tasks.link_variants_from_other_sources_task.apply_async') as mock_apply_async:
            with self.captureOnCommitCallbacks(execute=True):
                model_admin._auto_map_variants(self.product, self.mpd_product.id)

            mock_apply_async.assert_called_once()
            _, kwargs = mock_apply_async.call_args
            self.assertEqual(kwargs.get('args'), (self.mpd_product.id, self._mh_source_id()))
            self.assertEqual(kwargs.get('queue'), 'default')

    def _mh_source_id(self):
        return Sources.objects.using(_mpd_db()).get(name='Matterhorn API').id
