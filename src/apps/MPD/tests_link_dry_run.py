"""mpd_link_dry_run: podgląd dopięcia wariantów między hurtowniami po EAN."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from mada.models import MadaProduct, MadaProductVariant
from tabu.models import TabuProduct, TabuProductVariant


class LinkDryRunTest(TestCase):
    databases = '__all__'

    def test_shared_ean_between_wholesalers(self):
        tp = TabuProduct.objects.using('zzz_tabu').create(
            api_id=1, symbol='J1229', name='Biustonosz Soft Model Jessia 1229 Beige',
            last_update=timezone.now())
        TabuProductVariant.objects.using('zzz_tabu').create(
            product=tp, api_id=11, ean='5901111111111', size='75B', color='beige')
        mp = MadaProduct.objects.using('zzz_mada').create(api_id=2, name='Gaia Jessia 1229 soft')
        MadaProductVariant.objects.using('zzz_mada').create(
            product=mp, ean='5901111111111', size='75B')

        out = StringIO()
        call_command('mpd_link_dry_run', '--term', 'Jessia', '--term', '1229', stdout=out)
        text = out.getvalue()
        self.assertIn('5901111111111: Mada + Tabu', text)
        self.assertIn('wspólnych dla >1 hurtowni: 1', text)
        self.assertIn('Produktu jeszcze nie ma w MPD', text)
