"""
Ręczne dopinanie wariantów z innych hurtowni po EAN dla produktu MPD.

Użycie:
  python manage.py link_variants_by_ean 123 --source-id 1 --settings=core.settings.dev

Gdzie 123 to mpd_product_id, --source-id to current_source_id (źródło z którego dodano - pomijane).
"""
from django.core.management.base import BaseCommand

from MPD.source_adapters import link_variants_from_other_sources


class Command(BaseCommand):
    help = 'Dopina warianty z innych hurtowni po EAN dla produktu MPD (bez Celery)'

    def add_arguments(self, parser):
        parser.add_argument(
            'mpd_product_id',
            type=int,
            help='ID produktu w MPD',
        )
        parser.add_argument(
            '--source-id',
            type=int,
            required=True,
            help='ID źródła z którego dodano produkt (Tabu/Matterhorn) - zostanie pominięte',
        )

    def handle(self, *args, **options):
        mpd_product_id = options['mpd_product_id']
        current_source_id = options['source_id']

        self.stdout.write(
            f'Dopinanie wariantów dla MPD product_id={mpd_product_id} '
            f'(exclude source {current_source_id})...'
        )
        stats = link_variants_from_other_sources(mpd_product_id, current_source_id)

        linked = stats.get('linked_count', 0)
        errors = stats.get('errors', [])

        if linked:
            self.stdout.write(self.style.SUCCESS(f'Dopięto {linked} wariantów'))
        elif errors:
            self.stdout.write(self.style.WARNING(f'Błędy: {errors}'))
        else:
            self.stdout.write('Brak dopasowań (sprawdź logi)')

        self.stdout.write(f'Stats: {stats}')
