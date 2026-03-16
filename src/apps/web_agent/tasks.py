"""
Taski Celery dla automatyzacji wypełniania formularzy MPD.
- matterhorn1: przeglądarka (Selenium) + AI.
- tabu: backend – masowe tworzenie produktów MPD z Tabu (bez przeglądarki).
"""
import logging
from celery import shared_task
from django.utils import timezone
from .models import AutomationRun, ProductProcessingLog
from .automation.browser_automation import BrowserAutomation
from .automation.ai_processor import AIProcessor
from .automation.product_processor import ProductProcessor
import os

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='web_agent.tasks.automate_tabu_to_mpd')
def automate_tabu_to_mpd(
    self,
    brand_id: int = None,
    category_id: int = None,
    filters: dict = None,
    automation_run_id: int = None,
):
    """
    Automatyzacja dodawania produktów z Tabu do MPD (backend, bez przeglądarki).
    Pobiera listę produktów Tabu (np. niezmapowanych), dla każdego wywołuje
    tabu.services.create_mpd_product_from_tabu.
    """
    run = None
    if automation_run_id:
        try:
            run = AutomationRun.objects.get(pk=automation_run_id)
        except AutomationRun.DoesNotExist:
            pass
    if not run:
        run = AutomationRun.objects.create(
            status='running',
            source='tabu',
            brand_id=brand_id,
            category_id=category_id,
            filters=filters or {},
        )

    try:
        from tabu.models import TabuProduct
        from tabu.services import create_mpd_product_from_tabu

        qs = TabuProduct.objects.filter(mapped_product_uid__isnull=True)
        if brand_id is not None:
            qs = qs.filter(brand_id=brand_id)
        if category_id is not None:
            qs = qs.filter(category_id=category_id)
        if filters:
            if filters.get('brand_id') is not None:
                qs = qs.filter(brand_id=filters['brand_id'])
            if filters.get('category_id') is not None:
                qs = qs.filter(category_id=filters['category_id'])

        product_ids = list(qs.values_list('id', flat=True)[:500])
        if not product_ids:
            run.status = 'completed'
            run.completed_at = timezone.now()
            run.save()
            return {
                'status': 'completed',
                'automation_run_id': run.id,
                'products_processed': 0,
                'products_success': 0,
                'products_failed': 0,
            }

        for pid in product_ids:
            try:
                plog = ProductProcessingLog.objects.create(
                    automation_run=run,
                    product_id=pid,
                    status='processing',
                )
                tabu_product = TabuProduct.objects.filter(pk=pid).first()
                if tabu_product:
                    plog.product_name = (tabu_product.name or '')[:500]
                    plog.save()
                result = create_mpd_product_from_tabu(pid, form_data=None)
                if result['success']:
                    plog.status = 'success'
                    plog.mpd_product_id = result['mpd_product_id']
                    run.products_success += 1
                else:
                    plog.status = 'failed'
                    plog.error_message = (result.get('error_message') or '')[:2000]
                    run.products_failed += 1
                plog.processing_data = result
                plog.save()
            except Exception as e:
                logger.exception("Tabu automatyzacja produkt %s: %s", pid, e)
                try:
                    ProductProcessingLog.objects.create(
                        automation_run=run,
                        product_id=pid,
                        status='failed',
                        error_message=str(e)[:2000],
                    )
                except Exception:
                    pass
                run.products_failed += 1
            run.products_processed += 1
            run.save()

        run.status = 'completed'
        run.completed_at = timezone.now()
        run.save()
        return {
            'status': 'completed',
            'automation_run_id': run.id,
            'products_processed': run.products_processed,
            'products_success': run.products_success,
            'products_failed': run.products_failed,
        }
    except Exception as e:
        logger.exception("Automatyzacja Tabu→MPD: %s", e)
        run.status = 'failed'
        run.error_message = str(e)
        run.completed_at = timezone.now()
        run.save()
        raise


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
        # Utwórz log uruchomienia (źródło: Matterhorn1 – przeglądarka)
        automation_run = AutomationRun.objects.create(
            status='running',
            source='matterhorn1',
            brand_id=brand_id,
            category_id=category_id,
            filters=filters or {},
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

