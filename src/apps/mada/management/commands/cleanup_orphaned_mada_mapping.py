"""
Czyści osierocone mapowania Mada -> MPD: rekordy, w ktorych mapped_product_uid
lub mapped_variant_uid wskazuje na produkt/wariant MPD, ktory juz nie istnieje.

Powod: sygnal post_delete na Products czyscil mapowanie tylko w Matterhorn i
Tabu (patrz MPD/signals.py). Produkty MPD usuniete przed poprawka zostawily w
Mada wpisy wskazujace na nieistniejace ID. Ta komenda to jednorazowe
sprzatanie historii.

Uzycie:
  python manage.py cleanup_orphaned_mada_mapping --dry-run
  python manage.py cleanup_orphaned_mada_mapping
"""
from django.core.management.base import BaseCommand

from core.db_routers import _get_mada_db, _get_mpd_db
from mada.models import MadaProduct, MadaProductVariant
from MPD.models import Products, ProductVariants


class Command(BaseCommand):
    help = 'Czysci osierocone mapped_product_uid / mapped_variant_uid w Mada (produkt MPD juz nie istnieje).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Tylko pokaz ile rekordow zostaloby wyczyszczonych, bez zapisu.',
        )

    def handle(self, *args, **options):
        mada_db = _get_mada_db()
        mpd_db = _get_mpd_db()
        dry_run = options['dry_run']

        # --- Produkty ---
        mapped_product_uids = set(
            MadaProduct.objects.using(mada_db)
            .filter(mapped_product_uid__isnull=False)
            .values_list('mapped_product_uid', flat=True)
        )
        existing_product_ids = set(
            Products.objects.using(mpd_db)
            .filter(id__in=mapped_product_uids)
            .values_list('id', flat=True)
        )
        orphan_product_uids = mapped_product_uids - existing_product_ids
        orphan_products_qs = MadaProduct.objects.using(mada_db).filter(
            mapped_product_uid__in=orphan_product_uids
        )
        orphan_products_count = orphan_products_qs.count() if orphan_product_uids else 0

        # --- Warianty ---
        mapped_variant_uids = set(
            MadaProductVariant.objects.using(mada_db)
            .filter(mapped_variant_uid__isnull=False)
            .values_list('mapped_variant_uid', flat=True)
        )
        existing_variant_ids = set(
            ProductVariants.objects.using(mpd_db)
            .filter(variant_id__in=mapped_variant_uids)
            .values_list('variant_id', flat=True)
        )
        orphan_variant_uids = mapped_variant_uids - existing_variant_ids
        orphan_variants_qs = MadaProductVariant.objects.using(mada_db).filter(
            mapped_variant_uid__in=orphan_variant_uids
        )
        orphan_variants_count = orphan_variants_qs.count() if orphan_variant_uids else 0

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[dry-run] Osierocone produkty Mada: {orphan_products_count} '
                f'(mapped_product_uid: {sorted(orphan_product_uids)})'
            ))
            self.stdout.write(self.style.WARNING(
                f'[dry-run] Osierocone warianty Mada: {orphan_variants_count} '
                f'(mapped_variant_uid: {sorted(orphan_variant_uids)})'
            ))
            return

        if orphan_products_count == 0 and orphan_variants_count == 0:
            self.stdout.write(self.style.SUCCESS('Brak osieroconych mapowan Mada.'))
            return

        if orphan_products_count:
            updated = orphan_products_qs.update(mapped_product_uid=None)
            self.stdout.write(self.style.SUCCESS(
                f'Wyczyszczono mapped_product_uid w {updated} produktach Mada.'
            ))
        if orphan_variants_count:
            updated = orphan_variants_qs.update(mapped_variant_uid=None, is_mapped=False)
            self.stdout.write(self.style.SUCCESS(
                f'Wyczyszczono mapped_variant_uid w {updated} wariantach Mada.'
            ))
