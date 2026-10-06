"""
Unit: czyste helpery `matterhorn1.tasks` — bez DB, bez HTTP.

Warstwa rozbudowywana w Fazie 2 (docs/TESTING.md): `_prepare_product_create`
/ `_prepare_product_update` (wymagają DB — get_or_create marki/kategorii),
`stock_tracker`, `transaction_logger`, `database_utils`.
"""
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

import pytest
from django.utils import timezone

from matterhorn1.tasks import _parse_creation_date, full_import_and_update

pytestmark = pytest.mark.unit


def test_full_import_ma_acks_late_false():
    """#238: bez acks_late ubity w połowie run byłby redeliverowany po
    visibility_timeout (1 h) i leciał drugi raz na nieaktualnym oknie."""
    assert full_import_and_update.acks_late is False


class TestParseCreationDate:
    def test_none_zwraca_none(self):
        assert _parse_creation_date(None) is None

    def test_pusty_string_zwraca_none(self):
        assert _parse_creation_date("") is None

    def test_smieciowy_string_zwraca_none(self):
        assert _parse_creation_date("nie-data") is None

    def test_naive_dostaje_utc(self):
        result = _parse_creation_date("2026-01-15T10:00:00")
        assert result == datetime(2026, 1, 15, 10, 0, 0, tzinfo=dt_timezone.utc)
        assert timezone.is_aware(result)

    def test_z_offsetem_zachowuje_moment(self):
        result = _parse_creation_date("2026-01-15T12:00:00+02:00")
        assert result == datetime(2026, 1, 15, 10, 0, 0, tzinfo=dt_timezone.utc)
