"""
Agent Marko - Inteligentny system przetwarzania produktów marki Marko
Wykorzystuje embeddings i AI do automatycznego mapowania produktów
"""

__version__ = "1.0.0"
__author__ = "NC Project Team"
__description__ = "Agent do przetwarzania produktów marki Marko z wykorzystaniem embeddings"

from .marko_agent import MarkoAgent
from .marko_knowledge_base import marko_knowledge
from .marko_category_manager import marko_category_manager
from .marko_embeddings_knowledge import marko_embeddings

__all__ = [
    'MarkoAgent',
    'marko_knowledge',
    'marko_category_manager',
    'marko_embeddings'
]
