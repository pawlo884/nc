"""
Klasa Workflow - orkiestracja akcji agenta
"""
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from .action import Action, ActionType, ActionResult
from .browser import Browser

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """Pojedynczy krok w workflow"""
    name: str
    action: Action
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    on_success: Optional[Callable[[ActionResult], None]] = None
    on_error: Optional[Callable[[ActionResult], None]] = None


class Workflow:
    """
    Workflow - sekwencja akcji do wykonania przez agenta.
    Obsługuje warunki, retry, i callbacki.
    """
    
    def __init__(self, name: str, steps: List[WorkflowStep] = None):
        """
        Args:
            name: Nazwa workflow
            steps: Lista kroków do wykonania
        """
        self.name = name
        self.steps: List[WorkflowStep] = steps or []
        self.context: Dict[str, Any] = {}  # Kontekst współdzielony między krokami
        
    def add_step(
        self,
        name: str,
        action: Action,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        on_success: Optional[Callable[[ActionResult], None]] = None,
        on_error: Optional[Callable[[ActionResult], None]] = None
    ):
        """Dodaje krok do workflow"""
        step = WorkflowStep(
            name=name,
            action=action,
            condition=condition,
            on_success=on_success,
            on_error=on_error
        )
        self.steps.append(step)
        return self
        
    async def execute(self, browser: Browser) -> List[ActionResult]:
        """
        Wykonuje workflow na przeglądarce
        
        Args:
            browser: Instancja Browser do użycia
            
        Returns:
            Lista wyników akcji
        """
        results = []
        logger.info(f'Rozpoczynam workflow: {self.name} ({len(self.steps)} kroków)')
        
        for i, step in enumerate(self.steps):
            logger.info(f'Krok {i+1}/{len(self.steps)}: {step.name}')
            
            # Sprawdź warunek jeśli istnieje
            if step.condition and not step.condition(self.context):
                logger.info(f'Pominięto krok {step.name} - warunek nie spełniony')
                continue
                
            # Wykonaj akcję
            result = await self._execute_action(browser, step.action)
            results.append(result)
            
            # Zapisz wynik w kontekście
            self.context[f'step_{i}'] = result.to_dict()
            
            # Sprawdź czy wynik zawiera navigate_to_url (z evaluate)
            if result.success and result.data and isinstance(result.data, dict):
                navigate_to_url = result.data.get('navigate_to_url')
                if navigate_to_url:
                    logger.info(f'Nawigacja do: {navigate_to_url}')
                    nav_result = await browser.navigate(navigate_to_url)
                    if nav_result.get('success'):
                        logger.info('Nawigacja zakończona pomyślnie')
            
            # Wywołaj callbacki
            if result.success and step.on_success:
                step.on_success(result)
            elif not result.success and step.on_error:
                step.on_error(result)
                
            # Jeśli akcja nie jest opcjonalna i się nie powiodła, zatrzymaj workflow
            if not result.success and not step.action.optional:
                logger.error(f'Workflow zatrzymany - błąd w kroku {step.name}')
                break
                
        logger.info(f'Workflow {self.name} zakończony. Wykonano {len(results)} akcji.')
        return results
        
    async def _execute_action(self, browser: Browser, action: Action) -> ActionResult:
        """Wykonuje pojedynczą akcję"""
        from datetime import datetime
        try:
            from django.utils import timezone as django_timezone
            get_timestamp = lambda: django_timezone.now().isoformat()
        except (ImportError, RuntimeError):
            get_timestamp = lambda: datetime.now().isoformat()
            
        try:
            logger.info(f'Wykonuję akcję: {action.action_type.value}')
            
            if action.action_type == ActionType.NAVIGATE:
                url = action.params['url']
                logger.info(f'  Nawigacja do: {url}')
                result_data = await browser.navigate(
                    url,
                    wait_until=action.params.get('wait_until', 'load'),
                    timeout=action.params.get('timeout', 30000)
                )
                logger.info(f'  Wynik nawigacji: {result_data.get("success")} - {result_data.get("url", "N/A")}')
            elif action.action_type == ActionType.CLICK:
                selector = action.params['selector']
                logger.info(f'  Kliknięcie w: {selector}')
                result_data = await browser.click(
                    selector,
                    timeout=action.params.get('timeout', 10000)
                )
                logger.info(f'  Wynik kliknięcia: {result_data.get("success")}')
            elif action.action_type == ActionType.FILL:
                selector = action.params['selector']
                value = action.params['value']
                # Nie loguj pełnego hasła
                display_value = value if len(value) < 20 else value[:10] + '...'
                logger.info(f'  Wypełnienie {selector}: {display_value}')
                result_data = await browser.fill(
                    selector,
                    value,
                    timeout=action.params.get('timeout', 10000)
                )
                logger.info(f'  Wynik wypełnienia: {result_data.get("success")}')
            elif action.action_type == ActionType.WAIT_FOR:
                selector = action.params['selector']
                logger.info(f'  Oczekiwanie na: {selector}')
                result_data = await browser.wait_for_selector(
                    selector,
                    timeout=action.params.get('timeout', 10000),
                    state=action.params.get('state', 'visible')
                )
                logger.info(f'  Wynik oczekiwania: {result_data.get("success")}')
            elif action.action_type == ActionType.WAIT:
                seconds = action.params.get('seconds', 1)
                logger.info(f'  Oczekiwanie {seconds}s')
                await browser.wait(seconds)
                result_data = {'success': True}
            elif action.action_type == ActionType.EVALUATE:
                logger.info(f'  Wykonywanie JavaScript')
                result_data = await browser.evaluate(action.params['expression'])
                logger.info(f'  Wynik evaluate: {result_data.get("success")}')
            else:
                result_data = {'success': False, 'error': f'Nieobsługiwany typ akcji: {action.action_type}'}
                
            success = result_data.get('success', False)
            error = result_data.get('error') if not success else None
            
            if not success:
                logger.warning(f'  ❌ Akcja nie powiodła się: {error}')
            else:
                logger.info(f'  ✅ Akcja zakończona pomyślnie')
            
            return ActionResult(
                success=success,
                action_type=action.action_type,
                data=result_data,
                error=error,
                timestamp=get_timestamp()
            )
            
        except Exception as e:
            logger.error(f'Błąd podczas wykonywania akcji {action.action_type.value}: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return ActionResult(
                success=False,
                action_type=action.action_type,
                error=str(e),
                timestamp=get_timestamp()
            )

