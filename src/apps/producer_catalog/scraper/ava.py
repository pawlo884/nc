"""
Scraper katalogu AVA Lingerie (avalingerie.pl).
Zbiera: produkty, rozmiary, opisy, ceny. Do pilnowania cen zapisujemy historię.
"""
import logging
import re
from decimal import Decimal
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://avalingerie.pl"
LISTING_URLS = [
    "https://avalingerie.pl/pl/7-biustonosze",
    "https://avalingerie.pl/pl/11-figi",
    "https://avalingerie.pl/pl/258-majtki-damskie",
    "https://avalingerie.pl/pl/293-stroje-kapielowe",
    "https://avalingerie.pl/pl/4-nowosci",
    "https://avalingerie.pl/pl/5-promocje",
]
# Dodatkowe strony kategorii można dopisać
PRODUCT_LINK_PATTERN = re.compile(r"^/pl/[\w\-]+/\d+-\d+-.+\.html$", re.I)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
    })
    return s


def _normalize_product_url(href: str) -> Optional[str]:
    if not href or "javascript:" in href or "#" in href:
        return None
    if href.startswith("http"):
        parsed = urlparse(href)
        if "avalingerie.pl" not in parsed.netloc:
            return None
        path = parsed.path
    else:
        path = href.split("?")[0]
    if not PRODUCT_LINK_PATTERN.match(path):
        return None
    return urljoin(BASE_URL, path)


def collect_product_urls(
    session: Optional[requests.Session] = None,
    listing_urls: Optional[List[str]] = None,
) -> Set[str]:
    """Zbiera URL-e produktów z listingów (kategorie). listing_urls=None = wszystkie kategorie."""
    session = session or _session()
    urls_to_scan = listing_urls if listing_urls is not None else LISTING_URLS
    seen: Set[str] = set()
    for url in urls_to_scan:
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                full = _normalize_product_url(a["href"])
                if full:
                    seen.add(full)
        except Exception as e:
            logger.warning("Błąd pobierania listy %s: %s", url, e)
    return seen


def _parse_price_pln(text: str) -> Optional[Decimal]:
    """Wyciąga cenę w PLN z tekstu typu '176,99 zł (brutto)'."""
    if not text:
        return None
    # 176,99 lub 176.99
    m = re.search(r"(\d+)[,.](\d{2})\s*zł", text, re.I)
    if m:
        return Decimal(f"{m.group(1)}.{m.group(2)}")
    return None


def scrape_product_page(
    url: str,
    session: Optional[requests.Session] = None,
) -> Optional[Dict]:
    """
    Pobiera stronę produktu i parsuje: nazwa, opis, cena, lista rozmiarów.
    Zwraca dict: name, description, image_url, price_brutto, sizes (lista str), raw_html (opcjonalnie).
    """
    session = session or _session()
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        logger.warning("Błąd GET %s: %s", url, e)
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # Nazwa – h1
    name = ""
    h1 = soup.find("h1")
    if h1:
        name = (h1.get_text() or "").strip()

    # Cena – szukamy bloku z "zł (brutto)"
    price_brutto = None
    for el in soup.find_all(string=re.compile(r"zł\s*\(brutto\)", re.I)):
        price_brutto = _parse_price_pln(el)
        if price_brutto is not None:
            break
    if price_brutto is None:
        for el in soup.find_all(["span", "div", "p"]):
            t = (el.get_text() or "")
            if "brutto" in t.lower() and "zł" in t:
                price_brutto = _parse_price_pln(t)
                if price_brutto is not None:
                    break

    # Opis – często w #product-description lub .product-description / Sekcja "Opis"
    description = ""
    for id_ in ("product-description", "description"):
        block = soup.find(id=id_)
        if block:
            description = (block.get_text() or "").strip()[:10000]
            break
    if not description:
        for el in soup.find_all(["div", "section"], class_=re.compile(r"description|opis", re.I)):
            description = (el.get_text() or "").strip()[:10000]
            if len(description) > 50:
                break

    # Obrazek – główny zdjęcie produktu
    image_url = ""
    img = soup.find("img", {"id": "bigpic"}) or soup.find("img", class_=re.compile(r"product.*img|main.*img", re.I))
    if img and img.get("src"):
        image_url = urljoin(url, img["src"])
    if not image_url:
        for img in soup.find_all("img", src=True):
            if "product" in img["src"].lower() or "img/p" in img["src"]:
                image_url = urljoin(url, img["src"])
                break

    # Rozmiary – PrestaShop często: #group_3 li, .attribute_list, lub select#group_3 option
    sizes: List[str] = []
    size_select = soup.find("select", {"id": "group_3"}) or soup.find("select", class_=re.compile(r"attribute|size", re.I))
    if size_select:
        for opt in size_select.find_all("option", value=True):
            if opt.get("value"):
                label = (opt.get_text() or "").strip()
                if label and label != "Wybierz rozmiar":
                    sizes.append(label)
    if not sizes:
        # Lista li w bloku "Wybierz rozmiar" / tabela rozmiarów
        for label in soup.find_all(string=re.compile(r"^\s*(65|70|75|80|85|90|95|100|105)[A-Z]\s*$")):
            s = (label.strip() or "").strip()
            if s and s not in sizes:
                sizes.append(s)
        for li in soup.find_all("li"):
            t = (li.get_text() or "").strip()
            if re.match(r"^(65|70|75|80|85|90|95|100|105)[A-Z]$", t) and t not in sizes:
                sizes.append(t)
    sizes = sorted(set(sizes))

    # ID z URL (np. 2834-44763 -> 2834 lub pierwszy numer)
    external_id = None
    m = re.search(r"/(\d+)-\d+-", url)
    if m:
        external_id = m.group(1)

    return {
        "url": url,
        "external_id": external_id,
        "name": name or "Bez nazwy",
        "description": description,
        "image_url": image_url,
        "price_brutto": price_brutto,
        "sizes": sizes,
        "currency": "PLN",
    }
