from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
from typing import Dict, Any, Optional
from .models import WebSession, ScrapingTask, ScrapingResult, WebAgentLog

logger = logging.getLogger(__name__)


class BrowserAgent:
    """Agent działający w przeglądarce na żywo"""

    def __init__(self, session: WebSession, headless: bool = False):
        self.session = session
        self.driver = None
        self.headless = headless
        self._setup_driver()

    def _setup_driver(self):
        """Konfiguruje driver przeglądarki"""
        try:
            chrome_options = Options()

            # Ustawienia headless
            if self.headless:
                chrome_options.add_argument("--headless")

            # Dodatkowe opcje dla stabilności
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            # User agent
            if self.session.user_agent:
                chrome_options.add_argument(
                    f"--user-agent={self.session.user_agent}")
            else:
                chrome_options.add_argument(
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

            # Proxy
            if self.session.proxy:
                chrome_options.add_argument(
                    f"--proxy-server={self.session.proxy}")

            # Inicjalizacja driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(
                service=service, options=chrome_options)

            # Ustaw timeout
            self.driver.set_page_load_timeout(self.session.timeout)
            self.driver.implicitly_wait(10)

            # Dodaj cookies jeśli są
            if self.session.cookies:
                self.driver.get("https://example.com")  # Tymczasowa strona
                for key, value in self.session.cookies.items():
                    self.driver.add_cookie({"name": key, "value": value})

            self._log_action("Przeglądarka została uruchomiona", 'INFO')

        except Exception as e:
            error_msg = f"Błąd podczas uruchamiania przeglądarki: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            raise Exception(error_msg)

    def navigate_to(self, url: str, task: Optional[ScrapingTask] = None) -> Dict[str, Any]:
        """
        Przechodzi do strony w przeglądarce

        Args:
            url: URL do przejścia
            task: Opcjonalne zadanie scraping

        Returns:
            Dict z danymi strony
        """
        try:
            self._log_action(f"Przechodzę do: {url}", 'INFO', task)

            # Przejdź do strony
            self.driver.get(url)

            # Czekaj na załadowanie
            WebDriverWait(self.driver, self.session.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Pobierz dane strony
            result_data = {
                'url': url,
                'title': self.driver.title,
                'current_url': self.driver.current_url,
                'page_source_length': len(self.driver.page_source),
                'cookies': {cookie['name']: cookie['value'] for cookie in self.driver.get_cookies()},
                'window_size': self.driver.get_window_size(),
                'screenshot_taken': False
            }

            # Zrób screenshot
            try:
                screenshot_path = f"screenshots/{task.id if task else 'browser'}_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_path)
                result_data['screenshot_path'] = screenshot_path
                result_data['screenshot_taken'] = True
            except Exception as e:
                self._log_action(f"Błąd screenshot: {str(e)}", 'WARNING', task)

            # Zapisz wynik
            if task:
                ScrapingResult.objects.create(
                    task=task,
                    data=result_data,
                    raw_html=self.driver.page_source
                )

            self._log_action(f"Pomyślnie przejście do: {url}", 'INFO', task)
            return result_data

        except Exception as e:
            error_msg = f"Błąd podczas przechodzenia do {url}: {str(e)}"
            self._log_action(error_msg, 'ERROR', task)
            raise Exception(error_msg)

    def click_element(self, selector: str, selector_type: str = "css") -> bool:
        """
        Klika element na stronie

        Args:
            selector: Selektory elementu
            selector_type: Typ selektora (css, xpath, id, name, class)

        Returns:
            True jeśli kliknięcie udane
        """
        try:
            by_map = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "id": By.ID,
                "name": By.NAME,
                "class": By.CLASS_NAME
            }

            by = by_map.get(selector_type, By.CSS_SELECTOR)

            # Czekaj na element
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((by, selector))
            )

            # Kliknij
            element.click()
            self._log_action(f"Kliknięto element: {selector}", 'INFO')
            return True

        except Exception as e:
            error_msg = f"Błąd podczas klikania elementu {selector}: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return False

    def type_text(self, selector: str, text: str, selector_type: str = "css") -> bool:
        """
        Wpisuje tekst w pole

        Args:
            selector: Selektory pola
            text: Tekst do wpisania
            selector_type: Typ selektora

        Returns:
            True jeśli wpisanie udane
        """
        try:
            by_map = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "id": By.ID,
                "name": By.NAME,
                "class": By.CLASS_NAME
            }

            by = by_map.get(selector_type, By.CSS_SELECTOR)

            # Znajdź element
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((by, selector))
            )

            # Wyczyść i wpisz tekst
            element.clear()
            element.send_keys(text)

            self._log_action(f"Wpisano tekst w: {selector}", 'INFO')
            return True

        except Exception as e:
            error_msg = f"Błąd podczas wpisywania w {selector}: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return False

    def scroll_to_element(self, selector: str, selector_type: str = "css") -> bool:
        """
        Przewija do elementu

        Args:
            selector: Selektory elementu
            selector_type: Typ selektora

        Returns:
            True jeśli przewijanie udane
        """
        try:
            by_map = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "id": By.ID,
                "name": By.NAME,
                "class": By.CLASS_NAME
            }

            by = by_map.get(selector_type, By.CSS_SELECTOR)

            element = self.driver.find_element(by, selector)
            self.driver.execute_script(
                "arguments[0].scrollIntoView();", element)

            self._log_action(f"Przewinięto do elementu: {selector}", 'INFO')
            return True

        except Exception as e:
            error_msg = f"Błąd podczas przewijania do {selector}: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return False

    def wait_for_element(self, selector: str, timeout: int = 10, selector_type: str = "css") -> bool:
        """
        Czeka na pojawienie się elementu

        Args:
            selector: Selektory elementu
            timeout: Czas oczekiwania w sekundach
            selector_type: Typ selektora

        Returns:
            True jeśli element się pojawił
        """
        try:
            by_map = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "id": By.ID,
                "name": By.NAME,
                "class": By.CLASS_NAME
            }

            by = by_map.get(selector_type, By.CSS_SELECTOR)

            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )

            self._log_action(f"Element pojawił się: {selector}", 'INFO')
            return True

        except Exception as e:
            error_msg = f"Element nie pojawił się: {selector} - {str(e)}"
            self._log_action(error_msg, 'WARNING')
            return False

    def get_element_text(self, selector: str, selector_type: str = "css") -> str:
        """
        Pobiera tekst z elementu

        Args:
            selector: Selektory elementu
            selector_type: Typ selektora

        Returns:
            Tekst elementu
        """
        try:
            by_map = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "id": By.ID,
                "name": By.NAME,
                "class": By.CLASS_NAME
            }

            by = by_map.get(selector_type, By.CSS_SELECTOR)

            element = self.driver.find_element(by, selector)
            text = element.text

            self._log_action(f"Pobrano tekst z: {selector}", 'INFO')
            return text

        except Exception as e:
            error_msg = f"Błąd podczas pobierania tekstu z {selector}: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return ""

    def take_screenshot(self, filename: str = None) -> str:
        """
        Robi screenshot strony

        Args:
            filename: Nazwa pliku (opcjonalnie)

        Returns:
            Ścieżka do screenshot
        """
        try:
            if not filename:
                filename = f"screenshot_{int(time.time())}.png"

            screenshot_path = f"screenshots/{filename}"
            self.driver.save_screenshot(screenshot_path)

            self._log_action(f"Zrobiono screenshot: {screenshot_path}", 'INFO')
            return screenshot_path

        except Exception as e:
            error_msg = f"Błąd podczas robienia screenshot: {str(e)}"
            self._log_action(error_msg, 'ERROR')
            return ""

    def close(self):
        """Zamyka przeglądarkę"""
        if self.driver:
            self.driver.quit()
            self._log_action("Przeglądarka została zamknięta", 'INFO')

    def _log_action(self, message: str, level: str, task: Optional[ScrapingTask] = None):
        """Zapisuje log akcji"""
        WebAgentLog.objects.create(
            session=self.session,
            task=task,
            level=level,
            message=message
        )
        logger.info(f"BrowserAgent: {message}")


def create_browser_agent(session_name: str, url: str, headless: bool = False, **kwargs) -> BrowserAgent:
    """
    Tworzy nowego browser agenta

    Args:
        session_name: Nazwa sesji
        url: URL docelowy
        headless: Czy uruchomić w trybie headless
        **kwargs: Dodatkowe parametry sesji

    Returns:
        BrowserAgent instance
    """
    session = WebSession.objects.create(
        name=session_name,
        url=url,
        **kwargs
    )
    return BrowserAgent(session, headless)


def navigate_with_browser(url: str, session_name: str = "Browser Session", headless: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Szybka funkcja do nawigacji w przeglądarce

    Args:
        url: URL strony
        session_name: Nazwa sesji
        headless: Czy uruchomić w trybie headless
        **kwargs: Parametry sesji

    Returns:
        Dane ze strony
    """
    agent = create_browser_agent(session_name, url, headless, **kwargs)
    try:
        result = agent.navigate_to(url)
        return result
    finally:
        agent.close()
