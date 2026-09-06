"""
Integration: `sync_tabu_stock` — aktualizacja stanów/cen z `GET products/basic`.

Utrwala OBECNE zachowanie (per-wariant `.get()`/`save()` + `store_total`
przyrostowo + `_should_skip_processing`) jako punkt odniesienia przed
refaktorem (issue #233).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.management import call_command

from tabu.models import ApiSyncLog, StockHistory, TabuProductVariant
from tabu.management.commands.sync_tabu_stock import Command

from . import factories
from .mock_tabu import mock_products_basic

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestUpdateVariant:
    """`Command._update_variant` wołany bezpośrednio."""

    @pytest.fixture
    def cmd(self):
        return Command()

    def test_zmiana_stanu_aktualizuje_wariant_produkt_i_pisze_historie(self, cmd):
        p = factories.tabu_product(api_id=1000, store_total=5)
        v = factories.tabu_variant(p, api_id=2000, store=5)

        hist, compared, changed = cmd._update_variant(
            factories.basic_record(product_api_id=1000, variant_api_id=2000, store=2))

        assert (hist, compared, changed) == (1, 1, 1)
        v.refresh_from_db()
        p.refresh_from_db()
        assert v.store == 2
        assert p.store_total == 2  # 5 - 5 + 2
        h = StockHistory.objects.get(variant_api_id=2000)
        assert (h.old_stock, h.new_stock) == (5, 2)

    def test_brak_zmiany_stanu_bez_historii(self, cmd):
        p = factories.tabu_product(api_id=1001)
        factories.tabu_variant(p, api_id=2001, store=7)

        hist, compared, changed = cmd._update_variant(
            factories.basic_record(product_api_id=1001, variant_api_id=2001, store=7))

        assert (hist, compared, changed) == (0, 1, 0)
        assert StockHistory.objects.count() == 0

    def test_nieznany_wariant_jest_pomijany(self, cmd):
        assert cmd._update_variant(
            factories.basic_record(product_api_id=9, variant_api_id=999999, store=1)
        ) == (0, 0, 0)

    def test_brak_variant_id_pomijany(self, cmd):
        assert cmd._update_variant({"id": 1, "store": 3}) == (0, 0, 0)

    def test_aktualizuje_ceny_gdy_podane(self, cmd):
        p = factories.tabu_product(api_id=1002)
        v = factories.tabu_variant(p, api_id=2002, store=1, price_net="10.00")

        cmd._update_variant(factories.basic_record(
            product_api_id=1002, variant_api_id=2002, store=1,
            price_net="19.99", price_gross="24.59"))

        v.refresh_from_db()
        assert v.price_net == Decimal("19.99")
        assert v.price_gross == Decimal("24.59")


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

    def test_skip_gdy_ta_sama_liczba_rekordow_co_poprzednio(self, tabu_api, mocked_responses):
        # OBECNE zachowanie (znane ograniczenie #233 pkt 2): jeśli poprzedni
        # zakończony run stock_update miał tyle samo `products_processed`,
        # cały bieżący run jest pomijany.
        ApiSyncLog.objects.create(
            sync_type="stock_update", status="completed", products_processed=1)
        p = factories.tabu_product(api_id=2)
        factories.tabu_variant(p, api_id=21, store=5)
        mock_products_basic(mocked_responses, tabu_api, [
            [factories.basic_record(product_api_id=2, variant_api_id=21, store=1)],
            [],
        ])

        self._run(**{"update_from": "2026-01-01 00:00:00"})

        # zmiana 5->1 NIE została zastosowana - run pominięty
        assert TabuProductVariant.objects.get(api_id=21).store == 5
        assert StockHistory.objects.count() == 0
        log = ApiSyncLog.objects.filter(sync_type="stock_update").latest("started_at")
        assert log.raw_response.get("skipped_reason") == "same_count_as_previous_run"
