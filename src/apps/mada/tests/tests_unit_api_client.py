"""
`mada.api_client.MadaApiClient` — parsowanie manifestu, wybór plików full/partial,
rozpakowanie ZIP, redakcja danych logowania w komunikatach błędów.
"""
from __future__ import annotations

import io
import zipfile

import pytest
import responses

from mada.api_client import MadaApiClient, MadaApiError

from . import mock_mada

pytestmark = pytest.mark.unit


@pytest.fixture
def client(mada_api):
    return MadaApiClient()


@pytest.fixture
def rsps():
    with responses.RequestsMock() as r:
        yield r


def test_list_files_parsuje_manifest(client, rsps):
    mock_mada.register_manifest(rsps, [
        {"name": "2026-01-15-full", "date": "2026-01-15 00:01:00", "type": "full"},
        {"name": "2026-01-15_120500", "date": "2026-01-15 12:05:00", "type": "partial"},
        {"name": "bez-daty", "date": "", "type": "partial"},
    ])
    files = client.list_files()

    assert [f.name for f in files] == ["2026-01-15-full", "2026-01-15_120500", "bez-daty"]
    assert files[0].is_full
    assert files[2].date is None  # niepoprawna data → None, wpis zostaje


def test_latest_full_file_bierze_najnowszy(client, rsps):
    mock_mada.register_manifest(rsps, [
        {"name": "old-full", "date": "2026-01-10 00:01:00", "type": "full"},
        {"name": "new-full", "date": "2026-01-15 00:01:00", "type": "full"},
        {"name": "p1", "date": "2026-01-16 00:01:00", "type": "partial"},
    ])
    assert client.latest_full_file().name == "new-full"


def test_latest_full_file_none_gdy_brak_full(client, rsps):
    mock_mada.register_manifest(rsps, [{"name": "p1", "date": "2026-01-16 00:01:00", "type": "partial"}])
    assert client.latest_full_file() is None


def test_partial_files_after_filtruje_i_sortuje(client, rsps):
    mock_mada.register_manifest(rsps, [
        {"name": "2026-01-15_090000", "date": "2026-01-15 09:00:00", "type": "partial"},
        {"name": "2026-01-15_120000", "date": "2026-01-15 12:00:00", "type": "partial"},
        {"name": "2026-01-15_100000", "date": "2026-01-15 10:00:00", "type": "partial"},
        {"name": "2026-01-15-full", "date": "2026-01-15 00:01:00", "type": "full"},
    ])
    got = client.partial_files_after("2026-01-15_090000")
    assert [f.name for f in got] == ["2026-01-15_100000", "2026-01-15_120000"]


def test_partial_files_after_bez_kursora_zwraca_wszystkie(client, rsps):
    mock_mada.register_manifest(rsps, [
        {"name": "b", "date": "2026-01-15 12:00:00", "type": "partial"},
        {"name": "a", "date": "2026-01-15 09:00:00", "type": "partial"},
    ])
    assert [f.name for f in client.partial_files_after(None)] == ["a", "b"]


def test_download_products_xml_rozpakowuje_zip(client, rsps):
    mock_mada.register_file(rsps, "2026-01-15-full", {"110": "Gatta"},
                            [mock_mada.simple_product(161)])
    xml = client.download_products_xml("2026-01-15-full")
    assert b"<ID>161</ID>" in xml


def test_download_products_xml_zip_bez_xml(client, rsps):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "nope")
    rsps.add(responses.GET, mock_mada.MANIFEST_URL, body=buf.getvalue(),
             content_type="application/zip")

    with pytest.raises(MadaApiError, match="nie zawiera pliku XML"):
        client.download_products_xml("x")


def test_download_products_xml_zly_zip(client, rsps):
    rsps.add(responses.GET, mock_mada.MANIFEST_URL, body=b"to nie jest zip")
    with pytest.raises(MadaApiError, match="ZIP"):
        client.download_products_xml("x")


def test_blad_polaczenia_redaguje_haslo(client, rsps):
    rsps.add(responses.GET, mock_mada.MANIFEST_URL,
             body=responses.ConnectionError("failed for url: https://mada.test/get_xml.php?l=test-login&p=test-pass"))
    with pytest.raises(MadaApiError) as exc:
        client.list_files()
    msg = str(exc.value)
    assert "test-pass" not in msg and "test-login" not in msg
    assert "p=***" in msg


def test_brak_danych_logowania_blad_od_razu(mada_api):
    mada_api.MADA_API_PASSWORD = ""
    with pytest.raises(MadaApiError, match="MADA_API_LOGIN / MADA_API_PASSWORD"):
        MadaApiClient()
