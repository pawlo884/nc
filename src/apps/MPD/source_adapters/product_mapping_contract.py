"""
Kontrakt mapowania produktu hurtownia → MPD.

Wzorzec (kroki, pola, checklista) opisany w: docs/mapping/PRODUCT_MAPPING_WZOR.md.
Przy każdej nowej hurtowni implementuj ten kontrakt zamiast dorabiać logikę od zera.

Referencje: matterhorn1 (saga.py, saga_variants.py), tabu (services.py).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# Typ wyniku tworzenia produktu MPD z hurtowni (wspólny dla wszystkich adapterów)
MpdProductResult = Dict[str, Any]  # success: bool, mpd_product_id: int|None, error_message: str|None


class ProductMappingContract(ABC):
    """
    Kontrakt dla mapowania produktu z hurtowni do MPD.

    Każda hurtownia z pełnym flow „utwórz produkt w MPD + zapisz mapping”
    powinna realizować ten kontrakt (funkcja lub metoda o tej sygnaturze).
    """

    # Nazwa źródła w MPD (Sources.name lub fragment do dopasowania)
    source_name: str = ""

    @abstractmethod
    def create_mpd_product_from_source(
        self,
        source_product_id: int,
        form_data: Optional[Dict[str, Any]] = None,
    ) -> MpdProductResult:
        """
        Tworzy produkt w MPD na podstawie produktu z hurtowni i zapisuje mapping.

        Kroki (zgodnie z docs/mapping/PRODUCT_MAPPING_WZOR.md):
        1. Utworzenie produktu w MPD (Products, Brands, Series).
        2. Zapis w hurtowni: mapped_product_uid = mpd_product_id.
        3. Opcjonalnie: ścieżki, atrybuty, skład.
        4. Utworzenie wariantów w MPD (ProductVariants, ProductvariantsSources, StockAndPrices).
        5. Zapis w hurtowni: mapped_variant_uid na wariantach.
        6. Wywołanie tasku linkowania po EAN.
        7. Opcjonalnie: zdjęcia.

        Args:
            source_product_id: ID produktu w systemie hurtowni (PK).
            form_data: Opcjonalne nadpisania z formularza (np. mpd_name, mpd_brand,
                       main_color_id, producer_color_name, mpd_paths, mpd_attributes).

        Returns:
            Dict z kluczami:
            - success (bool)
            - mpd_product_id (int | None)
            - error_message (str | None)
        """
        raise NotImplementedError
