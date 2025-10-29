"""
Moduł do automatyzacji przeglądarki używając Playwright
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from django.utils import timezone

logger = logging.getLogger(__name__)


class BrowserAutomation:
    """Klasa do zarządzania automatyzacją przeglądarki"""

    def __init__(self, headless: bool = True, browser_type: str = 'chromium'):
        """
        Inicjalizuje BrowserAutomation

        Args:
            headless: Czy uruchomić przeglądarkę w trybie headless
            browser_type: Typ przeglądarki ('chromium', 'firefox', 'webkit')
        """
        self.headless = headless
        self.browser_type = browser_type
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def start(self):
        """Uruchamia przeglądarkę i tworzy kontekst"""
        try:
            self.playwright = await async_playwright().start()

            if self.browser_type == 'chromium':
                self.browser = await self.playwright.chromium.launch(headless=self.headless)
            elif self.browser_type == 'firefox':
                self.browser = await self.playwright.firefox.launch(headless=self.headless)
            elif self.browser_type == 'webkit':
                self.browser = await self.playwright.webkit.launch(headless=self.headless)
            else:
                raise ValueError(
                    f'Nieobsługiwany typ przeglądarki: {self.browser_type}')

            # Utwórz kontekst z domyślnymi ustawieniami
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            # Utwórz nową stronę
            self.page = await self.context.new_page()

            logger.info(f'Przeglądarka {self.browser_type} uruchomiona')

        except Exception as e:
            logger.error(f'Błąd podczas uruchamiania przeglądarki: {str(e)}')
            raise

    async def stop(self):
        """Zatrzymuje przeglądarkę i zwalnia zasoby"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            logger.info('Przeglądarka zatrzymana')

        except Exception as e:
            logger.error(f'Błąd podczas zatrzymywania przeglądarki: {str(e)}')

    async def navigate(self, url: str, wait_until: str = 'load', timeout: int = 30000):
        """Nawiguje do podanego URL"""
        try:
            if not self.page:
                raise RuntimeError(
                    'Strona nie została utworzona. Wywołaj start() najpierw.')

            await self.page.goto(url, wait_until=wait_until, timeout=timeout)
            logger.info(f'Nawigacja do: {url}')

            return {
                'url': url,
                'final_url': self.page.url,
                'title': await self.page.title(),
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas nawigacji do {url}: {str(e)}')
            raise

    async def get_page_content(self, wait_for_selector: Optional[str] = None):
        """Pobiera zawartość strony"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            if wait_for_selector:
                await self.page.wait_for_selector(wait_for_selector, timeout=10000)

            content = await self.page.content()
            text = await self.page.inner_text('body')

            return {
                'html': content,
                'text': text[:5000],  # Ogranicz do 5000 znaków
                'url': self.page.url,
                'title': await self.page.title(),
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(
                f'Błąd podczas pobierania zawartości strony: {str(e)}')
            raise

    async def click(self, selector: str, timeout: int = 10000):
        """Klikniecie w element"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            await self.page.click(selector, timeout=timeout)
            logger.info(f'Kliknięcie w element: {selector}')

            return {
                'action': 'click',
                'selector': selector,
                'success': True,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas kliknięcia w {selector}: {str(e)}')
            raise

    async def fill(self, selector: str, value: str, timeout: int = 10000):
        """Wypełnia pole formularza"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            await self.page.fill(selector, value, timeout=timeout)
            logger.info(f'Wypełnienie pola {selector}')

            return {
                'action': 'fill',
                'selector': selector,
                'value': value,
                'success': True,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas wypełniania {selector}: {str(e)}')
            raise

    async def fill_form(self, fields: List[Dict[str, str]], timeout: int = 10000):
        """Wypełnia formularz z wieloma polami"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            results = []
            for field in fields:
                selector = field.get('selector')
                value = field.get('value')

                if selector and value:
                    await self.page.fill(selector, value, timeout=timeout)
                    results.append({
                        'selector': selector,
                        'success': True
                    })

            logger.info(f'Wypełniono formularz: {len(fields)} pól')

            return {
                'action': 'fill_form',
                'fields_filled': len(results),
                'results': results,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas wypełniania formularza: {str(e)}')
            raise

    async def wait_for(self, selector: Optional[str] = None, text: Optional[str] = None, timeout: int = 10000):
        """Czeka na element lub tekst"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            if selector:
                await self.page.wait_for_selector(selector, timeout=timeout)
                logger.info(f'Element pojawił się: {selector}')
            elif text:
                await self.page.wait_for_selector(f'text={text}', timeout=timeout)
                logger.info(f'Tekst pojawił się: {text}')
            else:
                await self.page.wait_for_timeout(timeout)

            return {
                'action': 'wait_for',
                'selector': selector,
                'text': text,
                'success': True,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas oczekiwania: {str(e)}')
            raise

    async def take_screenshot(self, full_page: bool = False, path: Optional[str] = None):
        """Robię zrzut ekranu"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            await self.page.screenshot(full_page=full_page, path=path)

            return {
                'action': 'screenshot',
                'full_page': full_page,
                'path': path,
                'success': True,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas robienia zrzutu ekranu: {str(e)}')
            raise

    async def evaluate(self, expression: str):
        """Wykonuje JavaScript na stronie"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            result = await self.page.evaluate(expression)

            return {
                'action': 'evaluate',
                'expression': expression,
                'result': result,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Błąd podczas wykonywania JavaScript: {str(e)}')
            raise

    async def get_text(self, selector: str):
        """Pobiera tekst z elementu"""
        try:
            if not self.page:
                raise RuntimeError('Strona nie została utworzona.')

            text = await self.page.inner_text(selector)

            return {
                'action': 'get_text',
                'selector': selector,
                'text': text,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(
                f'Błąd podczas pobierania tekstu z {selector}: {str(e)}')
            raise

    async def execute_actions(self, actions: List[Dict[str, Any]]):
        """Wykonuje listę akcji"""
        results = []

        for action in actions:
            action_type = action.get('type')

            try:
                if action_type == 'navigate':
                    result = await self.navigate(
                        action.get('url'),
                        wait_until=action.get('wait_until', 'load'),
                        timeout=action.get('timeout', 30000)
                    )
                elif action_type == 'click':
                    result = await self.click(
                        action.get('selector'),
                        timeout=action.get('timeout', 10000)
                    )
                elif action_type == 'fill':
                    result = await self.fill(
                        action.get('selector'),
                        action.get('value'),
                        timeout=action.get('timeout', 10000)
                    )
                elif action_type == 'fill_form':
                    result = await self.fill_form(
                        action.get('fields', []),
                        timeout=action.get('timeout', 10000)
                    )
                elif action_type == 'wait_for':
                    result = await self.wait_for(
                        selector=action.get('selector'),
                        text=action.get('text'),
                        timeout=action.get('timeout', 10000)
                    )
                elif action_type == 'screenshot':
                    result = await self.take_screenshot(
                        full_page=action.get('full_page', False),
                        path=action.get('path')
                    )
                elif action_type == 'evaluate':
                    result = await self.evaluate(action.get('expression'))
                elif action_type == 'get_text':
                    result = await self.get_text(action.get('selector'))
                else:
                    result = {'error': f'Nieznany typ akcji: {action_type}'}

                results.append({
                    'action': action_type,
                    'result': result,
                    'success': 'error' not in result
                })

            except Exception as e:
                results.append({
                    'action': action_type,
                    'error': str(e),
                    'success': False
                })

        return results


# Funkcje pomocnicze dla synchronicznego użycia w Celery
def run_async(coro):
    """Uruchamia funkcję async w synchronicznym kontekście"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def scrape_with_browser(url: str, wait_for_selector: Optional[str] = None, headless: bool = True) -> Dict:
    """
    Scrapuje stronę używając przeglądarki (synchroniczna funkcja dla Celery)

    Args:
        url: URL do scrapowania
        wait_for_selector: Opcjonalny selektor CSS do oczekiwania
        headless: Czy uruchomić w trybie headless

    Returns:
        Słownik z zawartością strony
    """
    async def _scrape():
        automation = BrowserAutomation(headless=headless)
        try:
            await automation.start()
            await automation.navigate(url)
            content = await automation.get_page_content(wait_for_selector)
            return content
        finally:
            await automation.stop()

    return run_async(_scrape())


def execute_browser_actions(actions: List[Dict[str, Any]], headless: bool = True) -> List[Dict]:
    """
    Wykonuje listę akcji w przeglądarce (synchroniczna funkcja dla Celery)

    Args:
        actions: Lista akcji do wykonania
        headless: Czy uruchomić w trybie headless

    Returns:
        Lista wyników akcji
    """
    async def _execute():
        automation = BrowserAutomation(headless=headless)
        try:
            await automation.start()
            results = await automation.execute_actions(actions)
            return results
        finally:
            await automation.stop()

    return run_async(_execute())
