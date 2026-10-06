"""
Integration: `tabu.tasks` — cienkie wrappery Celery wokół komend zarządzania.
Kluczowe: advisory lock w `sync_tabu_stock` (skip gdy nie zdobyty) i wybór
`update_from` z ostatniego `ApiSyncLog`.
"""
from __future__ import annotations

import contextlib
from datetime import timedelta
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.utils import timezone

from tabu import tasks
from tabu.models import ApiSyncLog

pytestmark = pytest.mark.django_db


@contextlib.contextmanager
def _lock(acquired):
    yield acquired


class TestSyncTabuStockTask:
    def test_skip_gdy_lock_nie_zdobyty(self):
        with patch.object(tasks, "advisory_lock", lambda name: _lock(False)), \
                patch.object(tasks, "call_command") as cc:
            result = tasks.sync_tabu_stock.apply().get()

        assert result == {"status": "skipped", "reason": "already_running"}
        cc.assert_not_called()

    def test_brak_poprzedniego_synca_update_from_24h_wstecz(self):
        with patch.object(tasks, "advisory_lock", lambda name: _lock(True)), \
                patch.object(tasks, "call_command") as cc:
            result = tasks.sync_tabu_stock.apply().get()

        assert result["status"] == "ok"
        cc.assert_called_once()
        args = cc.call_args[0]
        assert args[0] == "sync_tabu_stock" and args[1] == "--update-from"
        # ~24 h wstecz (tolerancja)
        assert "update_from" in result

    def test_update_from_z_ostatniego_logu(self):
        ts = timezone.now() - timedelta(hours=3)
        log = ApiSyncLog.objects.create(sync_type="stock_update", status="completed")
        ApiSyncLog.objects.filter(pk=log.pk).update(started_at=ts)

        with patch.object(tasks, "advisory_lock", lambda name: _lock(True)), \
                patch.object(tasks, "call_command") as cc:
            result = tasks.sync_tabu_stock.apply().get()

        assert result["update_from"] == ts.strftime("%Y-%m-%d %H:%M:%S")
        assert cc.call_args[0][2] == ts.strftime("%Y-%m-%d %H:%M:%S")

    def test_update_from_ignoruje_niezakonczone_logi(self):
        # ostatni udany run 5 h temu; potem run 'failed' 1 h temu (nie zdążył
        # zaimportować swojego okna) → update_from ma się cofnąć do udanego.
        good = timezone.now() - timedelta(hours=5)
        bad = timezone.now() - timedelta(hours=1)
        g = ApiSyncLog.objects.create(sync_type="stock_update", status="completed")
        ApiSyncLog.objects.filter(pk=g.pk).update(started_at=good)
        b = ApiSyncLog.objects.create(sync_type="stock_update", status="failed")
        ApiSyncLog.objects.filter(pk=b.pk).update(started_at=bad)

        with patch.object(tasks, "advisory_lock", lambda name: _lock(True)), \
                patch.object(tasks, "call_command") as cc:
            result = tasks.sync_tabu_stock.apply().get()

        assert result["update_from"] == good.strftime("%Y-%m-%d %H:%M:%S")

    def test_blad_komendy_powoduje_retry(self):
        with patch.object(tasks, "advisory_lock", lambda name: _lock(True)), \
                patch.object(tasks, "call_command", side_effect=RuntimeError("boom")), \
                pytest.raises(Retry):
            tasks.sync_tabu_stock.apply(throw=True)


class TestOtherTasks:
    def test_watchdog_to_noop(self):
        assert tasks.watchdog_tabu_stock_lock.apply().get()["status"] == "ok"

    def test_products_update_woła_komendę(self):
        with patch.object(tasks, "call_command") as cc:
            assert tasks.sync_tabu_products_update.apply().get() == {"status": "ok"}
        cc.assert_called_once_with("sync_tabu_new_products")

    def test_categories_woła_komendę(self):
        with patch.object(tasks, "call_command") as cc:
            assert tasks.sync_tabu_categories_task.apply().get() == {"status": "ok"}
        cc.assert_called_once_with("sync_tabu_categories")
