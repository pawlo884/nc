"""
Scala zduplikowany rekord Sources w MPD do rekordu docelowego.

Kontekst: przez zbyt luźne dopasowanie w rejestrze adapterów stary, pusty
rekord Sources "MADA" łapał adapter "Mada API" i linkowanie po EAN dopinało
warianty Mady podwójnie — raz pod źródłem "MADA", raz pod "Mada API".

Komenda przenosi ProductvariantsSources / StockAndPrices ze źródła --from do
--to (pomijając wiersze, dla których w --to już istnieje odpowiednik), a na
końcu — jeśli po przeniesieniu źródło --from nie ma już żadnych powiązań —
usuwa sam rekord Sources.

Użycie:
  python manage.py merge_duplicate_source --from "MADA" --to "Mada API" --dry-run
  python manage.py merge_duplicate_source --from "MADA" --to "Mada API"
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.db_routers import _get_mpd_db
from MPD.models import ProductvariantsSources, Sources, StockAndPrices


class Command(BaseCommand):
    help = 'Scala zduplikowany rekord Sources (--from) do docelowego (--to) w bazie MPD.'

    def add_arguments(self, parser):
        parser.add_argument('--from', dest='src_name', required=True, help='Nazwa źródła do zlania (usuwanego).')
        parser.add_argument('--to', dest='dst_name', required=True, help='Nazwa źródła docelowego.')
        parser.add_argument('--dry-run', action='store_true', help='Pokaż plan, nic nie zapisuj.')

    def handle(self, *args, **options):
        db = _get_mpd_db()
        src_name, dst_name = options['src_name'], options['dst_name']
        dry_run = options['dry_run']

        src = Sources.objects.using(db).filter(name=src_name).first()
        dst = Sources.objects.using(db).filter(name=dst_name).first()
        if not src:
            raise CommandError(f'Źródło {src_name!r} nie istnieje.')
        if not dst:
            raise CommandError(f'Źródło docelowe {dst_name!r} nie istnieje.')
        if src.id == dst.id:
            raise CommandError('--from i --to to ten sam rekord.')

        dst_variant_ids = set(
            ProductvariantsSources.objects.using(db)
            .filter(source_id=dst.id).values_list('variant_id', flat=True)
        )
        dst_sap_variant_ids = set(
            StockAndPrices.objects.using(db)
            .filter(source_id=dst.id).values_list('variant_id', flat=True)
        )

        src_pvs = list(ProductvariantsSources.objects.using(db).filter(source_id=src.id))
        src_sap = list(StockAndPrices.objects.using(db).filter(source_id=src.id))

        pvs_move = [r for r in src_pvs if r.variant_id not in dst_variant_ids]
        pvs_drop = [r for r in src_pvs if r.variant_id in dst_variant_ids]
        sap_move = [r for r in src_sap if r.variant_id not in dst_sap_variant_ids]
        sap_drop = [r for r in src_sap if r.variant_id in dst_sap_variant_ids]

        self.stdout.write(
            f'Źródło {src_name!r} (id={src.id}) → {dst_name!r} (id={dst.id})\n'
            f'  PVS: {len(pvs_move)} do przeniesienia, {len(pvs_drop)} zdublowanych do usunięcia\n'
            f'  StockAndPrices: {len(sap_move)} do przeniesienia, {len(sap_drop)} zdublowanych do usunięcia'
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('[dry-run] bez zapisu.'))
            return

        with transaction.atomic(using=db):
            for r in pvs_move:
                ProductvariantsSources.objects.using(db).filter(pk=r.pk).update(source_id=dst.id)
            ProductvariantsSources.objects.using(db).filter(
                pk__in=[r.pk for r in pvs_drop]
            ).delete()
            for r in sap_move:
                StockAndPrices.objects.using(db).filter(pk=r.pk).update(source_id=dst.id)
            StockAndPrices.objects.using(db).filter(
                pk__in=[r.pk for r in sap_drop]
            ).delete()

            still_used = (
                ProductvariantsSources.objects.using(db).filter(source_id=src.id).exists()
                or StockAndPrices.objects.using(db).filter(source_id=src.id).exists()
            )
            if still_used:
                self.stdout.write(self.style.WARNING(
                    f'Źródło {src_name!r} nadal ma powiązania — rekordu Sources nie usuwam.'
                ))
            else:
                Sources.objects.using(db).filter(pk=src.id).delete()
                self.stdout.write(self.style.SUCCESS(f'Usunięto pusty rekord Sources {src_name!r}.'))

        self.stdout.write(self.style.SUCCESS('Gotowe.'))
