"""
Komenda sprzątająca Mada: `cleanup_empty_mada_products`.

(`cleanup_orphaned_mada_mapping` sięga do `_get_mada_db()` / `_get_mpd_db()`
bezpośrednio — poza remapowaniem routerów w trybie testowym — więc nie jest
tu pokryta.)
"""
from __future__ import annotations

import pytest
from django.core.management import call_command

from mada.models import MadaProduct

from .factories import mada_product, mada_variant

pytestmark = pytest.mark.django_db


class TestCleanupEmptyProducts:
    def test_usuwa_tylko_puste_niezmapowane(self):
        mada_product(api_id=1, name="")                       # pusty, niezmapowany → kasowany
        mada_product(api_id=2, name="", mapped_product_uid=55)  # pusty, ale zmapowany → zostaje
        mada_product(api_id=3, name="Ma nazwę")                 # z nazwą → zostaje

        call_command("cleanup_empty_mada_products")

        assert set(MadaProduct.objects.values_list("api_id", flat=True)) == {2, 3}

    def test_dry_run_nic_nie_kasuje(self):
        mada_product(api_id=1, name="")
        call_command("cleanup_empty_mada_products", "--dry-run")
        assert MadaProduct.objects.filter(api_id=1).exists()

    def test_kasuje_powiazane_warianty(self):
        p = mada_product(api_id=1, name="")
        mada_variant(p, variant_key="v1", ean="v1")

        call_command("cleanup_empty_mada_products")

        assert not MadaProduct.objects.filter(api_id=1).exists()
