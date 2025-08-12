import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, Any, Optional
from .models import WebSession, ScrapingTask, ScrapingResult, WebAgentLog

logger = logging.getLogger(__name__)


class WebAgent:
    """Prosty agent do łączenia się ze stronami internetowymi"""

    def __init__(self, session: WebSession):
        self.session = session
        self.session_obj = requests.Session()
        self._setup_session()

    def _setup_session(self):
        """Konfiguruje sesję requests"""
        # Ustaw user agent
        if self.session.user_agent:
            self.session_obj.headers.update(
                {'User-Agent': self.session.user_agent})
        else:
            self.session_obj.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

        # Dodaj custom headers
        if self.session.headers:
            self.session_obj.headers.update(self.session.headers)

        # Dodaj cookies
        if self.session.cookies:
            for key, value in self.session.cookies.items():
                self.session_obj.cookies.set(key, value)

        # Ustaw proxy
        if self.session.proxy:
            self.session_obj.proxies = {
                'http': self.session.proxy,
                'https': self.session.proxy
            }

    def connect_to_page(self, url: str, task: Optional[ScrapingTask] = None) -> Dict[str, Any]:
        """
        Łączy się ze stroną i pobiera dane

        Args:
            url: URL strony do połączenia
            task: Opcjonalne zadanie scraping

        Returns:
            Dict z danymi strony
        """
        try:
            # Log rozpoczęcia
            self._log_action(f"Łączenie z: {url}", 'INFO', task)

            # Wykonaj request
            response = self.session_obj.get(
                url,
                timeout=self.session.timeout,
                allow_redirects=True
            )

            # Sprawdź status
            response.raise_for_status()

            # Pobierz HTML
            html_content = response.text

            # Parsuj HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # Podstawowe dane
            result_data = {
                'url': url,
                'status_code': response.status_code,
                'title': soup.title.string if soup.title else '',
                'content_length': len(html_content),
                'headers': dict(response.headers),
                'cookies': dict(response.cookies),
                'encoding': response.encoding,
                'final_url': response.url
            }

            # Jeśli mamy zadanie z selektorami, wyciągnij dane
            if task and task.selectors:
                extracted_data = self._extract_data_with_selectors(
                    soup, task.selectors)
                result_data['extracted_data'] = extracted_data

            # Zapisz wynik
            if task:
                ScrapingResult.objects.create(
                    task=task,
                    data=result_data,
                    raw_html=html_content
                )

            # Log sukcesu
            self._log_action(f"Pomyślnie połączono z: {url}", 'INFO', task)

            return result_data

        except requests.exceptions.RequestException as e:
            error_msg = f"Błąd połączenia z {url}: {str(e)}"
            self._log_action(error_msg, 'ERROR', task)
            raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Nieoczekiwany błąd podczas łączenia z {url}: {str(e)}"
            self._log_action(error_msg, 'ERROR', task)
            raise Exception(error_msg)

    def _extract_data_with_selectors(self, soup: BeautifulSoup, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Wyciąga dane używając selektorów CSS"""
        extracted = {}

        for key, selector in selectors.items():
            try:
                elements = soup.select(selector)
                if elements:
                    if len(elements) == 1:
                        extracted[key] = elements[0].get_text(strip=True)
                    else:
                        extracted[key] = [elem.get_text(
                            strip=True) for elem in elements]
                else:
                    extracted[key] = None
            except Exception as e:
                extracted[key] = f"Błąd selektora {selector}: {str(e)}"

        return extracted

    def _log_action(self, message: str, level: str, task: Optional[ScrapingTask] = None):
        """Zapisuje log akcji"""
        WebAgentLog.objects.create(
            session=self.session,
            task=task,
            level=level,
            message=message
        )
        logger.info(f"WebAgent: {message}")


def create_web_agent(session_name: str, url: str, **kwargs) -> WebAgent:
    """
    Tworzy nowego web agenta

    Args:
        session_name: Nazwa sesji
        url: URL docelowy
        **kwargs: Dodatkowe parametry sesji

    Returns:
        WebAgent instance
    """
    session = WebSession.objects.create(
        name=session_name,
        url=url,
        **kwargs
    )
    return WebAgent(session)


def connect_to_website(url: str, session_name: str = "Default Session", **kwargs) -> Dict[str, Any]:
    """
    Szybka funkcja do łączenia się ze stroną

    Args:
        url: URL strony
        session_name: Nazwa sesji
        **kwargs: Parametry sesji

    Returns:
        Dane ze strony
    """
    agent = create_web_agent(session_name, url, **kwargs)
    return agent.connect_to_page(url)
