import logging
import requests
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import WebAgentTask, WebAgentLog

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, countdown=60)
def start_web_agent_task(self, task_id):
    """Uruchamia zadanie agenta web"""
    try:
        with transaction.atomic():
            task = WebAgentTask.objects.get(id=task_id)
            
            # Dodaj log o rozpoczęciu zadania
            WebAgentLog.objects.create(
                task=task,
                level='INFO',
                message=f'Rozpoczęcie wykonywania zadania: {task.name}',
                extra_data={'celery_task_id': self.request.id}
            )
            
            # Wykonaj zadanie w zależności od typu
            if task.task_type == 'scrape':
                result = perform_scraping_task(task)
            elif task.task_type == 'monitor':
                result = perform_monitoring_task(task)
            elif task.task_type == 'data_collection':
                result = perform_data_collection_task(task)
            elif task.task_type == 'automation':
                result = perform_automation_task(task)
            else:
                raise ValueError(f'Nieznany typ zadania: {task.task_type}')
            
            # Aktualizuj zadanie jako zakończone
            task.status = 'completed'
            task.completed_at = timezone.now()
            task.result = result
            task.save()
            
            # Dodaj log o zakończeniu
            WebAgentLog.objects.create(
                task=task,
                level='INFO',
                message=f'Zadanie zakończone pomyślnie: {task.name}',
                extra_data={'result': result}
            )
            
            return result
            
    except Exception as exc:
        logger.error(f'Błąd podczas wykonywania zadania {task_id}: {str(exc)}')
        
        # Aktualizuj zadanie jako nieudane
        try:
            with transaction.atomic():
                task = WebAgentTask.objects.get(id=task_id)
                task.status = 'failed'
                task.completed_at = timezone.now()
                task.error_message = str(exc)
                task.save()
                
                # Dodaj log błędu
                WebAgentLog.objects.create(
                    task=task,
                    level='ERROR',
                    message=f'Błąd podczas wykonywania zadania: {str(exc)}',
                    extra_data={'error': str(exc), 'celery_task_id': self.request.id}
                )
        except Exception as save_exc:
            logger.error(f'Błąd podczas zapisywania błędu zadania {task_id}: {str(save_exc)}')
        
        # Próba ponownego uruchomienia
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        else:
            raise exc


@shared_task(bind=True)
def stop_web_agent_task(self, celery_task_id):
    """Zatrzymuje zadanie agenta web"""
    try:
        # Zatrzymaj zadanie w Celery
        self.control.revoke(celery_task_id, terminate=True)
        
        logger.info(f'Zadanie Celery {celery_task_id} zostało zatrzymane')
        return {'status': 'stopped', 'celery_task_id': celery_task_id}
        
    except Exception as exc:
        logger.error(f'Błąd podczas zatrzymywania zadania {celery_task_id}: {str(exc)}')
        raise exc


def perform_scraping_task(task):
    """Wykonuje zadanie scrapingu"""
    try:
        config = task.config
        url = config.get('url', task.url)
        
        if not url:
            raise ValueError('URL nie został podany')
        
        # Podstawowy scraping
        headers = config.get('headers', {})
        timeout = config.get('timeout', 30)
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Przetwórz odpowiedź
        content_type = response.headers.get('content-type', '')
        
        if 'application/json' in content_type:
            data = response.json()
        elif 'text/html' in content_type:
            data = {'html': response.text[:1000]}  # Ogranicz do 1000 znaków
        else:
            data = {'content': response.text[:1000]}
        
        result = {
            'status_code': response.status_code,
            'content_type': content_type,
            'data': data,
            'url': url,
            'timestamp': timezone.now().isoformat()
        }
        
        # Dodaj log o scrapingu
        WebAgentLog.objects.create(
            task=task,
            level='INFO',
            message=f'Scraping zakończony pomyślnie dla URL: {url}',
            extra_data={'status_code': response.status_code, 'content_type': content_type}
        )
        
        return result
        
    except requests.RequestException as e:
        raise Exception(f'Błąd HTTP podczas scrapingu: {str(e)}')
    except Exception as e:
        raise Exception(f'Błąd podczas scrapingu: {str(e)}')


def perform_monitoring_task(task):
    """Wykonuje zadanie monitorowania"""
    try:
        config = task.config
        url = config.get('url', task.url)
        
        if not url:
            raise ValueError('URL nie został podany')
        
        # Sprawdź dostępność strony
        timeout = config.get('timeout', 10)
        response = requests.get(url, timeout=timeout)
        
        is_available = response.status_code == 200
        response_time = response.elapsed.total_seconds()
        
        result = {
            'url': url,
            'is_available': is_available,
            'status_code': response.status_code,
            'response_time': response_time,
            'timestamp': timezone.now().isoformat()
        }
        
        # Dodaj log o monitorowaniu
        log_level = 'INFO' if is_available else 'WARNING'
        WebAgentLog.objects.create(
            task=task,
            level=log_level,
            message=f'Monitorowanie URL: {url} - {"Dostępny" if is_available else "Niedostępny"}',
            extra_data={'status_code': response.status_code, 'response_time': response_time}
        )
        
        return result
        
    except requests.RequestException as e:
        # Strona niedostępna
        result = {
            'url': task.url,
            'is_available': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }
        
        WebAgentLog.objects.create(
            task=task,
            level='WARNING',
            message=f'URL niedostępny: {task.url}',
            extra_data={'error': str(e)}
        )
        
        return result
    except Exception as e:
        raise Exception(f'Błąd podczas monitorowania: {str(e)}')


def perform_data_collection_task(task):
    """Wykonuje zadanie zbierania danych"""
    try:
        config = task.config
        urls = config.get('urls', [])
        
        if not urls:
            raise ValueError('Lista URL nie została podana')
        
        results = []
        
        for url in urls:
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                # Zbierz podstawowe informacje
                data = {
                    'url': url,
                    'status_code': response.status_code,
                    'content_length': len(response.content),
                    'content_type': response.headers.get('content-type', ''),
                    'timestamp': timezone.now().isoformat()
                }
                
                results.append(data)
                
                # Dodaj log o zebraniu danych
                WebAgentLog.objects.create(
                    task=task,
                    level='INFO',
                    message=f'Dane zebrane z URL: {url}',
                    extra_data={'status_code': response.status_code, 'content_length': len(response.content)}
                )
                
            except requests.RequestException as e:
                # Log błędu dla konkretnego URL
                WebAgentLog.objects.create(
                    task=task,
                    level='WARNING',
                    message=f'Błąd podczas zbierania danych z URL: {url}',
                    extra_data={'error': str(e)}
                )
                
                results.append({
                    'url': url,
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                })
        
        return {
            'total_urls': len(urls),
            'successful': len([r for r in results if 'error' not in r]),
            'failed': len([r for r in results if 'error' in r]),
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        raise Exception(f'Błąd podczas zbierania danych: {str(e)}')


def perform_automation_task(task):
    """Wykonuje zadanie automatyzacji"""
    try:
        config = task.config
        actions = config.get('actions', [])
        
        if not actions:
            raise ValueError('Lista akcji nie została podana')
        
        results = []
        
        for action in actions:
            action_type = action.get('type')
            
            if action_type == 'http_request':
                result = perform_http_action(action)
            elif action_type == 'data_processing':
                result = perform_data_processing_action(action)
            else:
                result = {'error': f'Nieznany typ akcji: {action_type}'}
            
            results.append(result)
            
            # Dodaj log o akcji
            WebAgentLog.objects.create(
                task=task,
                level='INFO',
                message=f'Wykonano akcję: {action_type}',
                extra_data={'action': action, 'result': result}
            )
        
        return {
            'total_actions': len(actions),
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        raise Exception(f'Błąd podczas automatyzacji: {str(e)}')


def perform_http_action(action):
    """Wykonuje akcję HTTP"""
    try:
        url = action.get('url')
        method = action.get('method', 'GET').upper()
        headers = action.get('headers', {})
        data = action.get('data', {})
        
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=30)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f'Nieobsługiwana metoda HTTP: {method}')
        
        return {
            'method': method,
            'url': url,
            'status_code': response.status_code,
            'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:500]
        }
        
    except Exception as e:
        return {'error': f'Błąd HTTP: {str(e)}'}


def perform_data_processing_action(action):
    """Wykonuje akcję przetwarzania danych"""
    try:
        data = action.get('data', {})
        operation = action.get('operation')
        
        if operation == 'count':
            result = len(data) if isinstance(data, (list, dict)) else 0
        elif operation == 'filter':
            filter_key = action.get('filter_key')
            filter_value = action.get('filter_value')
            if isinstance(data, list):
                result = [item for item in data if item.get(filter_key) == filter_value]
            else:
                result = data
        elif operation == 'transform':
            # Prosta transformacja danych
            result = {k.upper(): v for k, v in data.items() if isinstance(data, dict)}
        else:
            result = data
        
        return {
            'operation': operation,
            'input_data': data,
            'result': result
        }
        
    except Exception as e:
        return {'error': f'Błąd przetwarzania danych: {str(e)}'}
