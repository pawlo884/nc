"""
`mada.tasks` — cienkie wrappery Celery wokół komend zarządzania.
Kluczowe: advisory lock (skip gdy nie zdobyty) i retry przy błędzie komendy.
"""
from __future__ import annotations

import contextlib
from unittest.mock import patch

import pytest
from celery.exceptions import Retry

from mada import tasks

pytestmark = pytest.mark.django_db


@contextlib.contextmanager
def _lock(acquired):
    yield acquired


@pytest.mark.parametrize("task_fn, command", [
    (tasks.sync_mada_full, "sync_mada_full"),
    (tasks.sync_mada_partial, "sync_mada_partial"),
    (tasks.cleanup_empty_products, "cleanup_empty_mada_products"),
])
class TestLockedTasks:
    def test_skip_gdy_lock_nie_zdobyty(self, task_fn, command):
        with patch.object(tasks, "advisory_lock", lambda name: _lock(False)), \
                patch.object(tasks, "call_command") as cc:
            result = task_fn.apply().get()

        assert result == {"status": "skipped", "reason": "already_running"}
        cc.assert_not_called()

    def test_ok_wola_komende(self, task_fn, command):
        with patch.object(tasks, "advisory_lock", lambda name: _lock(True)), \
                patch.object(tasks, "call_command") as cc:
            result = task_fn.apply().get()

        assert result == {"status": "ok"}
        cc.assert_called_once_with(command)

    def test_blad_komendy_powoduje_retry(self, task_fn, command):
        with patch.object(tasks, "advisory_lock", lambda name: _lock(True)), \
                patch.object(tasks, "call_command", side_effect=RuntimeError("boom")), \
                pytest.raises(Retry):
            task_fn.apply(throw=True)


def test_full_i_partial_uzywaja_roznych_lockow():
    """Regresja: gdyby ktoś ujednolicił nazwy, ten test przypomni o decyzji
    (#243) — dziś full i partial mają OSOBNE locki i mogą lecieć równolegle,
    dlatego upsert_variants musi być idempotentny."""
    seen = []

    def _spy(name):
        seen.append(name)
        return _lock(True)

    with patch.object(tasks, "advisory_lock", _spy), patch.object(tasks, "call_command"):
        tasks.sync_mada_full.apply().get()
        tasks.sync_mada_partial.apply().get()

    assert seen == ["mada:sync_mada_full", "mada:sync_mada_partial"]
