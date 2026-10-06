"""
Fixture'y wspólne dla testów matterhorn1 (warstwa integration/e2e).

`no_sleep` jest autouse — `matterhorn1.tasks` woła `time.sleep` po każdym
requeście (rate limit 1/s) i przy retry (20 s). Bez tego e2e trwałby minuty.
"""
from __future__ import annotations

import pytest

from matterhorn1.tests import factories

ALL_DBS = ["default", "MPD", "matterhorn1"]


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("matterhorn1.tasks.time.sleep", lambda *_a, **_k: None)


@pytest.fixture
def matterhorn_api(settings):
    """Ustawia adres i klucz API na wartości testowe."""
    settings.MATTERHORN_API_URL = "https://matterhorn.test"
    settings.MATTERHORN_API_KEY = "test-key"
    return settings


@pytest.fixture
def mocked_responses():
    import responses
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def prior_items_sync(db):
    """`ApiSyncLog` sygnalizujący, że wcześniej był udany import ITEMS —
    bez niego `_get_last_items_update_time()` zwraca None i import się nie
    zaczyna."""
    from matterhorn1.models import ApiSyncLog
    return ApiSyncLog.objects.using("matterhorn1").create(
        sync_type="items_import", status="success",
    )


@pytest.fixture
def api_item():
    return factories.api_item


@pytest.fixture
def api_variant():
    return factories.api_variant


@pytest.fixture
def inventory_record():
    return factories.inventory_record
