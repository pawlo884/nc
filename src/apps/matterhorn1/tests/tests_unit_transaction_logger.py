"""
Unit: `matterhorn1.transaction_logger` — czysta infra logowania (bez DB).

Używane przez `admin.py` (`add_new_variants_to_mpd`) i `database_utils.py`.
"""
from __future__ import annotations

import pytest

from matterhorn1.transaction_logger import TransactionLogger, logged_transaction

pytestmark = pytest.mark.unit


class TestTransactionLogger:
    def test_log_operation_zbiera_wpisy_i_bazy(self):
        tl = TransactionLogger("op")
        tl.log_operation("INSERT", "matterhorn1", "product", "create")
        tl.log_operation("UPDATE", "MPD", "products", "update")

        assert len(tl.operations_log) == 2
        assert tl.databases_involved == {"matterhorn1", "MPD"}
        assert tl.operations_log[0]["operation_type"] == "INSERT"
        assert tl.operations_log[0]["success"] is True

    def test_log_cross_database_operation_sklada_nazwe_bazy(self):
        tl = TransactionLogger("map")
        tl.log_cross_database_operation("matterhorn1", "MPD", "create_product")

        entry = tl.operations_log[0]
        assert entry["database"] == "matterhorn1->MPD"
        assert entry["operation_type"] == "CROSS_DB"

    def test_end_transaction_zwraca_podsumowanie(self):
        tl = TransactionLogger("op")
        tl.start_transaction()
        tl.log_operation("INSERT", "matterhorn1", "product", "create")

        summary = tl.end_transaction(success=True)

        assert summary["operation"] == "op"
        assert summary["success"] is True
        assert summary["operations_count"] == 1
        assert summary["databases_involved"] == ["matterhorn1"]


class TestLoggedTransactionContextManager:
    def test_happy_path_konczy_sukcesem(self):
        with logged_transaction("op") as tl:
            tl.log_operation("INSERT", "matterhorn1", "product", "create")
        assert len(tl.operations_log) == 1

    def test_wyjatek_jest_re_raise(self):
        with pytest.raises(ValueError, match="boom"):
            with logged_transaction("op") as tl:
                tl.log_operation("INSERT", "matterhorn1", "product", "create")
                raise ValueError("boom")

    def test_wyjatek_domyka_transakcje_jako_blad(self, caplog):
        import logging

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                with logged_transaction("op_z_bledem"):
                    raise RuntimeError("nope")

        assert any("BŁĄD" in r.message and "op_z_bledem" in r.message for r in caplog.records)
