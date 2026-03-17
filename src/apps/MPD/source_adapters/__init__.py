"""
Adaptery źródeł (hurtowni) do dopasowywania wariantów po EAN.

Każda hurtownia implementuje SourceAdapter - umożliwia wyszukiwanie
wariantów po EAN i dopinanie ich do produktów MPD.

Mapowanie produktu (tworzenie w MPD + mapping): kontrakt w product_mapping_contract.py,
wzorzec w docs/mapping/PRODUCT_MAPPING_WZOR.md.
"""
from .base import SourceAdapter, VariantMatch, normalize_ean
from .product_mapping_contract import MpdProductResult, ProductMappingContract
from .registry import get_adapters_for_source, get_all_adapters, register_adapter
from .tabu import TabuAdapter
from .matterhorn import MatterhornAdapter
from .linking import link_variants_from_other_sources, link_all_products_to_new_source

__all__ = [
    'SourceAdapter',
    'VariantMatch',
    'normalize_ean',
    'MpdProductResult',
    'ProductMappingContract',
    'TabuAdapter',
    'MatterhornAdapter',
    'get_adapters_for_source',
    'get_all_adapters',
    'register_adapter',
    'link_variants_from_other_sources',
    'link_all_products_to_new_source',
]
