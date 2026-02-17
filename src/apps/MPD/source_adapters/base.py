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
