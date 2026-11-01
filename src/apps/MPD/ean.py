"""Kanoniczny EAN/GTIN wariantu MPD (``ProductVariants.ean``).

Hurtownie trzymają kody w ``ProductvariantsSources`` (wariant × źródło), więc
jeden wariant może mieć kilka różnych EAN-ów. Eksportery (IOF, PrestaShop) i
deduplikacja produktów (#182) potrzebują jednego kodu na wariant — tu jest
jedna, deterministyczna reguła jego wyboru:

1. źródła w kolejności rosnącego ``source_id`` (pierwsza hurtownia wygrywa),
2. w obrębie źródła pola ``ean``, ``gtin13``, ``gtin14``, ``gtin12``, ``gtin8``,
3. pierwszy kod, który po oczyszczeniu jest poprawnym GTIN (same cyfry,
   długość 8/12/13/14),
4. awaryjnie, gdy żadne źródło nie ma GTIN-u: pole ``ean`` jako kod
   alfanumeryczny do 14 znaków (np. ``00011T180291`` z hurtowni Gatty) —
   takie kody też trzeba umieć deduplikować.

Kanoniczny EAN ustawiany jest tylko wtedy, gdy wariant jeszcze go nie ma —
ręczna korekta w adminie nie zostanie nadpisana przez kolejny import.
Reguła działa na źródłach obecnych w chwili wypełniania: migracja 0026 i
``mpd_ean --backfill`` widzą wszystkie hurtownie, a przy imporcie (sygnał)
EAN bierze się z pierwszej hurtowni, która przyniosła poprawny kod.
"""
from __future__ import annotations

from typing import Iterable, Optional

GTIN_LENGTHS = frozenset({8, 12, 13, 14})
SOURCE_CODE_FIELDS = ('ean', 'gtin13', 'gtin14', 'gtin12', 'gtin8')
MAX_CODE_LENGTH = 14  # = ProductVariants.ean.max_length


def clean_gtin(raw) -> Optional[str]:
    """Zwraca kod GTIN (same cyfry) albo ``None``, jeśli to nie jest GTIN.

    Usuwa spacje i myślniki; ``'5 901234 123457'`` -> ``'5901234123457'``.
    Sumy kontrolnej nie sprawdzamy: hurtownie bywają niedokładne, a odrzucenie
    kodu oznaczałoby brak EAN-u w ogóle.
    """
    if raw is None:
        return None
    value = str(raw).strip().replace(' ', '').replace('-', '')
    if value.isdigit() and len(value) in GTIN_LENGTHS:
        return value
    return None


def clean_fallback_code(raw) -> Optional[str]:
    """Kod spoza GTIN (litery + cyfry, min. jedna cyfra) do porównań, albo ``None``."""
    if raw is None:
        return None
    value = str(raw).strip().replace(' ', '').replace('-', '').upper()
    if (value and value.isalnum() and value.isascii()
            and len(value) <= MAX_CODE_LENGTH
            and any(ch.isdigit() for ch in value)):
        return value
    return None


def pick_canonical_ean(source_rows: Iterable) -> Optional[str]:
    """Wybiera kanoniczny EAN z wierszy ``ProductvariantsSources``.

    Działa na dowolnych obiektach z atrybutami ``source_id`` i polami kodów
    (także na modelach historycznych w migracjach).
    """
    rows = sorted(
        source_rows,
        key=lambda r: (getattr(r, 'source_id', None) is None,
                       getattr(r, 'source_id', None) or 0,
                       getattr(r, 'pk', 0) or 0),
    )
    for row in rows:
        for field in SOURCE_CODE_FIELDS:
            code = clean_gtin(getattr(row, field, None))
            if code:
                return code
    for row in rows:
        code = clean_fallback_code(getattr(row, 'ean', None))
        if code:
            return code
    return None


def ensure_variant_ean(variant_id: int, using: str) -> Optional[str]:
    """Ustawia ``ProductVariants.ean`` z hurtowni, jeśli jest pusty.

    Zwraca EAN wariantu po operacji (istniejący albo nowo ustawiony).
    """
    from django.db.models import Q

    from .models import ProductVariants, ProductvariantsSources

    current = (
        ProductVariants.objects.using(using)
        .filter(variant_id=variant_id)
        .values_list('ean', flat=True)
        .first()
    )
    if current:
        return current
    ean = pick_canonical_ean(
        ProductvariantsSources.objects.using(using).filter(variant_id=variant_id)
    )
    if ean:
        # update(), nie save(): bez sygnałów i bez ruszania innych pól.
        ProductVariants.objects.using(using).filter(
            Q(ean__isnull=True) | Q(ean=''), variant_id=variant_id,
        ).update(ean=ean)
    return ean
