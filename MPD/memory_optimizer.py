"""
Narzędzia do optymalizacji pamięci dla aplikacji MPD
"""
import gc
import psutil
import logging
from django.conf import settings
from django.core.cache import cache
from django.db import connection, connections
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MemoryOptimizer:
    """Klasa do zarządzania optymalizacją pamięci"""

    def __init__(self):
        self.batch_size = getattr(
            settings, 'DATABASE_OPTIMIZATION', {}).get('BATCH_SIZE', 1000)
        self.max_memory_usage = getattr(
            settings, 'MEMORY_OPTIMIZATION', {}).get('MAX_MEMORY_USAGE', 0.8)

    def get_memory_usage(self):
        """Pobiera aktualne użycie pamięci"""
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        return {
            'rss': memory_info.rss,  # Resident Set Size (fizyczna pamięć)
            'vms': memory_info.vms,  # Virtual Memory Size
            'percent': memory_percent,
            'available': psutil.virtual_memory().available
        }

    def check_memory_threshold(self):
        """Sprawdza czy użycie pamięci przekracza próg"""
        memory_usage = self.get_memory_usage()
        return memory_usage['percent'] > (self.max_memory_usage * 100)

    def force_garbage_collection(self):
        """Wymusza czyszczenie pamięci"""
        collected = gc.collect()
        logger.info(f"Wyczyszczono {collected} obiektów z pamięci")
        return collected

    def clear_database_connections(self):
        """Czyści nieaktywne połączenia z bazą danych"""
        for db_name in connections.databases:
            connection = connections[db_name]
            if connection.connection is not None:
                connection.close_if_unusable_or_obsolete()
        logger.info("Wyczyszczono połączenia z bazą danych")

    def clear_cache(self):
        """Czyści cache Redis"""
        cache.clear()
        logger.info("Wyczyszczono cache Redis")

    def optimize_memory(self):
        """Wykonuje pełną optymalizację pamięci"""
        logger.info("Rozpoczynam optymalizację pamięci...")

        # Sprawdź użycie pamięci przed optymalizacją
        before_memory = self.get_memory_usage()
        logger.info(
            f"Użycie pamięci przed optymalizacją: {before_memory['percent']:.2f}%")

        # Wymuś garbage collection
        collected = self.force_garbage_collection()

        # Wyczyść połączenia z bazą danych
        self.clear_database_connections()

        # Sprawdź użycie pamięci po optymalizacji
        after_memory = self.get_memory_usage()
        logger.info(
            f"Użycie pamięci po optymalizacji: {after_memory['percent']:.2f}%")

        # Oblicz oszczędności
        memory_saved = before_memory['rss'] - after_memory['rss']
        logger.info(
            f"Zaoszczędzono {memory_saved / 1024 / 1024:.2f} MB pamięci")

        return {
            'before': before_memory,
            'after': after_memory,
            'collected_objects': collected,
            'memory_saved_mb': memory_saved / 1024 / 1024
        }


class QueryOptimizer:
    """Klasa do optymalizacji zapytań do bazy danych"""

    def __init__(self):
        self.batch_size = getattr(
            settings, 'DATABASE_OPTIMIZATION', {}).get('BATCH_SIZE', 1000)
        self.max_query_results = getattr(
            settings, 'DATABASE_OPTIMIZATION', {}).get('MAX_QUERY_RESULTS', 10000)

    def optimize_queryset(self, queryset, use_iterator=True, batch_size=None):
        """Optymalizuje queryset dla lepszego zarządzania pamięcią"""
        if batch_size is None:
            batch_size = self.batch_size

        # Dodaj select_related i prefetch_related jeśli nie ma
        if not hasattr(queryset, '_prefetch_related_lookups'):
            # Automatycznie dodaj select_related dla ForeignKey
            select_related_fields = []
            for field in queryset.model._meta.fields:
                if field.is_relation and field.many_to_one:
                    select_related_fields.append(field.name)

            if select_related_fields:
                queryset = queryset.select_related(*select_related_fields)

        # Użyj iterator() dla dużych querysetów
        if use_iterator and queryset.count() > batch_size:
            return queryset.iterator(chunk_size=batch_size)

        return queryset

    def process_in_batches(self, queryset, process_func, batch_size=None):
        """Przetwarza queryset w batch'ach"""
        if batch_size is None:
            batch_size = self.batch_size

        total_count = queryset.count()
        processed_count = 0

        logger.info(
            f"Rozpoczynam przetwarzanie {total_count} obiektów w batch'ach po {batch_size}")

        for offset in range(0, total_count, batch_size):
            batch = list(queryset[offset:offset + batch_size])
            batch_count = len(batch)

            logger.info(
                f"Przetwarzanie batch {offset // batch_size + 1}: {batch_count} obiektów")

            # Przetwórz batch
            result = process_func(batch)

            processed_count += batch_count
            logger.info(
                f"Przetworzono {processed_count}/{total_count} obiektów")

            # Czyszczenie pamięci po każdym batch'u
            del batch
            gc.collect()

            yield result

        logger.info(f"Zakończono przetwarzanie {processed_count} obiektów")


class CacheManager:
    """Klasa do zarządzania cache"""

    def __init__(self):
        self.default_timeout = getattr(settings, 'CACHES', {}).get(
            'default', {}).get('TIMEOUT', 300)

    def cache_queryset(self, queryset, cache_key, timeout=None):
        """Cache'uje wyniki queryset"""
        if timeout is None:
            timeout = self.default_timeout

        # Sprawdź czy dane są już w cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Pobrano dane z cache: {cache_key}")
            return cached_data

        # Pobierz dane z bazy i zapisz do cache
        data = list(queryset)
        cache.set(cache_key, data, timeout)
        logger.info(
            f"Zapisano dane do cache: {cache_key} ({len(data)} obiektów)")

        return data

    def invalidate_cache_pattern(self, pattern):
        """Inwaliduje cache na podstawie wzorca"""
        # To jest uproszczona implementacja - w produkcji użyj Redis SCAN
        logger.info(f"Inwaliduję cache z wzorcem: {pattern}")
        # cache.delete_pattern(pattern)  # Wymaga django-redis

    def get_cache_stats(self):
        """Pobiera statystyki cache"""
        # To jest uproszczona implementacja
        return {
            'cache_backend': settings.CACHES.get('default', {}).get('BACKEND', 'unknown'),
            'timeout': self.default_timeout
        }


@contextmanager
def memory_monitor(operation_name="operacja"):
    """Context manager do monitorowania użycia pamięci"""
    optimizer = MemoryOptimizer()

    before_memory = optimizer.get_memory_usage()
    logger.info(
        f"Rozpoczynam {operation_name} - użycie pamięci: {before_memory['percent']:.2f}%")

    try:
        yield optimizer
    finally:
        after_memory = optimizer.get_memory_usage()
        memory_diff = after_memory['rss'] - before_memory['rss']
        logger.info(
            f"Zakończono {operation_name} - użycie pamięci: {after_memory['percent']:.2f}% (różnica: {memory_diff / 1024 / 1024:.2f} MB)")


@contextmanager
def query_monitor():
    """Context manager do monitorowania zapytań do bazy danych"""
    initial_queries = len(connection.queries) if hasattr(
        connection, 'queries') else 0

    try:
        yield
    finally:
        final_queries = len(connection.queries) if hasattr(
            connection, 'queries') else 0
        query_count = final_queries - initial_queries
        logger.info(f"Wykonano {query_count} zapytań do bazy danych")


# Funkcje pomocnicze
def optimize_django_settings():
    """Optymalizuje ustawienia Django dla lepszego zarządzania pamięcią"""
    recommendations = []

    # Sprawdź ustawienia debug
    if getattr(settings, 'DEBUG', False):
        recommendations.append("Wyłącz DEBUG w produkcji")

    # Sprawdź ustawienia cache
    if not getattr(settings, 'CACHES', {}):
        recommendations.append("Skonfiguruj cache Redis")

    # Sprawdź ustawienia bazy danych
    for db_name, db_config in getattr(settings, 'DATABASES', {}).items():
        if 'CONN_MAX_AGE' not in db_config:
            recommendations.append(f"Dodaj CONN_MAX_AGE dla bazy {db_name}")

    return recommendations


def get_memory_usage_summary():
    """Pobiera podsumowanie użycia pamięci"""
    optimizer = MemoryOptimizer()
    memory_info = optimizer.get_memory_usage()

    return {
        'memory_percent': memory_info['percent'],
        'memory_mb': memory_info['rss'] / 1024 / 1024,
        'virtual_memory_mb': memory_info['vms'] / 1024 / 1024,
        'available_mb': memory_info['available'] / 1024 / 1024,
        'threshold_exceeded': optimizer.check_memory_threshold()
    }
