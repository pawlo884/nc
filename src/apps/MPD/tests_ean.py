"""Kanoniczny EAN wariantu (ProductVariants.ean) — reguła, sygnał, komenda."""
from io import StringIO
from types import SimpleNamespace

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from MPD.ean import clean_gtin, ensure_variant_ean, pick_canonical_ean
from MPD.models import Products, ProductVariants, ProductvariantsSources, Sources


def _row(source_id, pk=1, **codes):
    return SimpleNamespace(source_id=source_id, pk=pk, **codes)


class CleanGtinTest(SimpleTestCase):

    def test_valid_lengths(self):
        for code in ('12345670', '123456789012', '5901234123457', '15901234123454'):
            self.assertEqual(clean_gtin(code), code)

    def test_strips_spaces_and_dashes(self):
        self.assertEqual(clean_gtin(' 590-1234 123457 '), '5901234123457')

    def test_rejects_non_gtin(self):
        for raw in (None, '', 'ABC123', '12345', '59012341234571234', 'brak'):
            self.assertIsNone(clean_gtin(raw))


class PickCanonicalEanTest(SimpleTestCase):

    def test_lowest_source_wins(self):
        rows = [
            _row(3, ean='5900000000003'),
            _row(1, ean='5900000000001'),
        ]
        self.assertEqual(pick_canonical_ean(rows), '5900000000001')

    def test_field_order_within_source(self):
        rows = [_row(1, ean='zły kod', gtin13='5900000000013', gtin14='15900000000010')]
        self.assertEqual(pick_canonical_ean(rows), '5900000000013')

    def test_falls_through_to_next_source(self):
        rows = [_row(1, ean=None, other='x'), _row(2, ean='5900000000002')]
        self.assertEqual(pick_canonical_ean(rows), '5900000000002')

    def test_none_when_no_code(self):
        self.assertIsNone(pick_canonical_ean([_row(1, ean='', mpn='ABC')]))
        self.assertIsNone(pick_canonical_ean([]))

    def test_alphanumeric_fallback_when_no_gtin(self):
        # kody Gatty z common_products_ean.csv
        self.assertEqual(pick_canonical_ean([_row(1, ean=' 00011t180291 ')]), '00011T180291')

    def test_gtin_from_any_source_beats_fallback(self):
        rows = [_row(1, ean='00011T180291'), _row(2, ean='5900000000002')]
        self.assertEqual(pick_canonical_ean(rows), '5900000000002')

    def test_fallback_rejects_too_long_or_junk(self):
        self.assertIsNone(pick_canonical_ean([_row(1, ean='32926800180203600')]))
        self.assertIsNone(pick_canonical_ean([_row(1, ean='brak kodu!')]))
        self.assertIsNone(pick_canonical_ean([_row(1, ean='brak-kodu')]))


class VariantEanSignalTest(TestCase):

    def setUp(self):
        self.source = Sources.objects.create(name='Hurtownia A')
        self.other_source = Sources.objects.create(name='Hurtownia B')
        self.product = Products.objects.create(name='Produkt')
        self.variant = ProductVariants.objects.create(product=self.product)

    def test_source_with_ean_sets_variant_ean(self):
        ProductvariantsSources.objects.create(
            variant=self.variant, source=self.source, ean='5901234123457')
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.ean, '5901234123457')

    def test_existing_ean_is_not_overwritten(self):
        ProductVariants.objects.filter(pk=self.variant.pk).update(ean='5000000000000')
        ProductvariantsSources.objects.create(
            variant=self.variant, source=self.source, ean='5901234123457')
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.ean, '5000000000000')

    def test_invalid_code_leaves_ean_empty(self):
        ProductvariantsSources.objects.create(
            variant=self.variant, source=self.source, ean='brak kodu!')
        self.variant.refresh_from_db()
        self.assertIsNone(self.variant.ean)

    def test_ensure_variant_ean_returns_existing(self):
        ProductvariantsSources.objects.create(
            variant=self.variant, source=self.other_source, gtin13='5900000000002')
        self.assertEqual(ensure_variant_ean(self.variant.pk, 'default'), '5900000000002')


class MpdEanCommandTest(TestCase):
    databases = {'default', 'zzz_MPD'}
    db = 'zzz_MPD'

    def setUp(self):
        objs = lambda m: m.objects.using(self.db)  # noqa: E731
        source = objs(Sources).create(name='Hurtownia')
        self.p1 = objs(Products).create(name='Stanik z Tabu')
        self.p2 = objs(Products).create(name='Stanik z Mady')
        self.v1 = objs(ProductVariants).create(product=self.p1)
        self.v2 = objs(ProductVariants).create(product=self.p2)
        # bulk_create pomija sygnały — tak jak importy masowe
        objs(ProductvariantsSources).bulk_create([
            ProductvariantsSources(variant=self.v1, source=source, ean='5901234123457'),
            ProductvariantsSources(variant=self.v2, source=source, ean='5901234123457'),
        ])

    def test_backfill_then_report_duplicates(self):
        err = StringIO()
        call_command('mpd_ean', '--backfill', stdout=StringIO(), stderr=err)
        self.assertIn('Uzupełniono EAN dla 2 wariantów', err.getvalue())

        out = StringIO()
        call_command('mpd_ean', '--report', stdout=out, stderr=StringIO())
        lines = out.getvalue().strip().splitlines()
        self.assertEqual(lines[0], 'ean,products,product_ids')
        self.assertTrue(lines[1].startswith('5901234123457,2,'))
        self.assertIn(f'{self.p1.pk};Stanik z Tabu', lines[1])
        self.assertIn(f'{self.p2.pk};Stanik z Mady', lines[1])



class FindExistingMpdProductTest(TestCase):
    databases = {'default'}

    def setUp(self):
        self.source = Sources.objects.create(name='Hurtownia')
        self.product = Products.objects.create(name='P')

    def test_matches_canonical_ean(self):
        from MPD.dedup import find_existing_mpd_product
        ProductVariants.objects.create(product=self.product, ean='5901234123457')
        self.assertEqual(
            find_existing_mpd_product([' 5901234123457', None, ''], 'default'), self.product.pk)

    def test_matches_legacy_source_ean_when_canonical_empty(self):
        from MPD.dedup import find_existing_mpd_product
        variant = ProductVariants.objects.create(product=self.product)
        ProductvariantsSources.objects.bulk_create([  # bez sygnału -> variant.ean pusty
            ProductvariantsSources(variant=variant, source=self.source, ean='00011T180291')])
        self.assertEqual(
            find_existing_mpd_product(['00011t180291'], 'default'), self.product.pk)

    def test_no_match(self):
        from MPD.dedup import find_existing_mpd_product
        self.assertIsNone(find_existing_mpd_product(['5900000000000'], 'default'))
        self.assertIsNone(find_existing_mpd_product([None, 'brak'], 'default'))

    def test_ambiguous(self):
        from MPD.dedup import AmbiguousMatch, find_existing_mpd_product
        other = Products.objects.create(name='Duplikat')
        ProductVariants.objects.create(product=self.product, ean='5901234123457')
        ProductVariants.objects.create(product=other, ean='5901234123457')
        with self.assertRaises(AmbiguousMatch) as ctx:
            find_existing_mpd_product(['5901234123457'], 'default')
        self.assertEqual(ctx.exception.product_ids, sorted([self.product.pk, other.pk]))
