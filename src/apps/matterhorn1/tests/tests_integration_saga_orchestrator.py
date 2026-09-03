"""
Integration: `core.saga.BaseSagaOrchestrator` przez `matterhorn1.saga.SagaOrchestrator`.

Wspólny silnik sagi (używany też przez tabu / mada). Kluczowe własności:
kompensacja cofa zapisy w bazie w odwrotnej kolejności, wynik kroku
propaguje się do `data` kolejnych kroków, status końcowy = COMPENSATED
przy błędzie.
"""
from __future__ import annotations

import pytest

from core.db_routers import _get_matterhorn1_db
from core.saga import SagaStatus
from matterhorn1.models import Brand, Saga
from matterhorn1.saga import SagaOrchestrator

SAGA_DB = _get_matterhorn1_db()  # 'zzz_matterhorn1' w trybie testów

# '__all__' bo core.saga pisze log do aliasu z `_get_matterhorn1_db()`
# (`zzz_matterhorn1` w trybie testów) — jak legacy tests_saga.py.
pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases="__all__")]
DB = "matterhorn1"


def _make_brand(brand_id, **_):
    b = Brand.objects.using(DB).create(brand_id=brand_id, name=f"B-{brand_id}")
    return {"created_brand_pk": b.pk}


def _delete_brand(brand_id, **_):
    # matterhorn1.SagaOrchestrator ma merge_result_into_own_step_data=False,
    # więc compensate dostaje tylko oryginalne `data` kroku (brand_id), nie wynik.
    Brand.objects.using(DB).filter(brand_id=brand_id).delete()


def _noop(**_):
    return {}


def _boom(**_):
    raise RuntimeError("krok celowo pada")


class TestHappyPath:
    def test_wszystkie_kroki_completed(self):
        saga = SagaOrchestrator(saga_type="test_ok")
        saga.add_step("a", _noop, _noop)
        saga.add_step("b", _noop, _noop)

        result = saga.execute()

        assert result.status == SagaStatus.COMPLETED
        assert [s.status for s in result.steps] == [SagaStatus.COMPLETED, SagaStatus.COMPLETED]

    def test_log_sagi_zapisany_jako_completed(self):
        saga = SagaOrchestrator(saga_type="test_log")
        saga.add_step("a", _noop, _noop)
        saga.execute()

        row = Saga.objects.using(SAGA_DB).get(saga_id=saga.saga_id)
        assert row.status == SagaStatus.COMPLETED.value


class TestKompensacja:
    def test_blad_kroku_cofa_wczesniejszy_zapis(self):
        saga = SagaOrchestrator(saga_type="test_compensate")
        saga.add_step("create_brand", _make_brand, _delete_brand, {"brand_id": "SAGA1"})
        saga.add_step("fail", _boom, _noop)

        result = saga.execute()

        assert result.status == SagaStatus.COMPENSATED
        assert result.error and "celowo pada" in result.error
        # krok 1 skompensowany → marka usunięta
        assert not Brand.objects.using(DB).filter(brand_id="SAGA1").exists()

    def test_kompensacja_w_odwrotnej_kolejnosci(self):
        order = []
        saga = SagaOrchestrator(saga_type="test_order")
        saga.add_step("s1", lambda **_: order.append("exec1") or {},
                      lambda **_: order.append("comp1"))
        saga.add_step("s2", lambda **_: order.append("exec2") or {},
                      lambda **_: order.append("comp2"))
        saga.add_step("s3", _boom, _noop)

        saga.execute()

        assert order == ["exec1", "exec2", "comp2", "comp1"]

    def test_kompensacja_kontynuuje_mimo_bledu_w_compensate(self):
        saga = SagaOrchestrator(saga_type="test_comp_err")
        saga.add_step("create_brand", _make_brand, _delete_brand, {"brand_id": "SAGA2"})
        saga.add_step("bad_comp", _noop, _boom)   # compensate rzuca
        saga.add_step("fail", _boom, _noop)

        result = saga.execute()

        assert result.status == SagaStatus.COMPENSATED
        # mimo wyjątku w kompensacji kroku "bad_comp", krok 1 i tak skompensowany
        assert not Brand.objects.using(DB).filter(brand_id="SAGA2").exists()

    def test_log_sagi_zapisany_jako_compensated(self):
        saga = SagaOrchestrator(saga_type="test_comp_log")
        saga.add_step("a", _noop, _noop)
        saga.add_step("fail", _boom, _noop)
        saga.execute()

        row = Saga.objects.using(SAGA_DB).get(saga_id=saga.saga_id)
        assert row.status == SagaStatus.COMPENSATED.value
        assert row.failed_step == "fail"


class TestPropagacjaWyniku:
    def test_wynik_kroku_wypelnia_none_w_data_kolejnego(self):
        seen = {}
        saga = SagaOrchestrator(saga_type="test_propagate")
        saga.add_step("s1", lambda **_: {"mpd_product_id": 777}, _noop)
        saga.add_step("s2", lambda **d: seen.update(d) or {}, _noop,
                      {"mpd_product_id": None})

        saga.execute()

        assert seen["mpd_product_id"] == 777

    def test_nie_nadpisuje_juz_ustawionej_wartosci(self):
        seen = {}
        saga = SagaOrchestrator(saga_type="test_no_override")
        saga.add_step("s1", lambda **_: {"mpd_product_id": 777}, _noop)
        saga.add_step("s2", lambda **d: seen.update(d) or {}, _noop,
                      {"mpd_product_id": 5})

        saga.execute()

        assert seen["mpd_product_id"] == 5
