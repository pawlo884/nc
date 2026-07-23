"""
Testy serializerów web_agent - AutomationRunSerializer, ProductProcessingLogSerializer,
StartAutomationSerializer.
"""
from django.test import TestCase
from django.utils import timezone

from web_agent.models import AutomationRun, ProductProcessingLog
from web_agent.serializers import (
    AutomationRunSerializer,
    ProductProcessingLogSerializer,
    StartAutomationSerializer,
)


class AutomationRunSerializerTest(TestCase):
    """Testy AutomationRunSerializer"""

    def test_serialize_run_without_logs(self):
        run = AutomationRun.objects.create(brand_id=1, status='pending')
        data = AutomationRunSerializer(run).data
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(data['product_logs'], [])
        self.assertIsNone(data['duration_seconds'])

    def test_duration_seconds_computed(self):
        started = timezone.now()
        run = AutomationRun.objects.create(brand_id=1, status='completed')
        AutomationRun.objects.filter(pk=run.pk).update(
            started_at=started, completed_at=started + timezone.timedelta(seconds=42)
        )
        run.refresh_from_db()
        data = AutomationRunSerializer(run).data
        self.assertEqual(data['duration_seconds'], 42.0)

    def test_nested_product_logs_serialized(self):
        run = AutomationRun.objects.create(brand_id=1, status='running')
        ProductProcessingLog.objects.create(
            automation_run=run, product_id=555, product_name='Test', status='success',
        )
        data = AutomationRunSerializer(run).data
        self.assertEqual(len(data['product_logs']), 1)
        self.assertEqual(data['product_logs'][0]['product_id'], 555)


class ProductProcessingLogSerializerTest(TestCase):
    """Testy ProductProcessingLogSerializer"""

    def test_serialize_log(self):
        run = AutomationRun.objects.create(brand_id=2, status='running')
        log = ProductProcessingLog.objects.create(
            automation_run=run,
            product_id=123,
            product_name='Produkt X',
            status='failed',
            error_message='Błąd testowy',
        )
        data = ProductProcessingLogSerializer(log).data
        self.assertEqual(data['product_id'], 123)
        self.assertEqual(data['status'], 'failed')
        self.assertEqual(data['error_message'], 'Błąd testowy')


class StartAutomationSerializerTest(TestCase):
    """Testy StartAutomationSerializer"""

    def test_matterhorn1_requires_brand_or_category(self):
        serializer = StartAutomationSerializer(data={'source': 'matterhorn1'})
        self.assertFalse(serializer.is_valid())

    def test_matterhorn1_valid_with_brand_id(self):
        serializer = StartAutomationSerializer(
            data={'source': 'matterhorn1', 'brand_id': 10}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_matterhorn1_valid_with_category_id(self):
        serializer = StartAutomationSerializer(
            data={'source': 'matterhorn1', 'category_id': 20}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_tabu_source_does_not_require_brand_or_category(self):
        serializer = StartAutomationSerializer(data={'source': 'tabu'})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_default_source_is_matterhorn1(self):
        serializer = StartAutomationSerializer(data={'brand_id': 5})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['source'], 'matterhorn1')
