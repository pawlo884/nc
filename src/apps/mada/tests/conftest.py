"""
Fixture'y wspólne dla testów `mada` (warstwa integration/e2e/performance).
"""
from __future__ import annotations

import pytest


@pytest.fixture
def mada_api(settings):
    """Adres + dane logowania API na wartości testowe."""
    settings.MADA_API_BASE_URL = "https://mada.test"
    settings.MADA_API_LOGIN = "test-login"
    settings.MADA_API_PASSWORD = "test-pass"
    return settings


@pytest.fixture
def mocked_responses():
    import responses
    with responses.RequestsMock() as rsps:
        yield rsps
