"""
Jedna logika kolorów dla wszystkich hurtowni (Matterhorn, Tabu, Mada i kolejne).

MPD jest źródłem prawdy: słownik kolorów głównych (`Colors` z `parent IS NULL`)
utrzymuje się w MPD i import z hurtowni nigdy go nie rozszerza. Hurtownia może
dopisać tylko kolor producenta (`parent` = kolor główny).

Reguły (te same niezależnie od hurtowni):

1. Kolor główny wariantu (`ProductVariants.color`):
   a) `main_color_id` z formularza mapowania, jeśli podany — musi wskazywać
      istniejący kolor główny, inaczej błąd;
   b) w przeciwnym razie kolor główny MPD o tej samej nazwie co kolor hurtowni
      (bez rozróżniania wielkości liter i spacji na brzegach);
   c) brak dopasowania = `ColorResolutionError`. Kolor główny nie powstaje sam.

2. Kolor producenta (`ProductVariants.producer_color`, `ProductImage.producer_color`):
   pusta nazwa = brak. Istniejący kolor o tej nazwie (bez rozróżniania wielkości
   liter) jest używany bez zmian — jego `parent` ustalony w MPD nie jest
   nadpisywany. Nowy powstaje z `parent` = kolor główny z pkt 1.

Nowa hurtownia: wołaj `resolve_variant_colors(...)` i zapisuj zwrócone obiekty.
Nie twórz kolorów bezpośrednio przez `Colors.objects`.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from django.db import IntegrityError, transaction

from .models import Colors

logger = logging.getLogger(__name__)

# colors.name ma max_length=50
_NAME_MAX = 50


class ColorResolutionError(ValueError):
    """Nie da się ustalić koloru głównego MPD dla wariantu."""


@dataclass(frozen=True)
class VariantColors:
    color: Colors
    producer_color: Optional[Colors]


def _clean_name(name: Optional[str]) -> str:
    return (name or '').strip()[:_NAME_MAX]


def _parse_id(value) -> Optional[int]:
    if value is None or value == '':
        return None
    if isinstance(value, Colors):
        return value.pk
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ColorResolutionError(f'Nieprawidłowy main_color_id: {value!r}')


def get_main_color(
    main_color_id=None,
    source_color_name: Optional[str] = None,
    *,
    using: str,
) -> Colors:
    """Zwraca kolor główny MPD wg reguły 1 (patrz docstring modułu)."""
    color_id = _parse_id(main_color_id)
    main_colors = Colors.objects.using(using).filter(parent__isnull=True)

    if color_id is not None:
        color = main_colors.filter(pk=color_id).first()
        if color is None:
            raise ColorResolutionError(
                f'Kolor o id={color_id} nie istnieje w MPD albo nie jest kolorem głównym.'
            )
        return color

    name = _clean_name(source_color_name)
    if name:
        color = main_colors.filter(name__iexact=name).first()
        if color is not None:
            return color
        raise ColorResolutionError(
            f'Kolor hurtowni „{name}” nie ma odpowiednika wśród kolorów głównych MPD. '
            'Wybierz kolor główny w formularzu albo dodaj go do słownika MPD.'
        )

    raise ColorResolutionError(
        'Brak koloru głównego: nie wybrano go w formularzu, a hurtownia nie podała koloru.'
    )


def get_or_create_producer_color(
    producer_color_name: Optional[str],
    main_color: Optional[Colors],
    *,
    using: str,
) -> Optional[Colors]:
    """Zwraca kolor producenta wg reguły 2 (patrz docstring modułu)."""
    name = _clean_name(producer_color_name)
    if not name:
        return None

    qs = Colors.objects.using(using)
    existing = qs.filter(name__iexact=name).first()
    if existing is None:
        try:
            with transaction.atomic(using=using):
                return qs.create(name=name, parent=main_color, hex_code='')
        except IntegrityError:
            # Równoległy import zdążył utworzyć ten sam kolor (colors.name UNIQUE).
            existing = qs.filter(name__iexact=name).first()
            if existing is None:
                raise

    if main_color is not None and existing.parent_id not in (None, main_color.pk):
        logger.warning(
            'Kolor producenta „%s” (id=%s) jest przypięty do koloru %s, a nie %s — '
            'zostawiam przypięcie z MPD.',
            existing.name, existing.pk, existing.parent_id, main_color.pk,
        )
    return existing


def resolve_variant_colors(
    *,
    main_color_id=None,
    producer_color_name: Optional[str] = None,
    source_color_name: Optional[str] = None,
    using: str,
) -> VariantColors:
    """Kolor główny + kolor producenta dla wariantu z dowolnej hurtowni."""
    color = get_main_color(main_color_id, source_color_name, using=using)
    producer_color = get_or_create_producer_color(producer_color_name, color, using=using)
    return VariantColors(color=color, producer_color=producer_color)
