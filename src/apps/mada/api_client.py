"""
Klient API Mada.

GET {base_url}/get_xml.php?l=<login>&p=<password>
    - bez `file`  -> manifest dostępnych plików (<FILES><FILE><NAME>/<DATE>/<TYPE>full|partial</TYPE></FILE>...)
    - z `file=<NAME>` -> ZIP zawierający products.xml

Auth przez parametry zapytania (nie nagłówki) - inny wzorzec niż matterhorn1/tabu.
"""
import io
import logging
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from xml.etree import ElementTree as ET

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Auth (login `l` i hasło `p`) idzie przez query string, więc wyjątki requests/
# urllib3 (np. ConnectionError, MaxRetryError) mają pełny URL - łącznie z
# hasłem w plaintext - wpisany w swój str(). Trzeba to redagować, zanim
# trafi do logów/Sentry.
_CREDENTIAL_PARAM_RE = re.compile(r'([?&][lp]=)[^&\s\'"]*')


def _redact_credentials(text: str) -> str:
    return _CREDENTIAL_PARAM_RE.sub(r'\1***', text)


class MadaApiError(Exception):
    pass


@dataclass
class MadaFeedFile:
    name: str
    date: Optional[datetime]
    type: str  # 'full' lub 'partial'

    @property
    def is_full(self) -> bool:
        return self.type == 'full'


class MadaApiClient:
    def __init__(self, base_url=None, login=None, password=None, timeout=120):
        self.base_url = (base_url or settings.MADA_API_BASE_URL).rstrip('/')
        self.login = login or settings.MADA_API_LOGIN
        self.password = password or settings.MADA_API_PASSWORD
        self.timeout = timeout
        if not self.login or not self.password:
            raise MadaApiError('Brak MADA_API_LOGIN / MADA_API_PASSWORD w konfiguracji.')

    def _get(self, extra_params: Optional[dict] = None) -> bytes:
        url = f'{self.base_url}/get_xml.php'
        params = {'l': self.login, 'p': self.password}
        if extra_params:
            params.update(extra_params)
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise MadaApiError(
                f'Błąd połączenia z API Mada: {_redact_credentials(str(exc))}'
            ) from exc
        return response.content

    def list_files(self) -> List[MadaFeedFile]:
        """Manifest dostępnych plików (full/partial)."""
        raw = self._get()
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise MadaApiError(f'Nie udało się sparsować manifestu Mada: {exc}') from exc

        files: List[MadaFeedFile] = []
        for file_el in root.findall('FILE'):
            name = (file_el.findtext('NAME') or '').strip()
            if not name:
                continue
            date_raw = (file_el.findtext('DATE') or '').strip()
            type_raw = (file_el.findtext('TYPE') or '').strip()
            try:
                date = datetime.strptime(date_raw, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                date = None
            files.append(MadaFeedFile(name=name, date=date, type=type_raw))
        return files

    def latest_full_file(self) -> Optional[MadaFeedFile]:
        full_files = [f for f in self.list_files() if f.is_full]
        if not full_files:
            return None
        return max(full_files, key=lambda f: f.date or datetime.min)

    def partial_files_after(self, after_name: Optional[str]) -> List[MadaFeedFile]:
        """Pliki TYPE=partial nowsze niż `after_name`, posortowane rosnąco wg nazwy
        (nazwy mają format YYYY-MM-DD_HHMMSS, więc porównanie leksykalne = chronologiczne)."""
        partials = sorted(
            (f for f in self.list_files() if f.type == 'partial'),
            key=lambda f: f.name,
        )
        if after_name:
            partials = [f for f in partials if f.name > after_name]
        return partials

    def download_products_xml(self, file_name: str) -> bytes:
        """Pobiera plik po nazwie z manifestu (ZIP) i zwraca zawartość products.xml."""
        raw = self._get({'file': file_name})
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                names = zf.namelist()
                inner_name = 'products.xml' if 'products.xml' in names else next(
                    (n for n in names if n.lower().endswith('.xml')), None,
                )
                if inner_name is None:
                    raise MadaApiError(f'Plik {file_name}: ZIP nie zawiera pliku XML')
                return zf.read(inner_name)
        except zipfile.BadZipFile as exc:
            raise MadaApiError(f'Plik {file_name} nie jest poprawnym archiwum ZIP: {exc}') from exc
