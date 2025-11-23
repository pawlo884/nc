"""
Klasa Browser - zarządzanie przeglądarką Playwright
"""
import logging
import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser as PlaywrightBrowser, Page, BrowserContext

logger = logging.getLogger(__name__)


class Browser:
    """
    Klasa do zarządzania przeglądarką Playwright.
    Opakowuje Playwright API w prostszy interfejs.
    """
    
    def __init__(self, headless: bool = False, browser_type: str = 'chromium'):
        """
        Args:
            headless: Czy uruchomić przeglądarkę w trybie headless
            browser_type: Typ przeglądarki ('chromium', 'firefox', 'webkit')
        """
        self.headless = headless
        self.browser_type = browser_type
        self.playwright = None
        self.browser: Optional[PlaywrightBrowser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def start(self):
        """Uruchamia przeglądarkę"""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            
        browser_launcher = getattr(self.playwright, self.browser_type)
        self.browser = await browser_launcher.launch(headless=self.headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        logger.info(f'Przeglądarka {self.browser_type} uruchomiona (headless={self.headless})')
        
    async def stop(self):
        """Zatrzymuje przeglądarkę"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            
        logger.info('Przeglądarka zatrzymana')
        
    async def navigate(self, url: str, wait_until: str = 'load', timeout: int = 30000) -> Dict[str, Any]:
        """
        Nawiguje do URL
        
        Args:
            url: URL do przejścia
            wait_until: Kiedy uznać że strona załadowana ('load', 'domcontentloaded', 'networkidle')
            timeout: Timeout w milisekundach
            
        Returns:
            Dict z informacjami o nawigacji
        """
        if not self.page:
            raise RuntimeError('Przeglądarka nie jest uruchomiona. Wywołaj start() najpierw.')
            
        try:
            await self.page.goto(url, wait_until=wait_until, timeout=timeout)
            return {
                'success': True,
                'url': self.page.url,
                'title': await self.page.title()
            }
        except Exception as e:
            logger.error(f'Błąd podczas nawigacji do {url}: {str(e)}')
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
            
    async def click(self, selector: str, timeout: int = 10000) -> Dict[str, Any]:
        """
        Klika w element
        
        Args:
            selector: CSS selector elementu
            timeout: Timeout w milisekundach
            
        Returns:
            Dict z wynikiem akcji
        """
        if not self.page:
            raise RuntimeError('Przeglądarka nie jest uruchomiona.')
            
        try:
            await self.page.click(selector, timeout=timeout)
            return {'success': True, 'selector': selector}
        except Exception as e:
            logger.error(f'Błąd podczas kliknięcia w {selector}: {str(e)}')
            return {'success': False, 'error': str(e), 'selector': selector}
            
    async def fill(self, selector: str, value: str, timeout: int = 10000) -> Dict[str, Any]:
        """
        Wypełnia pole formularza
        
        Args:
            selector: CSS selector pola
            value: Wartość do wpisania
            timeout: Timeout w milisekundach
            
        Returns:
            Dict z wynikiem akcji
        """
        if not self.page:
            raise RuntimeError('Przeglądarka nie jest uruchomiona.')
            
        try:
            await self.page.fill(selector, value, timeout=timeout)
            return {'success': True, 'selector': selector, 'value': value}
        except Exception as e:
            logger.error(f'Błąd podczas wypełniania {selector}: {str(e)}')
            return {'success': False, 'error': str(e), 'selector': selector}
            
    async def wait_for_selector(self, selector: str, timeout: int = 10000, state: str = 'visible') -> Dict[str, Any]:
        """
        Oczekuje na pojawienie się elementu
        
        Args:
            selector: CSS selector elementu
            timeout: Timeout w milisekundach
            state: Stan elementu ('visible', 'hidden', 'attached', 'detached')
            
        Returns:
            Dict z wynikiem akcji
        """
        if not self.page:
            raise RuntimeError('Przeglądarka nie jest uruchomiona.')
            
        try:
            await self.page.wait_for_selector(selector, timeout=timeout, state=state)
            return {'success': True, 'selector': selector, 'state': state}
        except Exception as e:
            logger.error(f'Błąd podczas oczekiwania na {selector}: {str(e)}')
            return {'success': False, 'error': str(e), 'selector': selector}
            
    async def evaluate(self, expression: str) -> Dict[str, Any]:
        """
        Wykonuje JavaScript w kontekście strony
        
        Args:
            expression: Kod JavaScript do wykonania
            
        Returns:
            Dict z wynikiem akcji i wartością zwróconą
        """
        if not self.page:
            raise RuntimeError('Przeglądarka nie jest uruchomiona.')
            
        try:
            result = await self.page.evaluate(expression)
            return {'success': True, 'result': result}
        except Exception as e:
            logger.error(f'Błąd podczas wykonywania JavaScript: {str(e)}')
            return {'success': False, 'error': str(e)}
            
    async def wait(self, seconds: float):
        """Oczekuje określoną liczbę sekund"""
        await asyncio.sleep(seconds)
        
    def is_running(self) -> bool:
        """Sprawdza czy przeglądarka jest uruchomiona"""
        return self.page is not None and not self.page.is_closed()

