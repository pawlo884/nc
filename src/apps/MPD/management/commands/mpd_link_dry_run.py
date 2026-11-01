"""
Dry run dopinania produktu między hurtowniami (tylko odczyt, nic nie zapisuje).

Użycie:
  python manage.py mpd_link_dry_run --term Jessia --term 1229 [--term beige]

Szuka w każdej hurtowni (Tabu, Mada, Matterhorn) produktów, których nazwa
zawiera WSZYSTKIE podane frazy (bez wielkości liter), wypisuje ich warianty
z EAN-ami, a potem dla każdego EAN-u pokazuje:
  * w których hurtowniach występuje,
  * czy MPD ma już wariant z tym EAN-em (ProductVariants.ean albo
    ProductvariantsSources.ean) i w jakim produkcie.

To jest dokładnie to, po czym link_variants_from_other_sources dopina warianty
po dodaniu produktu do MPD: wspólny EAN = wariant dopięty z innej hurtowni.
"""
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from MPD.models import ProductVariants, ProductvariantsSources
from MPD.source_adapters.base import normalize_ean
from MPD.source_adapters.linking import _get_mpd_db


def _wholesalers():
    """(nazwa, model produktu, baza, adapter) dla każdej hurtowni."""
    from core.db_routers import _get_mada_db, _get_matterhorn1_db, _get_tabu_db
    from mada.models import MadaProduct
    from matterhorn1.models import Product as MatterhornProduct
    from MPD.source_adapters.mada import MadaAdapter
    from MPD.source_adapters.matterhorn import MatterhornAdapter
    from MPD.source_adapters.tabu import TabuAdapter
    from tabu.models import TabuProduct

    return [
        ('Tabu', TabuProduct, _get_tabu_db(), TabuAdapter(source_id=0)),
        ('Mada', MadaProduct, _get_mada_db(), MadaAdapter(source_id=0)),
        ('Matterhorn', MatterhornProduct, _get_matterhorn1_db(), MatterhornAdapter(source_id=0)),
    ]


class Command(BaseCommand):
    help = 'Dry run: czy produkt z jednej hurtowni dopnie warianty z innych (po EAN). Tylko odczyt.'

    def add_arguments(self, parser):
        parser.add_argument('--term', action='append', required=True,
                            help='Fraza w nazwie produktu (można podać kilka, łączone AND)')
        parser.add_argument('--limit', type=int, default=20,
                            help='Maks. liczba produktów na hurtownię (domyślnie 20)')

    def handle(self, *args, **opts):
        terms = [t for t in opts['term'] if t.strip()]
        if not terms:
            raise CommandError('Podaj co najmniej jedno --term')
        q = Q()
        for t in terms:
            q &= Q(name__icontains=t.strip())

        out = self.stdout.write
        ean_sources = defaultdict(list)  # ean -> [(hurtownia, produkt, kolor, rozmiar)]

        for label, model, db, adapter in _wholesalers():
            try:
                products = list(model.objects.using(db).filter(q).order_by('pk')[:opts['limit']])
            except Exception as e:  # brak bazy danej hurtowni lokalnie
                out(self.style.WARNING(f'\n[{label}] pominięto: {e}'))
                continue
            out(self.style.MIGRATE_HEADING(f'\n[{label}] produktów: {len(products)}'))
            for p in products:
                color = getattr(p, 'color', '') or ''
                out(f'  #{p.pk} {p.name}'
                    f'{f" | kolor: {color}" if color else ""}'
                    f' | w MPD: {p.mapped_product_uid or "-"}')
                for v in adapter.get_all_variants_for_product(p.pk):
                    ean = normalize_ean(v.ean)
                    out(f'      rozmiar {v.size or "?":<8} kolor {v.color or color or "?":<12} '
                        f'EAN {ean or "(brak)"}')
                    if ean:
                        ean_sources[ean].append((label, p.pk, v.color or color, v.size))

        if not ean_sources:
            out(self.style.WARNING('\nBrak EAN-ów - nie ma po czym dopinać.'))
            return

        mpd = _get_mpd_db()
        eans = list(ean_sources)
        in_mpd = defaultdict(set)  # ean -> {(product_id, variant_id)}
        for vid, pid, ean in ProductVariants.objects.using(mpd).filter(
                ean__in=[e.upper() for e in eans] + eans).values_list('variant_id', 'product_id', 'ean'):
            in_mpd[normalize_ean(ean)].add((pid, vid))
        for vid, pid, ean in ProductvariantsSources.objects.using(mpd).filter(
                ean__in=eans).values_list('variant_id', 'variant__product_id', 'ean'):
            in_mpd[normalize_ean(ean)].add((pid, vid))

        out(self.style.MIGRATE_HEADING('\n=== EAN-y: hurtownie i MPD ==='))
        shared = 0
        for ean in sorted(eans):
            whs = sorted({w for w, *_ in ean_sources[ean]})
            if len(whs) > 1:
                shared += 1
            mpd_txt = ', '.join(f'produkt {p}/wariant {v}' for p, v in sorted(in_mpd[ean])) or 'brak'
            out(f'  {ean}: {" + ".join(whs):<24} MPD: {mpd_txt}')

        mpd_products = {p for s in in_mpd.values() for p, _ in s}
        out(self.style.MIGRATE_HEADING('\n=== Wniosek ==='))
        out(f'  EAN-ów: {len(eans)}, wspólnych dla >1 hurtowni: {shared}')
        if shared:
            out('  Po dodaniu produktu z jednej hurtowni warianty ze wspólnym EAN-em '
                'zostaną dopięte z pozostałych.')
        else:
            out('  Żaden EAN nie powtarza się między hurtowniami - nic się nie dopnie automatycznie.')
        if len(mpd_products) > 1:
            out(self.style.WARNING(f'  UWAGA: te EAN-y są już w {len(mpd_products)} różnych produktach MPD: '
                                   f'{sorted(mpd_products)}'))
        elif mpd_products:
            out(f'  Produkt jest już w MPD (id {mpd_products.pop()}).')
        else:
            out('  Produktu jeszcze nie ma w MPD.')
