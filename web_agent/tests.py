from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, Mock
# import json

from .models import WebAgentTask, WebAgentLog, WebAgentConfig


class WebAgentTaskModelTest(TestCase):
    """Testy dla modelu WebAgentTask"""
    
    def setUp(self):
        self.task = WebAgentTask.objects.create(
            name='Test Task',
            task_type='scrape',
            url='https://example.com',
            config={'timeout': 30}
        )
    
    def test_task_creation(self):
        """Test tworzenia zadania"""
        self.assertEqual(self.task.name, 'Test Task')
        self.assertEqual(self.task.task_type, 'scrape')
        self.assertEqual(self.task.status, 'pending')
        self.assertIsNotNone(self.task.created_at)
    
    def test_task_str_representation(self):
        """Test reprezentacji string zadania"""
        expected = "Test Task (Oczekujące)"
        self.assertEqual(str(self.task), expected)
    
    def test_task_status_choices(self):
        """Test wyborów statusu zadania"""
        valid_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
        for task_status in valid_statuses:
            self.task.status = task_status
            self.task.save()
            self.assertEqual(self.task.status, task_status)


class WebAgentLogModelTest(TestCase):
    """Testy dla modelu WebAgentLog"""
    
    def setUp(self):
        self.task = WebAgentTask.objects.create(
            name='Test Task',
            task_type='scrape',
            url='https://example.com'
        )
        self.log = WebAgentLog.objects.create(
            task=self.task,
            level='INFO',
            message='Test log message',
            extra_data={'test': 'data'}
        )
    
    def test_log_creation(self):
        """Test tworzenia logu"""
        self.assertEqual(self.log.task, self.task)
        self.assertEqual(self.log.level, 'INFO')
        self.assertEqual(self.log.message, 'Test log message')
        self.assertEqual(self.log.extra_data, {'test': 'data'})
    
    def test_log_str_representation(self):
        """Test reprezentacji string logu"""
        expected = f"Test Task - Informacja - {self.log.timestamp}"
        self.assertEqual(str(self.log), expected)


class WebAgentConfigModelTest(TestCase):
    """Testy dla modelu WebAgentConfig"""
    
    def setUp(self):
        self.config = WebAgentConfig.objects.create(
            name='Test Config',
            description='Test configuration',
            config_data={'timeout': 30, 'retries': 3}
        )
    
    def test_config_creation(self):
        """Test tworzenia konfiguracji"""
        self.assertEqual(self.config.name, 'Test Config')
        self.assertEqual(self.config.description, 'Test configuration')
        self.assertEqual(self.config.config_data, {'timeout': 30, 'retries': 3})
        self.assertTrue(self.config.is_active)
    
    def test_config_str_representation(self):
        """Test reprezentacji string konfiguracji"""
        self.assertEqual(str(self.config), 'Test Config')


class WebAgentTaskAPITest(APITestCase):
    """Testy API dla zadań agenta web"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.task_data = {
            'name': 'Test API Task',
            'task_type': 'scrape',
            'url': 'https://example.com',
            'config': {'timeout': 30}
        }
    
    def test_create_task(self):
        """Test tworzenia zadania przez API"""
        url = reverse('web_agent:webagenttask-list')
        response = self.client.post(url, self.task_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WebAgentTask.objects.count(), 1)
        
        task = WebAgentTask.objects.get()
        self.assertEqual(task.name, 'Test API Task')
        self.assertEqual(task.task_type, 'scrape')
        self.assertEqual(task.url, 'https://example.com')
    
    def test_list_tasks(self):
        """Test listy zadań"""
        WebAgentTask.objects.create(
            name='Task 1',
            task_type='scrape',
            url='https://example1.com'
        )
        WebAgentTask.objects.create(
            name='Task 2',
            task_type='monitor',
            url='https://example2.com'
        )
        
        url = reverse('web_agent:webagenttask-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_retrieve_task(self):
        """Test pobierania pojedynczego zadania"""
        task = WebAgentTask.objects.create(
            name='Test Task',
            task_type='scrape',
            url='https://example.com'
        )
        
        url = reverse('web_agent:webagenttask-detail', kwargs={'pk': task.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Task')
    
    def test_update_task(self):
        """Test aktualizacji zadania"""
        task = WebAgentTask.objects.create(
            name='Original Task',
            task_type='scrape',
            url='https://example.com'
        )
        
        update_data = {
            'name': 'Updated Task',
            'task_type': 'monitor',
            'url': 'https://updated.com'
        }
        
        url = reverse('web_agent:webagenttask-detail', kwargs={'pk': task.pk})
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        task.refresh_from_db()
        self.assertEqual(task.name, 'Updated Task')
        self.assertEqual(task.task_type, 'monitor')
        self.assertEqual(task.url, 'https://updated.com')
    
    def test_delete_task(self):
        """Test usuwania zadania"""
        task = WebAgentTask.objects.create(
            name='Task to Delete',
            task_type='scrape',
            url='https://example.com'
        )
        
        url = reverse('web_agent:webagenttask-detail', kwargs={'pk': task.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(WebAgentTask.objects.count(), 0)
    
    def test_task_stats(self):
        """Test statystyk zadań"""
        WebAgentTask.objects.create(
            name='Task 1',
            task_type='scrape',
            status='pending'
        )
        WebAgentTask.objects.create(
            name='Task 2',
            task_type='monitor',
            status='completed'
        )
        WebAgentTask.objects.create(
            name='Task 3',
            task_type='scrape',
            status='failed'
        )
        
        url = reverse('web_agent:webagenttask-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_tasks'], 3)
        self.assertEqual(response.data['pending_tasks'], 1)
        self.assertEqual(response.data['completed_tasks'], 1)
        self.assertEqual(response.data['failed_tasks'], 1)
    
    @patch('web_agent.views.start_web_agent_task.delay')
    def test_start_task(self, mock_delay):
        """Test uruchamiania zadania"""
        mock_delay.return_value = Mock(id='test-celery-id')
        
        task = WebAgentTask.objects.create(
            name='Task to Start',
            task_type='scrape',
            url='https://example.com',
            status='pending'
        )
        
        url = reverse('web_agent:webagenttask-start', kwargs={'pk': task.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('celery_task_id', response.data)
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'running')
        self.assertEqual(task.celery_task_id, 'test-celery-id')
    
    def test_start_task_invalid_status(self):
        """Test uruchamiania zadania z nieprawidłowym statusem"""
        task = WebAgentTask.objects.create(
            name='Task to Start',
            task_type='scrape',
            url='https://example.com',
            status='running'
        )
        
        url = reverse('web_agent:webagenttask-start', kwargs={'pk': task.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    @patch('web_agent.views.stop_web_agent_task.delay')
    def test_stop_task(self, mock_delay):
        """Test zatrzymywania zadania"""
        task = WebAgentTask.objects.create(
            name='Task to Stop',
            task_type='scrape',
            url='https://example.com',
            status='running',
            celery_task_id='test-celery-id'
        )
        
        url = reverse('web_agent:webagenttask-stop', kwargs={'pk': task.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'cancelled')
    
    def test_stop_task_invalid_status(self):
        """Test zatrzymywania zadania z nieprawidłowym statusem"""
        task = WebAgentTask.objects.create(
            name='Task to Stop',
            task_type='scrape',
            url='https://example.com',
            status='pending'
        )
        
        url = reverse('web_agent:webagenttask-stop', kwargs={'pk': task.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class WebAgentLogAPITest(APITestCase):
    """Testy API dla logów agenta web"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.task = WebAgentTask.objects.create(
            name='Test Task',
            task_type='scrape',
            url='https://example.com'
        )
        
        self.log = WebAgentLog.objects.create(
            task=self.task,
            level='INFO',
            message='Test log message'
        )
    
    def test_list_logs(self):
        """Test listy logów"""
        url = reverse('web_agent:webagentlog-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_retrieve_log(self):
        """Test pobierania pojedynczego logu"""
        url = reverse('web_agent:webagentlog-detail', kwargs={'pk': self.log.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Test log message')
    
    def test_filter_logs_by_level(self):
        """Test filtrowania logów po poziomie"""
        WebAgentLog.objects.create(
            task=self.task,
            level='ERROR',
            message='Error message'
        )
        
        url = reverse('web_agent:webagentlog-list')
        response = self.client.get(url, {'level': 'INFO'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['level'], 'INFO')


class WebAgentConfigAPITest(APITestCase):
    """Testy API dla konfiguracji agenta web"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.config_data = {
            'name': 'Test Config',
            'description': 'Test configuration',
            'config_data': {'timeout': 30, 'retries': 3}
        }
    
    def test_create_config(self):
        """Test tworzenia konfiguracji przez API"""
        url = reverse('web_agent:webagentconfig-list')
        response = self.client.post(url, self.config_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WebAgentConfig.objects.count(), 1)
        
        config = WebAgentConfig.objects.get()
        self.assertEqual(config.name, 'Test Config')
        self.assertEqual(config.config_data, {'timeout': 30, 'retries': 3})
    
    def test_list_configs(self):
        """Test listy konfiguracji"""
        WebAgentConfig.objects.create(
            name='Config 1',
            config_data={'timeout': 30}
        )
        WebAgentConfig.objects.create(
            name='Config 2',
            config_data={'timeout': 60}
        )
        
        url = reverse('web_agent:webagentconfig-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_retrieve_config(self):
        """Test pobierania pojedynczej konfiguracji"""
        config = WebAgentConfig.objects.create(
            name='Test Config',
            config_data={'timeout': 30}
        )
        
        url = reverse('web_agent:webagentconfig-detail', kwargs={'pk': config.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Config')
    
    def test_update_config(self):
        """Test aktualizacji konfiguracji"""
        config = WebAgentConfig.objects.create(
            name='Original Config',
            config_data={'timeout': 30}
        )
        
        update_data = {
            'name': 'Updated Config',
            'config_data': {'timeout': 60, 'retries': 5}
        }
        
        url = reverse('web_agent:webagentconfig-detail', kwargs={'pk': config.pk})
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        config.refresh_from_db()
        self.assertEqual(config.name, 'Updated Config')
        self.assertEqual(config.config_data, {'timeout': 60, 'retries': 5})
    
    def test_delete_config(self):
        """Test usuwania konfiguracji"""
        config = WebAgentConfig.objects.create(
            name='Config to Delete',
            config_data={'timeout': 30}
        )
        
        url = reverse('web_agent:webagentconfig-detail', kwargs={'pk': config.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(WebAgentConfig.objects.count(), 0)


class WebAgentTaskIntegrationTest(APITestCase):
    """Testy integracyjne dla zadań agenta web"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_task_lifecycle(self):
        """Test pełnego cyklu życia zadania"""
        # 1. Utwórz zadanie
        task_data = {
            'name': 'Lifecycle Test Task',
            'task_type': 'scrape',
            'url': 'https://example.com',
            'config': {'timeout': 30}
        }
        
        url = reverse('web_agent:webagenttask-list')
        response = self.client.post(url, task_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        task_id = response.data['id']
        
        # 2. Sprawdź, że zadanie zostało utworzone
        task = WebAgentTask.objects.get(id=task_id)
        self.assertEqual(task.status, 'pending')
        
        # 3. Sprawdź logi
        self.assertEqual(task.logs.count(), 0)
        
        # 4. Uruchom zadanie (mock)
        with patch('web_agent.views.start_web_agent_task.delay') as mock_delay:
            mock_delay.return_value = Mock(id='test-celery-id')
            
            url = reverse('web_agent:webagenttask-start', kwargs={'pk': task_id})
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 5. Sprawdź, że zadanie zostało uruchomione
        task.refresh_from_db()
        self.assertEqual(task.status, 'running')
        self.assertEqual(task.celery_task_id, 'test-celery-id')
        
        # 6. Sprawdź logi
        self.assertEqual(task.logs.count(), 1)
        log = task.logs.first()
        self.assertEqual(log.level, 'INFO')
        self.assertIn('Zadanie uruchomione', log.message)
        
        # 7. Zatrzymaj zadanie
        with patch('web_agent.views.stop_web_agent_task.delay') as mock_delay:
            url = reverse('web_agent:webagenttask-stop', kwargs={'pk': task_id})
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 8. Sprawdź, że zadanie zostało zatrzymane
        task.refresh_from_db()
        self.assertEqual(task.status, 'cancelled')
        
        # 9. Sprawdź logi
        self.assertEqual(task.logs.count(), 2)
        log = task.logs.last()
        self.assertEqual(log.level, 'INFO')
        self.assertIn('Zadanie zatrzymane', log.message)
