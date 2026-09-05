"""
Integration: komenda `dedupe_stock_history` - usuwa wpisy StockHistory
powielone przez nakładające się runy importu, nie rusza legalnych powtórzeń
tej samej zmiany (oddalonych w czasie / z wpisem odwrotnym pomiędzy).
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from core.db_routers import _get_matterhorn1_db
from matterhorn1.models import StockHistory

pytestmark = [pytest.mark.integration, pytest.mark.django_db(databases="__all__")]
DB = _get_matterhorn1_db()


def _row(variant_uid, old, new, ts):
    r = StockHistory.objects.using(DB).create(
        variant_uid=variant_uid, product_uid=1, product_name="P", variant_name="M",
        old_stock=old, new_stock=new, stock_change=new - old,
        change_type="decrease" if new < old else "increase")
    StockHistory.objects.using(DB).filter(pk=r.pk).update(timestamp=ts)
    return r.pk


def test_usuwa_powielone_w_oknie_zostawia_pierwszy():
    t0 = timezone.now()
    keep = _row("V1", 3, 2, t0)
    dup1 = _row("V1", 3, 2, t0 + timedelta(minutes=1))
    dup2 = _row("V1", 3, 2, t0 + timedelta(minutes=9))

    call_command("dedupe_stock_history", "--execute", "--window-minutes", "15")

    ids = set(StockHistory.objects.using(DB).values_list("id", flat=True))
    assert keep in ids
    assert dup1 not in ids and dup2 not in ids


def test_nie_rusza_powtorzenia_z_wpisem_odwrotnym_pomiedzy():
    t0 = timezone.now()
    a = _row("V2", 3, 2, t0)
    b = _row("V2", 2, 3, t0 + timedelta(minutes=3))   # restock pomiędzy
    c = _row("V2", 3, 2, t0 + timedelta(minutes=6))

    call_command("dedupe_stock_history", "--execute", "--window-minutes", "15")

    ids = set(StockHistory.objects.using(DB).values_list("id", flat=True))
    assert {a, b, c} <= ids


def test_nie_rusza_tego_samego_przejscia_poza_oknem():
    t0 = timezone.now()
    a = _row("V3", 1, 0, t0)
    b = _row("V3", 1, 0, t0 + timedelta(hours=20))   # kolejny dzień, restock nie zalogowany

    call_command("dedupe_stock_history", "--execute", "--window-minutes", "15")

    ids = set(StockHistory.objects.using(DB).values_list("id", flat=True))
    assert {a, b} <= ids


def test_dry_run_domyslnie_nic_nie_usuwa():
    t0 = timezone.now()
    _row("V4", 5, 4, t0)
    _row("V4", 5, 4, t0 + timedelta(minutes=2))

    call_command("dedupe_stock_history", "--window-minutes", "15")

    assert StockHistory.objects.using(DB).filter(variant_uid="V4").count() == 2
