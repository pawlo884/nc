"""
Klient PrestaShop WebAPI (REST, zasoby jako XML pod /api/<resource>).

W przeciwieństwie do matterhorn1/tabu/mada (import KATALOGU hurtowni do naszej
bazy) - PrestaShop to kanał SPRZEDAŻOWY: wypychamy dane MPD DO sklepu (POST/PUT),
nie pobieramy stamtąd niczego do lokalnej bazy. Stąd brak modelu bazodanowego
"zdalnego katalogu" - tylko klient + (docelowo) tabela mapowania MPD -> PrestaShop ID.

Auth: HTTP Basic, klucz webservice jako login, puste hasło (standard PrestaShop).
Dokumentacja: https://devdocs.prestashop-project.org/8/webservice/

Użycie:
    client = PrestaShopApiClient()
    resources = client.list_resources()               # GET /api/
    schema = client.get_blank_schema('products')       # GET /api/products?schema=blank
    xml = client.get('products', resource_id=42)       # GET /api/products/42
    created = client.create('products', xml_bytes)     # POST /api/products
    client.update('products', 42, xml_bytes)           # PUT /api/products/42
    client.delete('products', 42)                      # DELETE /api/products/42
"""
import logging
from typing import Optional
from xml.etree import ElementTree as ET

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PrestaShopApiError(Exception):
    pass


class PrestaShopApiClient:
    def __init__(self, base_url=None, api_key=None, timeout=30, verify_ssl=True):
        base_url = (base_url or settings.PRESTASHOP_API_URL).rstrip('/')
        # Akceptuj zarowno "https://sklep.pl" jak i "https://sklep.pl/api" -
        # _url() i tak dokleja "/api/<resource>", wiec drugi zapis dawalby
        # podwojne /api/api/... gdyby nie ta normalizacja.
        if base_url.endswith('/api'):
            base_url = base_url[:-len('/api')]
        self.base_url = base_url
        self.api_key = api_key or settings.PRESTASHOP_API_KEY
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        if not self.base_url:
            raise PrestaShopApiError('Brak PRESTASHOP_API_URL w konfiguracji.')
        if not self.api_key:
            raise PrestaShopApiError('Brak PRESTASHOP_API_KEY w konfiguracji.')

    def _url(self, resource: str, resource_id: Optional[int] = None) -> str:
        url = f'{self.base_url}/api/{resource}'
        if resource_id is not None:
            url = f'{url}/{resource_id}'
        return url

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            response = requests.request(
                method, url,
                auth=(self.api_key, ''),
                timeout=self.timeout,
                verify=self.verify_ssl,
                **kwargs,
            )
        except requests.exceptions.RequestException as exc:
            # auth idzie przez requests `auth=`, nie query string - str(exc) nie
            # zawiera klucza, ale i tak nie logujemy samego requests.Request.
            raise PrestaShopApiError(f'Błąd połączenia z PrestaShop ({method} {url}): {exc}') from exc

        if response.status_code >= 400:
            raise PrestaShopApiError(
                f'{method} {url} -> HTTP {response.status_code}: '
                f'{_extract_error_message(response.content)}'
            )
        return response

    def list_resources(self) -> dict:
        """GET /api/ - lista włączonych zasobów WebAPI. Najlżejszy sposób na test
        połączenia/autoryzacji, bez dotykania żadnych danych."""
        response = self._request('GET', f'{self.base_url}/api/')
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            raise PrestaShopApiError(f'Nieoczekiwana odpowiedź z /api/ (nie XML): {exc}') from exc
        api_el = root.find('api')
        if api_el is None:
            return {}
        resources = {}
        for child in api_el:
            href = child.get('xlink:href') or child.get(
                '{http://www.w3.org/1999/xlink}href')
            resources[child.tag] = href
        return resources

    def get_blank_schema(self, resource: str) -> bytes:
        """GET /api/<resource>?schema=blank - pusty szkielet XML z wszystkimi
        polami, jakich oczekuje TA konkretna instalacja PrestaShop (różni się
        między wersjami/konfiguracją sklepu) - punkt wyjścia do budowy payloadu."""
        response = self._request(
            'GET', self._url(resource), params={'schema': 'blank'})
        return response.content

    def get(self, resource: str, resource_id: Optional[int] = None, params: Optional[dict] = None) -> bytes:
        response = self._request(
            'GET', self._url(resource, resource_id), params=params)
        return response.content

    def create(self, resource: str, xml_body: bytes) -> bytes:
        response = self._request(
            'POST', self._url(resource),
            data=xml_body, headers={'Content-Type': 'text/xml'},
        )
        return response.content

    def update(self, resource: str, resource_id: int, xml_body: bytes) -> bytes:
        response = self._request(
            'PUT', self._url(resource, resource_id),
            data=xml_body, headers={'Content-Type': 'text/xml'},
        )
        return response.content

    def delete(self, resource: str, resource_id: int) -> None:
        self._request('DELETE', self._url(resource, resource_id))


def _extract_error_message(content: bytes) -> str:
    """PrestaShop zwraca błędy jako XML: <prestashop><errors><error><code/>
    <message/></error></errors></prestashop>. Fallback na surową treść, gdy
    to nie jest poprawny XML (np. HTML strony błędu serwera)."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return content[:500].decode('utf-8', errors='replace')
    messages = []
    for error_el in root.findall('.//errors/error'):
        code = error_el.findtext('code', '')
        message = error_el.findtext('message', '')
        messages.append(f'[{code}] {message}'.strip())
    return '; '.join(messages) if messages else content[:500].decode('utf-8', errors='replace')
