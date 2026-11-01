"""
Testy wspólnej reguły kolorów MPD (MPD/colors.py) używanej przez wszystkie hurtownie.
"""
from django.conf import settings
from django.test import TestCase

from MPD.colors import (
    ColorResolutionError,
    get_main_color,
    get_or_create_producer_color,
    resolve_variant_colors,
)
from MPD.models import Colors


def _mpd_db():
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


class MainColorTest(TestCase):
    databases = '__all__'

    def setUp(self):
        self.db = _mpd_db()
        self.czarny = Colors.objects.using(self.db).create(name='Czarny')
        self.bezowy = Colors.objects.using(self.db).create(name='Beżowy')
        self.beige = Colors.objects.using(self.db).create(name='Beige', parent=self.bezowy)

    def test_form_id_wins_over_source_name(self):
        color = get_main_color(self.czarny.id, 'Beżowy', using=self.db)
        self.assertEqual(color, self.czarny)

    def test_form_id_as_string(self):
        self.assertEqual(get_main_color(str(self.czarny.id), None, using=self.db), self.czarny)

    def test_empty_form_id_falls_back_to_name_case_insensitive(self):
        self.assertEqual(get_main_color('', '  czarny ', using=self.db), self.czarny)

    def test_form_id_pointing_to_producer_color_is_rejected(self):
        with self.assertRaises(ColorResolutionError):
            get_main_color(self.beige.id, None, using=self.db)

    def test_unknown_form_id_is_rejected(self):
        with self.assertRaises(ColorResolutionError):
            get_main_color(999999, 'Czarny', using=self.db)

    def test_non_numeric_form_id_is_rejected(self):
        with self.assertRaises(ColorResolutionError):
            get_main_color('abc', 'Czarny', using=self.db)

    def test_name_matching_only_producer_color_is_rejected(self):
        with self.assertRaises(ColorResolutionError):
            get_main_color(None, 'Beige', using=self.db)

    def test_unknown_source_color_does_not_create_main_color(self):
        before = Colors.objects.using(self.db).count()
        with self.assertRaises(ColorResolutionError):
            get_main_color(None, 'Fuksja', using=self.db)
        self.assertEqual(Colors.objects.using(self.db).count(), before)

    def test_nothing_given_is_rejected(self):
        with self.assertRaises(ColorResolutionError):
            get_main_color(None, None, using=self.db)


class ProducerColorTest(TestCase):
    databases = '__all__'

    def setUp(self):
        self.db = _mpd_db()
        self.czarny = Colors.objects.using(self.db).create(name='Czarny')
        self.bezowy = Colors.objects.using(self.db).create(name='Beżowy')

    def test_empty_name_returns_none(self):
        self.assertIsNone(get_or_create_producer_color('  ', self.czarny, using=self.db))

    def test_creates_with_parent(self):
        pc = get_or_create_producer_color('Nero', self.czarny, using=self.db)
        self.assertEqual(pc.parent, self.czarny)
        self.assertEqual(pc.name, 'Nero')

    def test_reuses_existing_case_insensitive(self):
        nero = Colors.objects.using(self.db).create(name='Nero', parent=self.czarny)
        self.assertEqual(get_or_create_producer_color('NERO', self.czarny, using=self.db), nero)

    def test_existing_with_other_parent_is_reused_and_not_moved(self):
        beige = Colors.objects.using(self.db).create(name='Beige', parent=self.bezowy)
        pc = get_or_create_producer_color('Beige', self.czarny, using=self.db)
        self.assertEqual(pc, beige)
        beige.refresh_from_db(using=self.db)
        self.assertEqual(beige.parent, self.bezowy)

    def test_name_trimmed_to_50(self):
        pc = get_or_create_producer_color('x' * 60, self.czarny, using=self.db)
        self.assertEqual(len(pc.name), 50)


class ResolveVariantColorsTest(TestCase):
    databases = '__all__'

    def test_returns_both(self):
        db = _mpd_db()
        czarny = Colors.objects.using(db).create(name='Czarny')
        colors = resolve_variant_colors(
            main_color_id=None, producer_color_name='Nero',
            source_color_name='CZARNY', using=db,
        )
        self.assertEqual(colors.color, czarny)
        self.assertEqual(colors.producer_color.parent, czarny)
