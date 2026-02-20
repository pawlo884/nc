"""
Dopinanie wariantów z nowej hurtowni do wszystkich produktów MPD (po EAN).

Uruchom po dodaniu nowego źródła (Sources) do systemu - np. nowa hurtownia.
Szuka w nowej hurtowni wariantów o EAN istniejących w MPD i dopina je
(ProductvariantsSources, StockAndPrices, mapped_product_uid w hurtowni).

Użycie:
  python manage.py link_new_warehouse --source-id 3 --settings=core.settings.dev

Gdzie --source-id to ID rekordu Sources w MPD (admin MPD → Sources).
"""
from django.core.management.base import BaseCommand

from MPD.source_adapters import link_all_products_to_new_source


class Command(BaseCommand):
    help = (
        'Dopina warianty z nowej hurtowni do wszystkich produktów MPD (po EAN). '
        'Uruchom po podłączeniu nowej hurtowni.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-id',
            type=int,
            required=True,
            help='ID źródła (Sources) w MPD - nowa hurtownia',
        )

    def handle(self, *args, **options):
        source_id = options['source_id']

        self.stdout.write(
            f'Dopinanie wariantów z nowej hurtowni (source_id={source_id}) do MPD...'
        )
        stats = link_all_products_to_new_source(source_id)

        linked = stats.get('linked_count', 0)
        errors = stats.get('errors', [])

        if linked:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Dopięto {linked} wariantów do {stats.get("products_processed", 0)} produktów'
                )
            )
        elif errors:
            self.stdout.write(self.style.WARNING(f'Błędy: {errors}'))
        else:
            self.stdout.write('Brak dopasowań EAN między MPD a nową hurtownią')

        self.stdout.write(f'Stats: {stats}')
