"""
Testy wznawiania importu ITEMS (fix a) i propagacji SoftTimeLimitExceeded (fix b).

Kontekst: import inkrementalny wpadał w spiralę — po przekroczeniu limitu czasu
Celery run ginął ze statusem 'error', znacznik last_update (przeskakuje tylko po
'completed') stał w miejscu, a każdy kolejny run zaczynał od strony 1 i znów nie
nadążał. _get_last_items_page() teraz wznawia od current_page ostatniego
przerwanego runu.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from celery.exceptions import SoftTimeLimitExceeded

from matterhorn1.models import ApiSyncLog
from matterhorn1.tasks import _get_last_items_page, _bulk_import_products


def _mk_log(status, current_page, age_hours=0, sync_type='items_import'):
    row = ApiSyncLog.objects.using('matterhorn1').create(
        sync_type=sync_type, status=status, current_page=current_page,
    )
    if age_hours:
        ApiSyncLog.objects.using('matterhorn1').filter(pk=row.pk).update(
            started_at=timezone.now() - timedelta(hours=age_hours)
        )
    return ApiSyncLog.objects.using('matterhorn1').get(pk=row.pk)


class GetLastItemsPageResumeTest(TestCase):
    databases = {'matterhorn1', 'default'}

    def test_resumes_from_last_interrupted_page(self):
        _mk_log('completed', 22, age_hours=6)
        _mk_log('error', 37, age_hours=1)
        self.assertEqual(_get_last_items_page(), 37)

    def test_resumes_from_running_row(self):
        _mk_log('running', 12, age_hours=0)
        self.assertEqual(_get_last_items_page(), 12)

    def test_starts_from_one_when_last_run_completed(self):
        _mk_log('error', 40, age_hours=3)
        _mk_log('completed', 5, age_hours=1)
        self.assertEqual(_get_last_items_page(), 1)

    def test_starts_from_one_when_interrupted_run_is_stale(self):
        _mk_log('error', 40, age_hours=48)
        self.assertEqual(_get_last_items_page(), 1)

    def test_starts_from_one_when_page_is_one(self):
        _mk_log('error', 1, age_hours=1)
        self.assertEqual(_get_last_items_page(), 1)

    def test_starts_from_one_when_no_history(self):
        self.assertEqual(_get_last_items_page(), 1)


class BulkImportSoftTimeLimitTest(TestCase):
    databases = {'matterhorn1', 'default'}

    def test_soft_time_limit_propagates_not_swallowed(self):
        """_bulk_import_products nie może połknąć SoftTimeLimitExceeded jako
        'status: error' (to uruchamiało 5x retry per-strona i zjadało grace
        między soft a hard limitem)."""
        from unittest.mock import MagicMock, patch

        mock_product = MagicMock()
        mock_product.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_product.objects.using.return_value.get.side_effect = SoftTimeLimitExceeded()

        with patch('matterhorn1.models.Product', mock_product):
            with self.assertRaises(SoftTimeLimitExceeded):
                _bulk_import_products([{'id': 1, 'creation_date': '2026-01-01'}])
