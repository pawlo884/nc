"""
Integration: `mada.tasks.watchdog_import_healthcheck` — siatka bezpieczeństwa
sprzątająca ApiSyncLog utknięte w `running` (#267), niezależna od tego czy
kolejny przebieg w ogóle się odpali (samo-leczenie w sync_mada_full/partial
działa dopiero na starcie następnego runu).

Celery Beat woła to co 5 min.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from mada.models import ApiSyncLog
from mada.tasks import watchdog_import_healthcheck

pytestmark = pytest.mark.django_db


def _running(sync_type: str, minutes_ago: int) -> ApiSyncLog:
    row = ApiSyncLog.objects.create(sync_type=sync_type, status="running")
    ApiSyncLog.objects.filter(pk=row.pk).update(
        started_at=timezone.now() - timedelta(minutes=minutes_ago))
    row.refresh_from_db()
    return row


@pytest.mark.parametrize("sync_type, stale_minutes", [
    ("partial_import", 61),
    ("full_import", 181),
])
def test_stary_running_oznaczany_jako_failed(sync_type, stale_minutes):
    stale = _running(sync_type, stale_minutes)

    watchdog_import_healthcheck.apply()

    stale.refresh_from_db()
    assert stale.status == "failed"
    assert stale.completed_at is not None
    assert "Watchdog" in stale.error_message


@pytest.mark.parametrize("sync_type, fresh_minutes", [
    ("partial_import", 30),
    ("full_import", 60),
])
def test_swiezy_running_nie_jest_ruszany(sync_type, fresh_minutes):
    fresh = _running(sync_type, fresh_minutes)

    watchdog_import_healthcheck.apply()

    fresh.refresh_from_db()
    assert fresh.status == "running"


def test_zwraca_liczbe_posprzatanych():
    _running("partial_import", 61)
    _running("full_import", 181)
    _running("full_import", 10)  # świeży - nie liczy się

    result = watchdog_import_healthcheck.apply().get()

    assert result == {"status": "success", "cleaned": 2}
