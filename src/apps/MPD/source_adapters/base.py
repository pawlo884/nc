"""
Bazowa klasa adaptera źródła (hurtowni).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


def normalize_ean(ean: str) -> str:
    """Normalizuje EAN do porównań (strip + lowercase)."""
    e = (ean or '').strip()
    return e.lower() if e else ''


@dataclass
class VariantMatch:
    """Dopasowany wariant z hurtowni do dodania do MPD."""
    ean: str
    variant_uid: str  # ID w systemie hurtowni (variant_uid, api_id, etc.)
    stock: int
    price: Decimal
    currency: str = 'PLN'
    size: Optional[str] = None
    color: Optional[str] = None
    source_product_id: Optional[int] = None  # ID produktu w hurtowni (do ustawienia mapped_product_uid)
    producer_code: Optional[str] = None  # Kod producenta (symbol, variant_uid itp.) → ProductvariantsSources.producer_code (per hurtownia)


class SourceAdapter(ABC):
    """Adapter do pobierania wariantów z hurtowni."""

    source_name: str  # Nazwa do dopasowania w Sources (np. 'Tabu API', 'Matterhorn')

    def __init__(self, source_id: int):
        self.source_id = source_id

    @abstractmethod
    def get_variants_by_eans(
        self,
        ean_list: List[str],
        mpd_product_id: Optional[int] = None,
    ) -> List[VariantMatch]:
        """
        Zwraca warianty z hurtowni o podanych EAN.

        Args:
            ean_list: Lista EAN do wyszukania
            mpd_product_id: Opcjonalnie - tylko warianty z produktów zmapowanych do tego MPD

        Returns:
            Lista VariantMatch
        """
        raise NotImplementedError

    def get_all_variants_for_product(
        self,
        source_product_id: int,
    ) -> List[VariantMatch]:
        """
        Zwraca wszystkie warianty produktu w hurtowni (do dopinania „pozostałych” wariantów).

        Args:
            source_product_id: ID produktu w systemie hurtowni

        Returns:
            Lista VariantMatch (ean może być pusty)
        """
        return []

    def update_source_product_mapped(
        self,
        source_product_id: int,
        mpd_product_id: int,
    ) -> None:
        """
        Ustawia mapped_product_uid w hurtowni źródłowej (po zlinkowaniu wariantów do MPD).
        Adapter może nadpisać; domyślnie brak akcji (dla hurtowni bez takiego pola).
        """
        pass

    def update_source_variant_mapped(
        self,
        source_product_id: int,
        source_variant_uid: Optional[str],
        mpd_variant_id: int,
    ) -> None:
        """
        Ustawia mapped_variant_uid w hurtowni źródłowej (np. productvariant w Matterhorn).
        Wywoływane po dopięciu wariantu do MPD (ProductvariantsSources).
        source_variant_uid: identyfikator wariantu w źródle (variant_uid w MH, api_id w Tabu jako str).
        """
        pass
