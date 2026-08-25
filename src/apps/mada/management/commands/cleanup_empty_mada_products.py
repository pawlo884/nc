"""
Usuwa "puste" produkty Mada - rekordy bez NAME (a wiec bez PRICE/PRODUCER/
CATEGORIES) w products.xml. Feed Mada zawiera takie wpisy trwale (nie jest
to stan przejsciowy w trakcie parsowania - upsert_product zapisuje caly
produkt jednym update_or_create) - prawdopodobnie produkty wycofane
z oferty, ale nadal raportowane w feedzie ze wzgledu na EAN/stan.

Bezpieczenstwo: filtrujemy dodatkowo po mapped_product_uid__isnull=True,
zeby nigdy nie ruszyc produktu, ktory mimo pustej nazwy zdazyl zostac
zmapowany do MPD. CASCADE kasuje tez powiazane warianty/zdjecia. Jesli
produkt pojawi sie pozniej w feedzie z uzupelnionymi danymi, kolejny
sync_mada_full po prostu go odtworzy (update_or_create po api_id).

Uzycie:
  python manage.py cleanup_empty_mada_products --dry-run
  python manage.py cleanup_empty_mada_products
"""
from django.core.management.base import BaseCommand
from django.db import router
from django.db.models import Q

from mada.models import MadaProduct


class Command(BaseCommand):
    help = 'Usuwa puste produkty Mada (bez NAME w feedzie, nigdy nie zmapowane do MPD).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Tylko pokaz ile produktow zostaloby usunietych, bez usuwania.',
        )

    def handle(self, *args, **options):
        db = router.db_for_write(MadaProduct)
        qs = MadaProduct.objects.using(db).filter(
            Q(name='') | Q(name__isnull=True),
            mapped_product_uid__isnull=True,
        )
        count = qs.count()

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                f'[dry-run] Znaleziono {count} pustych produktow Mada do usuniecia.'
            ))
            return

        if count == 0:
            self.stdout.write(self.style.SUCCESS('Brak pustych produktow Mada do usuniecia.'))
            return

        deleted_total, details = qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f'Usunieto {count} pustych produktow Mada '
            f'(lacznie z powiazanymi rekordami: {deleted_total}).'
        ))
        for model_label, n in details.items():
            self.stdout.write(f'  - {model_label}: {n}')
