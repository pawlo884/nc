"""
Integration: `sync_tabu_stock` — aktualizacja stanów/cen z `GET products/basic`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db import connections
from django.test.utils import CaptureQueriesContext

from tabu.models import ApiSyncLog, StockHistory, TabuProduct, TabuProductVariant
from tabu.management.commands.sync_tabu_stock import Command

from . import factories
from .mock_tabu import mock_products_basic

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestApplyStockUpdates:
    """`Command._apply_stock_updates` — batch, warunkowy UPDATE, store_total z sumy."""

    @pytest.fixture
    def cmd(self):
        return Command()

    def test_zmiana_stanu_aktualizuje_wariant_produkt_i_pisze_historie(self, cmd):
        p = factories.tabu_product(api_id=1000, store_total=5)
        v = factories.tabu_variant(p, api_id=2000, store=5)

        hist, compared, changed, failed = cmd._apply_stock_updates([
            factories.basic_record(product_api_id=1000, variant_api_id=2000, store=2)])

        assert (hist, compared, changed, failed) == (1, 1, 1, 0)
        v.refresh_from_db()
        p.refresh_from_db()
        assert v.store == 2
        assert p.store_total == 2  # suma wariantów produktu
        h = StockHistory.objects.get(variant_api_id=2000)
        assert (h.old_stock, h.new_stock, h.change_type) == (5, 2, "decrease")

    def test_brak_zmiany_stanu_bez_historii(self, cmd):
        p = factories.tabu_product(api_id=1001)
        factories.tabu_variant(p, api_id=2001, store=7)

        assert cmd._apply_stock_updates([
            factories.basic_record(product_api_id=1001, variant_api_id=2001, store=7)
        ]) == (0, 1, 0, 0)
        assert StockHistory.objects.count() == 0

    def test_nieznany_wariant_jest_pomijany(self, cmd):
        assert cmd._apply_stock_updates([
            factories.basic_record(product_api_id=9, variant_api_id=999999, store=1)
        ]) == (0, 0, 0, 0)

    def test_brak_variant_id_pomijany(self, cmd):
        assert cmd._apply_stock_updates([{"id": 1, "store": 3}]) == (0, 0, 0, 0)

    def test_aktualizuje_ceny_gdy_podane_bez_zmiany_stanu(self, cmd):
        p = factories.tabu_product(api_id=1002)
        v = factories.tabu_variant(p, api_id=2002, store=1, price_net="10.00")

        cmd._apply_stock_updates([factories.basic_record(
            product_api_id=1002, variant_api_id=2002, store=1,
            price_net="19.99", price_gross="24.59")])

        v.refresh_from_db()
        assert v.price_net == Decimal("19.99")
        assert v.price_gross == Decimal("24.59")

    def test_store_total_z_sumy_wariantow_bez_dryfu(self, cmd):
        # store_total w bazie zawyżony (dryf), fix policzy go z sumy wariantów
        p = factories.tabu_product(api_id=1003, store_total=999)
        factories.tabu_variant(p, api_id=3001, store=4)
        v2 = factories.tabu_variant(p, api_id=3002, store=6)

        cmd._apply_stock_updates([
            factories.basic_record(product_api_id=1003, variant_api_id=3002, store=1)])

        p.refresh_from_db()
        assert p.store_total == 5  # 4 (bez zmian) + 1 (nowy) — nie 999, nie przyrostowo

    def test_idempotencja_drugi_run_nie_powiela_historii(self, cmd):
        p = factories.tabu_product(api_id=1004)
        factories.tabu_variant(p, api_id=4001, store=8)
        rec = [factories.basic_record(product_api_id=1004, variant_api_id=4001, store=2)]

        assert cmd._apply_stock_updates(rec)[0] == 1
        assert cmd._apply_stock_updates(rec)[0] == 0  # stan już 2 → nic
        assert StockHistory.objects.filter(variant_api_id=4001).count() == 1

    def test_zapytania_nie_rosna_liniowo_z_liczba_wariantow(self, cmd):
        p = factories.tabu_product(api_id=1005)
        for i in range(20):
            factories.tabu_variant(p, api_id=5000 + i, store=10)
        # połowa się zmienia
        recs = [
            factories.basic_record(product_api_id=1005, variant_api_id=5000 + i,
                                   store=3 if i % 2 == 0 else 10)
            for i in range(20)
        ]

        with CaptureQueriesContext(connections["default"]) as ctx:
            hist, compared, changed, failed = cmd._apply_stock_updates(recs)

        assert (hist, compared) == (10, 20)
        # 1 SELECT wariantów + 10 warunkowych UPDATE + agregat store_total +
        # SELECT produktów + bulk_update produktów + bulk_create historii.
        # Rośnie ze ZMIENIONYMI (10), nie z 20 w danych.
        assert len(ctx.captured_queries) < 20, (
            f"{len(ctx.captured_queries)} zapytań dla 20 wariantów (10 zmian)"
        )

    def test_przetwarza_porcjami_bez_ladowania_wszystkiego_naraz(self, cmd, monkeypatch):
        """`_CHUNK` mały → rekordy przekraczające jedną porcję są poprawnie
        przetworzone (ochrona przed OOM przy ~10k+ wariantów)."""
        monkeypatch.setattr(cmd, "_CHUNK", 3)
        p = factories.tabu_product(api_id=1006, store_total=0)
        for i in range(10):
            factories.tabu_variant(p, api_id=6000 + i, store=1)

        # lean krotki (tak jak `handle` po redukcji), wszystkie ze zmianą 1 → 5
        lean = [(6000 + i, 5, None, None) for i in range(10)]
        hist, compared, changed, failed = cmd._apply_stock_updates(lean)

        assert (hist, compared, changed, failed) == (10, 10, 10, 0)
        assert TabuProductVariant.objects.filter(product=p, store=5).count() == 10
        assert StockHistory.objects.filter(product_api_id=p.api_id).count() == 10
        p.refresh_from_db()
        assert p.store_total == 50   # store_total z sumy po wszystkich porcjach


class TestSyncTabuStockCommand:
    """Pełny przebieg `call_command('sync_tabu_stock', ...)`."""

    def _run(self, **extra):
        call_command(
            "sync_tabu_stock", "--api-url", "https://tabu.test",
            "--api-key", "test-key", **extra)

    def test_pelny_przebieg_aktualizuje_i_loguje(self, tabu_api, mocked_responses):
        p = factories.tabu_product(api_id=1, store_total=10)
        factories.tabu_variant(p, api_id=11, store=5)
        factories.tabu_variant(p, api_id=12, store=5)
        mock_products_basic(mocked_responses, tabu_api, [
            [
                factories.basic_record(product_api_id=1, variant_api_id=11, store=3),
                factories.basic_record(product_api_id=1, variant_api_id=12, store=0),
            ],
            [],
        ])

        self._run(**{"update_from": "2026-01-01 00:00:00"})

        assert TabuProductVariant.objects.get(api_id=11).store == 3
        assert TabuProductVariant.objects.get(api_id=12).store == 0
        assert StockHistory.objects.count() == 2
        log = ApiSyncLog.objects.filter(sync_type="stock_update").latest("started_at")
        assert log.status == "completed"
        assert log.products_processed == 2

    def test_ta_sama_liczba_ale_inne_dane_NIE_pomija(self, tabu_api, mocked_responses):
        # #233 pkt 2: dawniej "ta sama liczba rekordów" = skip, co gubiło
        # realne zmiany innych wariantów. Teraz liczy się odcisk DANYCH.
        ApiSyncLog.objects.create(
            sync_type="stock_update", status="completed", products_processed=1,
            raw_response={"fetch_fingerprint": "cos-zupelnie-innego"})
        p = factories.tabu_product(api_id=2)
        factories.tabu_variant(p, api_id=21, store=5)
        mock_products_basic(mocked_responses, tabu_api, [
            [factories.basic_record(product_api_id=2, variant_api_id=21, store=1)],
            [],
        ])

        self._run(**{"update_from": "2026-01-01 00:00:00"})

        assert TabuProductVariant.objects.get(api_id=21).store == 1  # zmiana zastosowana
        assert StockHistory.objects.count() == 1

    def test_identyczne_dane_jak_poprzednio_pomija_run(self, tabu_api, mocked_responses):
        p = factories.tabu_product(api_id=3)
        factories.tabu_variant(p, api_id=31, store=9)
        pages = [
            [factories.basic_record(product_api_id=3, variant_api_id=31, store=4)],
            [],
        ]
        mock_products_basic(mocked_responses, tabu_api, pages)
        # 1. run: stosuje 9->4, zapisuje odcisk
        self._run(**{"update_from": "2026-01-01 00:00:00"})
        assert TabuProductVariant.objects.get(api_id=31).store == 4
        StockHistory.objects.all().delete()

        # 2. run: API zwraca DOKŁADNIE to samo -> pomijamy
        mock_products_basic(mocked_responses, tabu_api, pages)
        self._run(**{"update_from": "2026-01-02 00:00:00"})

        assert StockHistory.objects.count() == 0
        log = ApiSyncLog.objects.filter(sync_type="stock_update").latest("started_at")
        assert log.raw_response.get("skipped_reason") == "identical_fetch_as_previous_run"
