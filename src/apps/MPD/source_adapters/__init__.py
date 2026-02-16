"""
Adaptery źródeł (hurtowni) do dopasowywania wariantów po EAN.

Każda hurtownia implementuje SourceAdapter - umożliwia wyszukiwanie
wariantów po EAN i dopinanie ich do produktów MPD.
"""
from .base import SourceAdapter, VariantMatch
from .registry import get_adapters_for_source, get_all_adapters, register_adapter
from .tabu import TabuAdapter
from .matterhorn import MatterhornAdapter
from .linking import link_variants_from_other_sources, link_all_products_to_new_source

__all__ = [
    'SourceAdapter',
    'VariantMatch',
    'TabuAdapter',
    'MatterhornAdapter',
    'get_adapters_for_source',
    'get_all_adapters',
    'register_adapter',
    'link_variants_from_other_sources',
    'link_all_products_to_new_source',
]
