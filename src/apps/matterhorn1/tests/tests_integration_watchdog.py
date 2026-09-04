"""
Integration: `matterhorn1.tasks.watchdog_import_healthcheck` — sprząta
zawieszone importy ITEMS (status `running` bez postępu > 15 min → `error`).

Celery Beat woła to co 5 min.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from matterhorn1.models import ApiSyncLog
from matterhorn1.tasks import watchdog_import_healthcheck

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases=["default", "matterhorn1"])]


def _running_import(minutes_ago: int, **fields) -> ApiSyncLog:
    row = ApiSyncLog.objects.create(sync_type="items_import", status="running", **fields)
    ApiSyncLog.objects.filter(pk=row.pk).update(
        started_at=timezone.now() - timedelta(minutes=minutes_ago))
    row.refresh_from_db()
    return row


def test_ghost_task_bez_postepu_oznaczony_jako_error():
    ghost = _running_import(20)  # 20 min, zero postępu

    watchdog_import_healthcheck.apply()

    ghost.refresh_from_db()
    assert ghost.status == "error"
    assert "Ghost" in (ghost.error_details or "")


def test_swiezy_running_nie_jest_ruszany():
    fresh = _running_import(5)  # < 15 min

    watchdog_import_healthcheck.apply()

    fresh.refresh_from_db()
    assert fresh.status == "running"


def test_stary_running_z_postepem_nie_jest_ghostem():
    working = _running_import(20, records_created=120, current_page=3)

    watchdog_import_healthcheck.apply()

    working.refresh_from_db()
    # ma postęp → nie jest oznaczany jako ghost (brak wartości)
    assert working.error_details != "Ghost task - brak postępu przez 15 minut"
