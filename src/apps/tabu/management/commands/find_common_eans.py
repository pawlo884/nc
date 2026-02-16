"""
Znajduje kody EAN występujące w obu bazach: Tabu i Matterhorn.

To nie duplikaty – EAN może (i powinien) występować w obu systemach.
Narzędzie służy do wyszukiwania dopasowań / wspólnych EAN między hurtowniami.

Źródła:
- Tabu: TabuProduct.ean, TabuProductVariant.ean
- Matterhorn: ProductVariant.ean

Użycie:
  python manage.py find_common_eans --settings=core.settings.dev
  python manage.py find_common_eans --output ean_matches.csv --settings=core.settings.dev
  python manage.py find_common_eans --format json --settings=core.settings.dev
"""
import json

from django.core.management.base import BaseCommand

from tabu.models import TabuProduct, TabuProductVariant
from matterhorn1.models import ProductVariant


class Command(BaseCommand):
    help = 'Znajduje EANy występujące w Tabu i Matterhorn (dopasowania między hurtowniami)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', '-o',
            type=str,
            default=None,
            help='Ścieżka do pliku wyjściowego (CSV lub JSON w zależności od --format)',
        )
        parser.add_argument(
            '--format', '-f',
            choices=['table', 'json', 'csv'],
            default='table',
            help='Format wyjścia: table (domyślny), json, csv',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Pokaż szczegóły (nazwy produktów, variant_uid)',
        )

    def handle(self, *args, **options):
        output_path = options.get('output')
        fmt = options.get('format')
        verbose = options.get('verbose')

        # EANy z Tabu (produkt + warianty)
        tabu_eans = {}  # ean -> [(source, product_id/name, details)]
        for p in TabuProduct.objects.all().only('id', 'name', 'symbol', 'ean'):
            ean = (p.ean or '').strip()
            if ean:
                tabu_eans.setdefault(ean, []).append(('TabuProduct', p.name or p.symbol or str(p.id), f'id={p.id}'))
        for v in TabuProductVariant.objects.select_related('product').all().only('id', 'ean', 'product'):
            ean = (v.ean or '').strip()
            if ean:
                prod_name = v.product.name if v.product else str(v.id)
                tabu_eans.setdefault(ean, []).append(('TabuProductVariant', prod_name, f'variant_id={v.id}'))

        # EANy z Matterhorn
        matterhorn_eans = {}
        for v in ProductVariant.objects.select_related('product').all().only('id', 'ean', 'name', 'variant_uid', 'product'):
            ean = (v.ean or '').strip()
            if ean:
                prod_name = v.product.name if v.product else '-'
                matterhorn_eans.setdefault(ean, []).append({
                    'variant_uid': v.variant_uid,
                    'name': v.name,
                    'product_name': prod_name,
                })

        # Przecięcie – EANy w obu bazach
        common_eans = sorted(set(tabu_eans.keys()) & set(matterhorn_eans.keys()))

        # Wyniki (konwersja tuple -> list dla JSON)
        rows = []
        for ean in common_eans:
            tabu_info = [{'source': s, 'product': p, 'details': d} for s, p, d in tabu_eans[ean]]
            mh_info = matterhorn_eans[ean]
            rows.append({
                'ean': ean,
                'tabu_sources': tabu_info,
                'matterhorn_sources': mh_info,
            })

        # Wyjście
        if output_path and fmt == 'table':
            if output_path.lower().endswith('.json'):
                fmt = 'json'
            else:
                fmt = 'csv'

        if fmt == 'json':
            out = json.dumps(rows, ensure_ascii=False, indent=2)
        elif fmt == 'csv':
            lines = []
            if verbose:
                lines.append(['EAN', 'Tabu_źródła', 'Matterhorn_info'])
                for r in rows:
                    tabu_str = '; '.join(f"{t['source']}: {t['product']}" for t in r['tabu_sources'])
                    mh_str = '; '.join(f"{m.get('variant_uid', '')} ({m.get('product_name', '')})" for m in r['matterhorn_sources'])
                    lines.append([r['ean'], tabu_str, mh_str])
            else:
                lines.append(['EAN', 'Tabu_count', 'Matterhorn_count'])
                for r in rows:
                    lines.append([r['ean'], len(r['tabu_sources']), len(r['matterhorn_sources'])])
            buf = []
            for row in lines:
                buf.append(','.join(f'"{str(c).replace(chr(34), chr(34)+chr(34))}"' for c in row))
            out = '\n'.join(buf)
        else:
            # table
            out_lines = [
                '',
                f'EANy występujące w obu bazach (Tabu i Matterhorn): {len(common_eans)}',
                '',
            ]
            for r in rows:
                out_lines.append(f"  EAN: {r['ean']}")
                if verbose:
                    for t in r['tabu_sources']:
                        out_lines.append(f"    Tabu ({t['source']}): {t['product']} [{t['details']}]")
                    for mh in r['matterhorn_sources']:
                        out_lines.append(f"    Matterhorn: {mh.get('product_name', '')} / {mh.get('name', '')} (variant_uid={mh.get('variant_uid', '')})")
                out_lines.append('')
            out = '\n'.join(out_lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(out)
            self.stdout.write(self.style.SUCCESS(f'Zapisano do {output_path}'))
        else:
            self.stdout.write(out)

        self.stdout.write(self.style.SUCCESS(f'\nPodsumowanie: {len(common_eans)} EANów w obu bazach'))
