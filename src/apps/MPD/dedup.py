"""Dedup produktów między hurtowniami (#182).

Ten sam towar z kilku hurtowni ma być w MPD jednym produktem. Zanim import
z hurtowni utworzy nowy ``Products``, sprawdza tutaj, czy któryś z jego kodów
EAN jest już przypięty do wariantu w MPD — jeśli tak, dopina się do tamtego
produktu zamiast tworzyć duplikat.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Optional

from django.db import connections

from .ean import clean_fallback_code, clean_gtin
from .models import ProductVariants, ProductvariantsSources


def _codes(raw_codes: Iterable) -> set[str]:
    codes = set()
    for raw in raw_codes:
        code = clean_gtin(raw) or clean_fallback_code(raw)
        if code:
            codes.add(code)
    return codes


def find_mpd_products_by_eans(raw_codes: Iterable, using: str) -> Counter:
    """Produkty MPD, które mają już warianty z tymi kodami: ``{product_id: trafienia}``.

    Szuka po kanonicznym ``ProductVariants.ean`` oraz (dla wariantów, którym
    EAN jeszcze nie został uzupełniony) po ``ProductvariantsSources.ean``.
    """
    codes = _codes(raw_codes)
    hits = Counter()
    if not codes:
        return hits
    for product_id in (
        ProductVariants.objects.using(using)
        .filter(ean__in=codes)
        .values_list('product_id', flat=True)
    ):
        hits[product_id] += 1
    # Kody w hurtowniach bywają zapisane ze spacjami/małymi literami — porównujemy
    # po normalizacji w Pythonie, ale zawężamy zapytanie do kandydatów.
    candidates = {c for c in codes} | {c.lower() for c in codes}
    for product_id, raw in (
        ProductvariantsSources.objects.using(using)
        .filter(ean__in=candidates, variant__ean__isnull=True)
        .values_list('variant__product_id', 'ean')
    ):
        if (clean_gtin(raw) or clean_fallback_code(raw)) in codes:
            hits[product_id] += 1

    return hits


class AmbiguousMatch(Exception):
    """Kody EAN trafiają w kilka różnych produktów MPD — wymagane ręczne przypisanie."""

    def __init__(self, product_ids):
        self.product_ids = sorted(product_ids)
        super().__init__(f'EAN-y pasują do kilku produktów MPD: {self.product_ids}')


def find_existing_mpd_product(raw_codes: Iterable, using: str) -> Optional[int]:
    """Jedyny produkt MPD z tymi kodami EAN, ``None`` gdy brak.

    Rzuca ``AmbiguousMatch``, gdy kody trafiają w więcej niż jeden produkt
    (np. stare duplikaty albo produkt hurtowni z kilkoma kolorami, które w MPD
    są osobnymi produktami) — wtedy nie zgadujemy, tylko prosimy o wybór.
    """
    hits = find_mpd_products_by_eans(raw_codes, using)
    if not hits:
        return None
    if len(hits) > 1:
        raise AmbiguousMatch(hits.keys())
    return next(iter(hits))


def product_size_category(product_id: int, using: str) -> Optional[str]:
    """Kategoria rozmiarówki produktu MPD (z pierwszego wariantu z rozmiarem)."""
    with connections[using].cursor() as cursor:
        cursor.execute(
            """
            SELECT s.category
            FROM product_variants pv
            JOIN sizes s ON pv.size_id = s.id
            WHERE pv.product_id = %s AND s.category IS NOT NULL
            LIMIT 1
            """,
            [product_id],
        )
        row = cursor.fetchone()
    return row[0] if row and row[0] else None
