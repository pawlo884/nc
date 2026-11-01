"""
Kanoniczny EAN wariantów MPD (ProductVariants.ean).

Użycie:
  python manage.py mpd_ean --backfill   # uzupełnij puste EAN-y z hurtowni
  python manage.py mpd_ean --report     # EAN-y współdzielone przez różne produkty (#182)

--report wypisuje CSV: ean, liczba produktów, product_id;nazwa | ... — to lista
kandydatów do scalenia duplikatów produktów między hurtowniami.
"""
import csv
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q

from MPD.ean import pick_canonical_ean
from MPD.models import ProductVariants, ProductvariantsSources

BATCH = 2000


def _mpd_db():
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


class Command(BaseCommand):
    help = 'Uzupełnia kanoniczny EAN wariantów i raportuje duplikaty EAN między produktami'

    def add_arguments(self, parser):
        parser.add_argument('--backfill', action='store_true',
                            help='Uzupełnij puste ProductVariants.ean z ProductvariantsSources')
        parser.add_argument('--report', action='store_true',
                            help='Wypisz (CSV) EAN-y przypięte do wariantów w więcej niż jednym produkcie')

    def handle(self, *args, **options):
        if not options['backfill'] and not options['report']:
            raise CommandError('Podaj --backfill i/lub --report')
        db = _mpd_db()
        if options['backfill']:
            filled = self._backfill(db)
            self.stderr.write(self.style.SUCCESS(f'Uzupełniono EAN dla {filled} wariantów'))
        if options['report']:
            self._report(db)

    def _backfill(self, db):
        variant_ids = list(
            ProductVariants.objects.using(db)
            .filter(Q(ean__isnull=True) | Q(ean=''))
            .order_by('variant_id').values_list('variant_id', flat=True)
        )
        filled = 0
        for start in range(0, len(variant_ids), BATCH):
            chunk = variant_ids[start:start + BATCH]
            rows = defaultdict(list)
            for row in ProductvariantsSources.objects.using(db).filter(variant_id__in=chunk):
                rows[row.variant_id].append(row)
            for variant_id, source_rows in rows.items():
                ean = pick_canonical_ean(source_rows)
                if ean:
                    filled += ProductVariants.objects.using(db).filter(
                        Q(ean__isnull=True) | Q(ean=''),
                        variant_id=variant_id,
                    ).update(ean=ean)
        return filled

    def _report(self, db):
        shared = (
            ProductVariants.objects.using(db)
            .exclude(Q(ean__isnull=True) | Q(ean=''))
            .values('ean')
            .annotate(products=Count('product_id', distinct=True))
            .filter(products__gt=1)
            .order_by('-products', 'ean')
        )
        writer = csv.writer(self.stdout)
        writer.writerow(['ean', 'products', 'product_ids'])
        total = 0
        for row in shared:
            products = (
                ProductVariants.objects.using(db).filter(ean=row['ean'])
                .values_list('product_id', 'product__name').distinct()
                .order_by('product_id')
            )
            writer.writerow([
                row['ean'], row['products'],
                ' | '.join(f'{pid};{name}' for pid, name in products),
            ])
            total += 1
        self.stderr.write(f'EAN-y w więcej niż jednym produkcie: {total}')
