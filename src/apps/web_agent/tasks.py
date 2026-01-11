"""
Taski Celery dla automatyzacji wypełniania formularzy MPD.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db import connections
from .models import AutomationRun, ProductProcessingLog
from .automation.browser_automation import BrowserAutomation
from .automation.ai_processor import AIProcessor
from .automation.product_processor import ProductProcessor
import os

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='web_agent.tasks.automate_mpd_form_filling')
def automate_mpd_form_filling(self, brand_id: int = None, category_id: int = None, filters: dict = None):
    """
    Task Celery do automatyzacji wypełniania formularzy MPD.
    
    Args:
        brand_id: ID marki do filtrowania
        category_id: ID kategorii do filtrowania
        filters: Dodatkowe filtry (active, is_mapped, etc.)
        
    Returns:
        Słownik ze statystykami przetwarzania
    """
    automation_run = None
    
    try:
        # Utwórz log uruchomienia
        automation_run = AutomationRun.objects.create(
            status='running',
            brand_id=brand_id,
            category_id=category_id,
            filters=filters or {}
        )
        
        logger.info(f"Rozpoczęcie automatyzacji MPD - Run ID: {automation_run.id}")
        
        # Przygotuj filtry
        automation_filters = {
            'brand_id': brand_id,
            'category_id': category_id,
            'active': filters.get('active', True) if filters else True,
            'is_mapped': filters.get('is_mapped', True) if filters else True,
        }
        
        # Pobierz dane konfiguracyjne
        base_url = os.getenv('WEB_AGENT_BASE_URL', 'http://localhost:8000')
        # Usuń /admin/ z końca URL jeśli jest
        base_url = base_url.rstrip('/').replace('/admin', '')
        
        admin_username = os.getenv('DJANGO_ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('DJANGO_ADMIN_PASSWORD', '')
        openai_api_key = os.getenv('OPENAI_API_KEY', '')
        headless = os.getenv('BROWSER_HEADLESS', 'False').lower() == 'true'
        
        if not admin_username:
            raise ValueError("DJANGO_ADMIN_USERNAME nie jest ustawione w zmiennych środowiskowych")
        
        if not admin_password:
            raise ValueError("DJANGO_ADMIN_PASSWORD nie jest ustawione w zmiennych środowiskowych")
        
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY nie jest ustawione w zmiennych środowiskowych")
        
        # Inicjalizuj komponenty
        browser_automation = BrowserAutomation(
            base_url=base_url,
            username=admin_username,
            password=admin_password,
            headless=headless
        )
        
        ai_processor = AIProcessor(api_key=openai_api_key)
        
        product_processor = ProductProcessor(
            browser_automation=browser_automation,
            ai_processor=ai_processor
        )
        
        # Uruchom przeglądarkę
        browser_automation.start_browser()
        
        try:
            # Zaloguj się do admin
            browser_automation.login_to_admin()
            
            # Przejdź do listy produktów z filtrami
            browser_automation.navigate_to_product_list(automation_filters)
            
            # Pobierz listę ID produktów
            product_ids = browser_automation.get_product_ids_from_list()
            
            if not product_ids:
                logger.warning("Nie znaleziono produktów do przetworzenia")
                automation_run.status = 'completed'
                automation_run.completed_at = timezone.now()
                automation_run.save()
                return {
                    'status': 'completed',
                    'message': 'Nie znaleziono produktów do przetworzenia',
                    'products_processed': 0,
                    'products_success': 0,
                    'products_failed': 0
                }
            
            logger.info(f"Znaleziono {len(product_ids)} produktów do przetworzenia")
            
            # Przetwarzaj każdy produkt
            for product_id in product_ids:
                try:
                    # Utwórz log produktu
                    product_log = ProductProcessingLog.objects.create(
                        automation_run=automation_run,
                        product_id=product_id,
                        status='processing'
                    )
                    
                    # Pobierz nazwę produktu z bazy
                    product_data = product_processor.get_product_from_database(product_id)
                    if product_data:
                        product_log.product_name = product_data.get('name', '')
                        product_log.save()
                    
                    # Przetwórz produkt
                    result = product_processor.process_product(product_id)
                    
                    # Zaktualizuj log produktu
                    if result['success']:
                        product_log.status = 'success'
                        product_log.mpd_product_id = result.get('mpd_product_id')
                        automation_run.products_success += 1
                    else:
                        product_log.status = 'failed'
                        product_log.error_message = result.get('error_message', 'Unknown error')
                        automation_run.products_failed += 1
                    
                    product_log.processing_data = result
                    product_log.save()
                    
                    automation_run.products_processed += 1
                    automation_run.save()
                    
                    logger.info(f"Produkt {product_id} przetworzony: {result['success']}")
                    
                except Exception as e:
                    logger.error(f"Błąd podczas przetwarzania produktu {product_id}: {e}")
                    try:
                        product_log = ProductProcessingLog.objects.get(
                            automation_run=automation_run,
                            product_id=product_id
                        )
                        product_log.status = 'failed'
                        product_log.error_message = str(e)
                        product_log.save()
                    except:
                        ProductProcessingLog.objects.create(
                            automation_run=automation_run,
                            product_id=product_id,
                            status='failed',
                            error_message=str(e)
                        )
                    
                    automation_run.products_failed += 1
                    automation_run.products_processed += 1
                    automation_run.save()
            
            # Zakończ sukcesem
            automation_run.status = 'completed'
            automation_run.completed_at = timezone.now()
            automation_run.save()
            
            logger.info(f"Automatyzacja zakończona - Run ID: {automation_run.id}")
            
            return {
                'status': 'completed',
                'automation_run_id': automation_run.id,
                'products_processed': automation_run.products_processed,
                'products_success': automation_run.products_success,
                'products_failed': automation_run.products_failed
            }
            
        finally:
            # Zamknij przeglądarkę
            browser_automation.close_browser()
    
    except Exception as e:
        logger.error(f"Błąd podczas automatyzacji MPD: {e}", exc_info=True)
        
        if automation_run:
            automation_run.status = 'failed'
            automation_run.error_message = str(e)
            automation_run.completed_at = timezone.now()
            automation_run.save()
        
        raise

