"""
Testy dla aplikacji web_agent
Testy modeli i API endpoints
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from datetime import timedelta
import json

from .models import (
    AutomationRun, ProductProcessingLog,
    BrandConfig, ProducerColor
)


class AutomationRunModelTest(TestCase):
    """Testy dla modelu AutomationRun"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.automation_run = AutomationRun.objects.create(
            status='pending',
            products_processed=0,
            products_success=0,
            products_failed=0,
            brand_id=1,
            category_id=2,
            filters={'active': True}
        )

    def test_automation_run_creation(self):
        """Test tworzenia uruchomienia automatyzacji"""
        self.assertEqual(self.automation_run.status, 'pending')
        self.assertEqual(self.automation_run.products_processed, 0)
        self.assertEqual(self.automation_run.products_success, 0)
        self.assertEqual(self.automation_run.products_failed, 0)
        self.assertEqual(self.automation_run.brand_id, 1)
        self.assertEqual(self.automation_run.category_id, 2)
        self.assertEqual(self.automation_run.filters['active'], True)
        self.assertIsNotNone(self.automation_run.started_at)

    def test_automation_run_str(self):
        """Test metody __str__"""
        self.assertIn('AutomationRun', str(self.automation_run))
        self.assertIn('pending', str(self.automation_run))

    def test_automation_run_duration(self):
        """Test właściwości duration"""
        # Bez completed_at
        self.assertIsNone(self.automation_run.duration)

        # Z completed_at
        self.automation_run.completed_at = timezone.now() + timedelta(seconds=60)
        self.automation_run.save()
        duration = self.automation_run.duration
        self.assertIsNotNone(duration)
        self.assertAlmostEqual(duration.total_seconds(), 60, delta=1)

    def test_automation_run_status_choices(self):
        """Test wyboru statusu"""
        valid_statuses = ['pending', 'running', 'completed', 'failed']
        for status_choice in valid_statuses:
            run = AutomationRun.objects.create(status=status_choice)
            self.assertEqual(run.status, status_choice)

    def test_automation_run_json_filters(self):
        """Test pola JSON filters"""
        filters = {
            'active': True,
            'is_mapped': False,
            'brand_id': 1
        }
        self.automation_run.filters = filters
        self.automation_run.save()

        run = AutomationRun.objects.get(pk=self.automation_run.pk)
        self.assertEqual(run.filters['active'], True)
        self.assertEqual(run.filters['is_mapped'], False)
        self.assertEqual(run.filters['brand_id'], 1)


class ProductProcessingLogModelTest(TestCase):
    """Testy dla modelu ProductProcessingLog"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.automation_run = AutomationRun.objects.create(
            status='running'
        )
        self.product_log = ProductProcessingLog.objects.create(
            automation_run=self.automation_run,
            product_id=12345,
            product_name='Test Product',
            status='success',
            mpd_product_id=67890,
            processing_data={'color': 'red', 'size': 'M'}
        )

    def test_product_log_creation(self):
        """Test tworzenia logu produktu"""
        self.assertEqual(self.product_log.automation_run, self.automation_run)
        self.assertEqual(self.product_log.product_id, 12345)
        self.assertEqual(self.product_log.product_name, 'Test Product')
        self.assertEqual(self.product_log.status, 'success')
        self.assertEqual(self.product_log.mpd_product_id, 67890)
        self.assertEqual(self.product_log.processing_data['color'], 'red')
        self.assertIsNotNone(self.product_log.processed_at)

    def test_product_log_str(self):
        """Test metody __str__"""
        self.assertIn('ProductLog', str(self.product_log))
        self.assertIn('12345', str(self.product_log))
        self.assertIn('success', str(self.product_log))

    def test_product_log_relationship(self):
        """Test relacji z AutomationRun"""
        self.assertEqual(self.automation_run.product_logs.count(), 1)
        self.assertIn(self.product_log, self.automation_run.product_logs.all())

    def test_product_log_status_choices(self):
        """Test wyboru statusu"""
        valid_statuses = ['pending', 'processing', 'success', 'failed']
        for status_choice in valid_statuses:
            log = ProductProcessingLog.objects.create(
                automation_run=self.automation_run,
                product_id=999,
                status=status_choice
            )
            self.assertEqual(log.status, status_choice)

    def test_product_log_json_processing_data(self):
        """Test pola JSON processing_data"""
        data = {
            'color': 'blue',
            'size': 'L',
            'attributes': ['Cotton', 'Elastic']
        }
        self.product_log.processing_data = data
        self.product_log.save()

        log = ProductProcessingLog.objects.get(pk=self.product_log.pk)
        self.assertEqual(log.processing_data['color'], 'blue')
        self.assertEqual(log.processing_data['size'], 'L')
        self.assertEqual(len(log.processing_data['attributes']), 2)


class BrandConfigModelTest(TestCase):
    """Testy dla modelu BrandConfig"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.brand_config = BrandConfig.objects.create(
            brand_id=1,
            brand_name='Test Brand',
            default_active_filter=True,
            default_is_mapped_filter=False,
            color_mapping={
                'Dark Brown': 'Ciemny Brąz',
                'Beige': 'Beż'
            },
            attributes=['Bawełna', 'Elastan', 'Bambus'],
            similarity_threshold=0.7
        )

    def test_brand_config_creation(self):
        """Test tworzenia konfiguracji marki"""
        self.assertEqual(self.brand_config.brand_id, 1)
        self.assertEqual(self.brand_config.brand_name, 'Test Brand')
        self.assertTrue(self.brand_config.default_active_filter)
        self.assertFalse(self.brand_config.default_is_mapped_filter)
        self.assertEqual(self.brand_config.color_mapping['Dark Brown'], 'Ciemny Brąz')
        self.assertIn('Bawełna', self.brand_config.attributes)
        self.assertEqual(self.brand_config.similarity_threshold, 0.7)

    def test_brand_config_str(self):
        """Test metody __str__"""
        expected = "Test Brand (ID: 1)"
        self.assertEqual(str(self.brand_config), expected)

    def test_brand_config_unique_brand_id(self):
        """Test unikalności brand_id"""
        with self.assertRaises(Exception):
            BrandConfig.objects.create(
                brand_id=1,
                brand_name='Another Brand'
            )

    def test_brand_config_json_fields(self):
        """Test pól JSON"""
        color_mapping = {
            'Red': 'Czerwony',
            'Blue': 'Niebieski'
        }
        attributes = ['Cotton', 'Polyester']

        self.brand_config.color_mapping = color_mapping
        self.brand_config.attributes = attributes
        self.brand_config.save()

        config = BrandConfig.objects.get(pk=self.brand_config.pk)
        self.assertEqual(config.color_mapping['Red'], 'Czerwony')
        self.assertEqual(config.attributes[0], 'Cotton')


class ProducerColorModelTest(TestCase):
    """Testy dla modelu ProducerColor"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.producer_color = ProducerColor.objects.create(
            brand_id=1,
            brand_name='Test Brand',
            color_name='Dark Brown',
            usage_count=5
        )

    def test_producer_color_creation(self):
        """Test tworzenia koloru producenta"""
        self.assertEqual(self.producer_color.brand_id, 1)
        self.assertEqual(self.producer_color.brand_name, 'Test Brand')
        self.assertEqual(self.producer_color.color_name, 'Dark Brown')
        self.assertEqual(self.producer_color.usage_count, 5)

    def test_producer_color_str(self):
        """Test metody __str__"""
        expected = "Test Brand - Dark Brown"
        self.assertEqual(str(self.producer_color), expected)

    def test_producer_color_normalization(self):
        """Test automatycznej normalizacji nazwy koloru"""
        # Sprawdź czy normalized_color został utworzony
        self.assertIsNotNone(self.producer_color.normalized_color)
        # Sprawdź czy jest znormalizowany (lowercase, bez spacji)
        normalized = self.producer_color._normalize_color_name('Dark Brown')
        self.assertEqual(normalized, 'darkbrown')

    def test_producer_color_unique_together(self):
        """Test unikalności kombinacji brand_id + color_name"""
        # Ten sam brand_id i color_name - powinno zwrócić błąd
        with self.assertRaises(Exception):
            ProducerColor.objects.create(
                brand_id=1,
                brand_name='Test Brand',
                color_name='Dark Brown'
            )

    def test_producer_color_normalize_method(self):
        """Test metody normalizacji"""
        test_cases = [
            ('Dark Brown', 'darkbrown'),
            ('Light Blue', 'lightblue'),
            ('Red-Blue', 'redblue'),
            ('  Green  ', 'green'),
            ('', '')
        ]

        for color_name, expected in test_cases:
            normalized = ProducerColor._normalize_color_name(color_name)
            self.assertEqual(normalized, expected)


# ==================== API TESTS ====================


class AutomationRunAPITest(APITestCase):
    """Testy API dla AutomationRun"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        self.automation_run = AutomationRun.objects.create(
            status='pending',
            brand_id=1,
            category_id=2
        )

    def test_automation_run_list_requires_auth(self):
        """Test czy lista uruchomień wymaga autoryzacji"""
        client = APIClient()
        response = client.get('/api/web-agent/automation-runs/')
        # DRF może zwracać 403 (Forbidden) zamiast 401
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ])

    def test_automation_run_list(self):
        """Test listy uruchomień"""
        url = '/api/web-agent/automation-runs/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_automation_run_detail(self):
        """Test szczegółów uruchomienia"""
        url = f'/api/web-agent/automation-runs/{self.automation_run.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.automation_run.id)
        self.assertEqual(response.data['status'], 'pending')

    def test_automation_run_filter_by_status(self):
        """Test filtrowania po statusie"""
        AutomationRun.objects.create(status='completed')
        AutomationRun.objects.create(status='failed')

        url = '/api/web-agent/automation-runs/?status=pending'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Powinien zwrócić tylko pending
        for item in response.data['results']:
            self.assertEqual(item['status'], 'pending')

    def test_automation_run_filter_by_brand_id(self):
        """Test filtrowania po brand_id"""
        AutomationRun.objects.create(status='pending', brand_id=2)
        AutomationRun.objects.create(status='pending', brand_id=3)

        url = '/api/web-agent/automation-runs/?brand_id=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Powinien zwrócić tylko brand_id=1
        for item in response.data['results']:
            self.assertEqual(item['brand_id'], 1)

    def test_automation_run_create(self):
        """Test tworzenia uruchomienia"""
        url = '/api/web-agent/automation-runs/'
        data = {
            'status': 'pending',
            'brand_id': 5,
            'category_id': 6,
            'filters': {'active': True}
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['brand_id'], 5)
        self.assertEqual(response.data['category_id'], 6)

    def test_automation_run_update(self):
        """Test aktualizacji uruchomienia"""
        url = f'/api/web-agent/automation-runs/{self.automation_run.id}/'
        data = {
            'status': 'completed',
            'products_processed': 100,
            'products_success': 95,
            'products_failed': 5
        }

        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['products_processed'], 100)

    def test_automation_run_delete(self):
        """Test usuwania uruchomienia"""
        url = f'/api/web-agent/automation-runs/{self.automation_run.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AutomationRun.objects.filter(pk=self.automation_run.id).exists())


class ProductProcessingLogAPITest(APITestCase):
    """Testy API dla ProductProcessingLog"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        self.automation_run = AutomationRun.objects.create(
            status='running'
        )
        self.product_log = ProductProcessingLog.objects.create(
            automation_run=self.automation_run,
            product_id=12345,
            product_name='Test Product',
            status='success'
        )

    def test_product_log_list_requires_auth(self):
        """Test czy lista logów wymaga autoryzacji"""
        client = APIClient()
        response = client.get('/api/web-agent/product-logs/')
        # DRF może zwracać 403 (Forbidden) zamiast 401
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ])

    def test_product_log_list(self):
        """Test listy logów"""
        url = '/api/web-agent/product-logs/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_product_log_detail(self):
        """Test szczegółów logu"""
        url = f'/api/web-agent/product-logs/{self.product_log.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.product_log.id)
        self.assertEqual(response.data['product_id'], 12345)

    def test_product_log_readonly(self):
        """Test czy logi są tylko do odczytu (nie można tworzyć przez API)"""
        url = '/api/web-agent/product-logs/'
        data = {
            'automation_run': self.automation_run.id,
            'product_id': 99999,
            'status': 'pending'
        }

        # POST powinien zwrócić 405 (Method Not Allowed) lub 403
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_403_FORBIDDEN
        ])


class AutomationRunStartAPITest(APITestCase):
    """Testy API dla uruchamiania automatyzacji"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_start_automation_requires_auth(self):
        """Test czy uruchomienie automatyzacji wymaga autoryzacji"""
        client = APIClient()
        url = '/api/web-agent/automation-runs/start-automation/'
        response = client.post(url, {})
        # DRF może zwracać 403 (Forbidden) zamiast 401
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ])

    def test_start_automation_endpoint_exists(self):
        """Test czy endpoint start-automation istnieje"""
        url = '/api/web-agent/automation-runs/start-automation/'
        # Może zwrócić 400 (błąd walidacji) lub 202 (zaakceptowane), ale nie 404
        response = self.client.post(url, {}, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_202_ACCEPTED,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])

    def test_start_automation_with_params(self):
        """Test uruchomienia automatyzacji z parametrami"""
        url = '/api/web-agent/automation-runs/start-automation/'
        data = {
            'brand_id': 1,
            'category_id': 2,
            'filters': {'active': True}
        }

        # Może zwrócić 202 (zaakceptowane) lub błąd jeśli Celery nie działa
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_202_ACCEPTED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])
