"""
Główna klasa Agent - orkiestruje wykonanie zadań
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from django.utils import timezone

from .core import Browser, Workflow, ActionResult
from .workflows import DjangoAdminWorkflow, ProductMappingWorkflow

logger = logging.getLogger(__name__)


class Agent:
    """
    Główna klasa agenta - zarządza przeglądarką i wykonuje workflow.
    """
    
    def __init__(
        self,
        headless: bool = False,
        browser_type: str = 'chromium'
    ):
        """
        Args:
            headless: Czy uruchomić przeglądarkę w trybie headless
            browser_type: Typ przeglądarki
        """
        self.browser = Browser(headless=headless, browser_type=browser_type)
        self.workflows: List[Workflow] = []
        self.results: List[ActionResult] = []
        
    async def start(self):
        """Uruchamia przeglądarkę"""
        await self.browser.start()
        logger.info('Agent uruchomiony')
        
    async def stop(self):
        """Zatrzymuje przeglądarkę"""
        await self.browser.stop()
        logger.info('Agent zatrzymany')
        
    def add_workflow(self, workflow: Workflow):
        """Dodaje workflow do wykonania"""
        self.workflows.append(workflow)
        return self
        
    async def execute(self) -> Dict[str, Any]:
        """
        Wykonuje wszystkie dodane workflow
        
        Returns:
            Dict z wynikami wykonania
        """
        if not self.browser.is_running():
            await self.start()
            
        all_results = []
        
        for workflow in self.workflows:
            logger.info(f'Wykonuję workflow: {workflow.name}')
            results = await workflow.execute(self.browser)
            all_results.extend(results)
            
        self.results = all_results
        
        # Sprawdź czy wszystkie workflow się powiodły
        success = all(r.success for r in all_results if not r.action_type.value.startswith('wait'))
        
        return {
            'success': success,
            'workflows_executed': len(self.workflows),
            'total_actions': len(all_results),
            'successful_actions': sum(1 for r in all_results if r.success),
            'failed_actions': sum(1 for r in all_results if not r.success),
            'results': [r.to_dict() for r in all_results]
        }
        
    async def execute_django_admin_product_mapping(
        self,
        base_url: str,
        products_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        max_products: int = 10,
        env_file: str = '.env.dev'
    ) -> Dict[str, Any]:
        """
        Wykonuje pełny workflow: logowanie + nawigacja + mapowanie produktów
        
        Args:
            base_url: URL aplikacji Django
            products_url: URL do listy produktów (z filtrami)
            username: Nazwa użytkownika
            password: Hasło
            max_products: Maksymalna liczba produktów
            env_file: Ścieżka do .env
            
        Returns:
            Dict z wynikami
        """
        # 1. Workflow logowania
        login_workflow = DjangoAdminWorkflow.create_login_workflow(
            base_url=base_url,
            username=username,
            password=password,
            env_file=env_file
        )
        
        # 2. Workflow nawigacji do produktów
        nav_workflow = DjangoAdminWorkflow.create_navigate_to_products_workflow(
            products_url=products_url
        )
        
        # 3. Workflow mapowania produktów
        mapping_workflow = ProductMappingWorkflow.create_product_loop_workflow(
            max_products=max_products,
            changelist_url=products_url
        )
        
        # Dodaj wszystkie workflow
        self.add_workflow(login_workflow)
        self.add_workflow(nav_workflow)
        self.add_workflow(mapping_workflow)
        
        # Wykonaj
        return await self.execute()


# Funkcja pomocnicza do synchronicznego użycia
def run_agent_sync(
    base_url: str,
    products_url: str,
    headless: bool = False,
    username: Optional[str] = None,
    password: Optional[str] = None,
    max_products: int = 10
) -> Dict[str, Any]:
    """
    Uruchamia agenta synchronicznie (dla użycia w Celery)
    
    Args:
        base_url: URL aplikacji Django
        products_url: URL do listy produktów
        headless: Czy headless
        username: Nazwa użytkownika
        password: Hasło
        max_products: Maksymalna liczba produktów
        
    Returns:
        Dict z wynikami
    """
    agent = Agent(headless=headless)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        return loop.run_until_complete(
            agent.execute_django_admin_product_mapping(
                base_url=base_url,
                products_url=products_url,
                username=username,
                password=password,
                max_products=max_products
            )
        )
    finally:
        loop.run_until_complete(agent.stop())

