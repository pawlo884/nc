"""
Bazowa klasa adaptera źródła (hurtowni).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


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
