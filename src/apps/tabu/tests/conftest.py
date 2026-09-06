"""
Fixture'y wspólne dla testów `tabu` (warstwa integration/e2e).

`no_sleep` autouse — `sync_tabu_stock` woła `time.sleep(1)` po każdej stronie
(limit API), a `base_tabu_api_command` `time.sleep(2)` przy retry / `120` przy
429. Bez tego testy trwałyby minuty.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    for target in (
        "tabu.management.commands.sync_tabu_stock.time.sleep",
        "tabu.management.commands.sync_tabu_new_products.time.sleep",
        "tabu.management.commands.base_tabu_api_command.time.sleep",
    ):
        monkeypatch.setattr(target, lambda *_a, **_k: None, raising=False)


@pytest.fixture
def tabu_api(settings):
    """Adres + klucz API na wartości testowe."""
    settings.TABU_API_BASE_URL = "https://tabu.test"
    settings.TABU_API_KEY = "test-key"
    return settings


@pytest.fixture
def mocked_responses():
    import responses
    with responses.RequestsMock() as rsps:
        yield rsps
