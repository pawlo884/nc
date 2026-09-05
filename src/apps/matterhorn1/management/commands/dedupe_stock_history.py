"""
Czyści zduplikowane wpisy w `matterhorn1_stock_history`, które powstały przy
nakładających się runach importu INVENTORY (beat + redeliver ubitego taska)
- ta sama zmiana stanu zapisana kilka razy w krótkim odstępie.

Kod importu jest już idempotentny (warunkowy UPDATE w `_bulk_update_inventory`),
ta komenda sprząta HISTORYCZNE duplikaty.

Kryterium duplikatu (konserwatywne - nie rusza legalnych powtórzeń zmiany):
dla danego wariantu, kolejne wpisy (po timestamp) o IDENTYCZNYM przejściu
`old_stock -> new_stock`, których timestamp mieści się w oknie od pierwszego
z serii. Legalne powtórzenie tego samego przejścia wymaga wpisu odwrotnego
pomiędzy (żeby stan wrócił), więc dwa takie same przejścia pod rząd bez
niczego pomiędzy = duplikat. Okno czasowe chroni przed usunięciem realnych
powtórzeń oddalonych o godziny/dni (gdy wpis odwrotny gdzieś przepadł).

Domyślnie DRY-RUN. Realne usunięcie: --execute.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand

from core.db_routers import _get_matterhorn1_db
from matterhorn1.models import StockHistory


class Command(BaseCommand):
    help = "Usuwa zduplikowane wpisy StockHistory z nakładających się runów importu"

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute', action='store_true',
            help='Faktycznie usuń (bez tego tylko raport - dry run)')
        parser.add_argument(
            '--window-minutes', type=int, default=15,
            help='Maksymalny odstęp od pierwszego wpisu z serii, by uznać kolejny '
                 'za duplikat (domyślnie 15 - obejmuje cykl beat 10 min + opóźnienie; '
                 'szersze okno łapie też re-recordy z buga transakcji, ale mniej pewnie)')
        parser.add_argument(
            '--limit-sample', type=int, default=20,
            help='Ile przykładowych duplikatów wypisać')

    def handle(self, *args, **opts):
        db = _get_matterhorn1_db()
        window = timedelta(minutes=opts['window_minutes'])
        execute = opts['execute']

        qs = (StockHistory.objects.using(db)
              .order_by('variant_uid', 'timestamp', 'id')
              .values('id', 'variant_uid', 'old_stock', 'new_stock',
                      'change_type', 'timestamp', 'product_name'))

        dup_ids = []
        samples = []
        prev = None          # poprzedni wpis (dowolny) dla tego wariantu
        keeper = None        # pierwszy wpis bieżącej serii identycznych przejść

        for row in qs.iterator(chunk_size=5000):
            same_variant = prev is not None and row['variant_uid'] == prev['variant_uid']
            same_transition = (
                same_variant
                and row['old_stock'] == prev['old_stock']
                and row['new_stock'] == prev['new_stock']
            )

            if same_transition and keeper is not None and \
                    row['timestamp'] - keeper['timestamp'] <= window:
                dup_ids.append(row['id'])
                if len(samples) < opts['limit_sample']:
                    samples.append((keeper, row))
            elif same_transition and keeper is not None:
                # to samo przejście, ale poza oknem - traktujemy jako nowy keeper
                keeper = row
            else:
                keeper = row

            prev = row

        total = StockHistory.objects.using(db).count()
        self.stdout.write(
            f"StockHistory: {total} wpisów, znaleziono {len(dup_ids)} duplikatów "
            f"(okno {opts['window_minutes']} min)")

        for keeper, dup in samples:
            self.stdout.write(
                f"  keep id={keeper['id']} {keeper['timestamp']:%Y-%m-%d %H:%M:%S}"
                f"  <-  del id={dup['id']} {dup['timestamp']:%H:%M:%S}"
                f"  [{dup['variant_uid']}: {dup['old_stock']}->{dup['new_stock']}"
                f" {dup['product_name']}]")
        if len(dup_ids) > len(samples):
            self.stdout.write(f"  ... i {len(dup_ids) - len(samples)} więcej")

        if not dup_ids:
            self.stdout.write(self.style.SUCCESS("Brak duplikatów do usunięcia"))
            return

        if not execute:
            self.stdout.write(self.style.WARNING(
                "DRY RUN - nic nie usunięto. Uruchom z --execute żeby usunąć."))
            return

        deleted = 0
        for i in range(0, len(dup_ids), 1000):
            batch = dup_ids[i:i + 1000]
            n, _ = StockHistory.objects.using(db).filter(id__in=batch).delete()
            deleted += n
        self.stdout.write(self.style.SUCCESS(f"Usunięto {deleted} zduplikowanych wpisów"))
