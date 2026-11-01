"""Jedno miejsce na interpretację kolumny ``product_variants_retail_price.vat``.

Kolumna jest Decimalem, ale semantycznie to ID wiersza w tabeli ``vat``
(tak zapisuje ją admin i endpoint cen). Starsze ścieżki zapisywały tam stawkę
(np. 23.00), więc przy odczycie obsługujemy oba warianty — zawsze tą samą
regułą, zamiast powielać ją w każdym eksporterze:

1. wartość całkowita, dla której istnieje ``Vat(id=wartość)`` -> to ID,
2. w przeciwnym razie wartość traktujemy jako stawkę (legacy).

Docelowo kolumna powinna stać się FK do ``Vat`` — wtedy wystarczy zmienić
tylko ten moduł.
"""
from __future__ import annotations

import decimal
from decimal import Decimal

from .models import Vat

DB_ALIAS = 'MPD'
DEFAULT_VAT_ID = 1
DEFAULT_RATE = Decimal('23')


def _to_decimal(raw) -> Decimal | None:
    if raw in (None, ''):
        return None
    try:
        return Decimal(str(raw))
    except (decimal.InvalidOperation, TypeError, ValueError):
        return None


def _vat_by_id(val: Decimal) -> Vat | None:
    if val != val.to_integral_value():
        return None
    return Vat.objects.using(DB_ALIAS).filter(id=int(val)).first()


def resolve_vat_id(raw) -> int:
    """Zamienia wejście (ID albo stawkę) na ID wiersza ``vat`` do zapisu."""
    val = _to_decimal(raw)
    if val is not None:
        row = _vat_by_id(val)
        if row:
            return row.id
        row = Vat.objects.using(DB_ALIAS).filter(vat_rate=val).first()
        if row:
            return row.id

    if Vat.objects.using(DB_ALIAS).filter(id=DEFAULT_VAT_ID).exists():
        return DEFAULT_VAT_ID
    first = Vat.objects.using(DB_ALIAS).order_by('id').first()
    return first.id if first else DEFAULT_VAT_ID


def vat_id_for_rate(rate=DEFAULT_RATE) -> int:
    """ID wiersza ``vat`` dla stawki (np. 23) — dla domyślnej stawki przy tworzeniu."""
    row = Vat.objects.using(DB_ALIAS).filter(vat_rate=_to_decimal(rate)).first()
    return row.id if row else resolve_vat_id(None)


def resolve_vat_id_or_default(raw) -> int:
    """Jak ``resolve_vat_id``, ale brak wartości oznacza domyślną stawkę 23%."""
    if _to_decimal(raw) is None:
        return vat_id_for_rate(DEFAULT_RATE)
    return resolve_vat_id(raw)


def resolve_vat(raw) -> tuple[int | None, Decimal | None]:
    """Odczyt zapisanej wartości: zwraca ``(vat_id, stawka)``.

    ``vat_id`` jest ``None``, gdy w kolumnie siedzi stawka (legacy).
    """
    val = _to_decimal(raw)
    if val is None:
        return None, None
    row = _vat_by_id(val)
    if row:
        return row.id, row.vat_rate
    return None, val


def vat_rate(raw) -> Decimal | None:
    """Sama stawka VAT (np. ``Decimal('23.00')``) dla zapisanej wartości."""
    return resolve_vat(raw)[1]
