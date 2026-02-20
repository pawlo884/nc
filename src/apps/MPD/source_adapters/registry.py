"""
Rejestr adapterów źródeł.
"""
import logging
from typing import Dict, List, Optional

from django.conf import settings

from MPD.models import Sources

logger = logging.getLogger(__name__)

# Rejestr: source_name -> adapter class
_ADAPTER_REGISTRY: Dict[str, type] = {}
# Cache: source_id -> adapter instance
_ADAPTER_CACHE: Dict[int, object] = {}


def register_adapter(source_name: str, adapter_class: type) -> None:
    """
    Rejestruje adapter dla hurtowni (źródła).

    Aby dodać nową hurtownię: zaimplementuj klasę dziedziczącą SourceAdapter
    (get_variants_by_eans, opcjonalnie get_all_variants_for_product i update_source_product_mapped),
    dodaj wpis Sources w MPD (nazwa zawierająca source_name) i wywołaj register_adapter.
    Linkowanie używa wszystkich zarejestrowanych adapterów – bez hardkodu nazw hurtowni.
    """
    _ADAPTER_REGISTRY[source_name] = adapter_class
    logger.debug("Zarejestrowano adapter dla: %s", source_name)


def _get_mpd_db() -> str:
    return 'zzz_MPD' if 'zzz_MPD' in settings.DATABASES else 'MPD'


def get_adapter_for_source(source_id: int) -> Optional[object]:
    """Zwraca instancję adaptera dla source_id."""
    if source_id in _ADAPTER_CACHE:
        return _ADAPTER_CACHE[source_id]

    try:
        source = Sources.objects.using(_get_mpd_db()).get(id=source_id)
        name = (source.name or '').strip()
        for reg_name, adapter_class in _ADAPTER_REGISTRY.items():
            if reg_name.lower() in name.lower() or name.lower() in reg_name.lower():
                adapter = adapter_class(source_id=source_id)
                _ADAPTER_CACHE[source_id] = adapter
                return adapter
    except Sources.DoesNotExist:
        pass
    return None


def get_adapters_for_source(exclude_source_id: Optional[int] = None) -> List[tuple]:
    """
    Zwraca listę (source_id, adapter) dla wszystkich zarejestrowanych źródeł.

    Args:
        exclude_source_id: Pomiń to źródło (np. to z którego właśnie dodano)
    """
    result = []
    for source in Sources.objects.using(_get_mpd_db()).all():
        if exclude_source_id and source.id == exclude_source_id:
            continue
        adapter = get_adapter_for_source(source.id)
        if adapter:
            result.append((source.id, adapter))
    return result


def get_all_adapters() -> List[tuple]:
    """Zwraca wszystkie (source_id, adapter)."""
    return get_adapters_for_source(exclude_source_id=None)


def register_default_adapters() -> None:
    """
    Rejestruje domyślne adaptery. Aby dodać kolejną hurtownię, zaimportuj jej adapter
    i wywołaj register_adapter('Nazwa w Sources', AdapterClass).
    """
    from .tabu import TabuAdapter
    from .matterhorn import MatterhornAdapter
    register_adapter('Tabu API', TabuAdapter)
    register_adapter('Matterhorn', MatterhornAdapter)
