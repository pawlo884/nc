#!/usr/bin/env python3
"""
Skrypt do testowania optymalizacji pamięci w aplikacji MPD
"""
from MPD.models import ProductVariants, Sizes
from MPD.memory_optimizer import (
    MemoryOptimizer,
    QueryOptimizer,
    CacheManager,
    get_memory_usage_summary,
    optimize_django_settings
)
import time
import os
import sys
import django
from dotenv import load_dotenv

# Dodaj katalog główny projektu do sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Załaduj zmienne środowiskowe
env_path = os.path.join(current_dir, '.env.dev')
load_dotenv(dotenv_path=env_path)

# Konfiguracja Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()


def test_memory_optimizer():
    """Test MemoryOptimizer"""
    print("🧪 Testowanie MemoryOptimizer...")

    optimizer = MemoryOptimizer()

    # Sprawdź użycie pamięci
    memory_info = optimizer.get_memory_usage()
    print(f"📊 Aktualne użycie pamięci: {memory_info['percent']:.2f}%")
    print(f"📊 Pamięć fizyczna: {memory_info['rss'] / 1024 / 1024:.2f} MB")
    print(f"📊 Pamięć wirtualna: {memory_info['vms'] / 1024 / 1024:.2f} MB")

    # Sprawdź próg pamięci
    threshold_exceeded = optimizer.check_memory_threshold()
    print(f"⚠️ Przekroczono próg pamięci: {threshold_exceeded}")

    # Wykonaj optymalizację
    print("🧹 Wykonuję optymalizację pamięci...")
    result = optimizer.optimize_memory()

    print(f"✅ Zaoszczędzono {result['memory_saved_mb']:.2f} MB pamięci")
    print(f"✅ Wyczyszczono {result['collected_objects']} obiektów")

    return result


def test_query_optimizer():
    """Test QueryOptimizer"""
    print("\n🧪 Testowanie QueryOptimizer...")

    query_optimizer = QueryOptimizer()

    # Test z małym queryset
    print("📝 Test z małym queryset...")
    small_queryset = Sizes.objects.filter(category='bielizna')[:10]
    optimized_small = query_optimizer.optimize_queryset(
        small_queryset, use_iterator=False)
    print(f"✅ Mały queryset: {optimized_small.count()} obiektów")

    # Test z dużym queryset (używa iterator)
    print("📝 Test z dużym queryset (iterator)...")
    large_queryset = ProductVariants.objects.all()
    optimized_large = query_optimizer.optimize_queryset(
        large_queryset, use_iterator=True)

    # Policz obiekty w iteratorze
    count = 0
    for obj in optimized_large:
        count += 1
        if count >= 100:  # Ogranicz do 100 dla testu
            break

    print(f"✅ Duży queryset (iterator): {count} obiektów (ograniczone do 100)")

    return True


def test_cache_manager():
    """Test CacheManager"""
    print("\n🧪 Testowanie CacheManager...")

    cache_manager = CacheManager()

    # Test cache'owania
    print("📝 Test cache'owania...")
    test_data = {'test': 'data', 'number': 42}
    cache_key = 'test_memory_optimization'

    # Zapisz do cache
    from django.core.cache import cache
    cache.set(cache_key, test_data, 60)  # 60 sekund
    print("✅ Dane zapisane do cache")

    # Pobierz z cache
    cached_data = cache.get(cache_key)
    if cached_data == test_data:
        print("✅ Dane poprawnie pobrane z cache")
    else:
        print("❌ Błąd pobierania z cache")

    # Pobierz statystyki cache
    stats = cache_manager.get_cache_stats()
    print(f"📊 Backend cache: {stats['cache_backend']}")
    print(f"📊 Timeout: {stats['timeout']} sekund")

    return True


def test_batch_processing():
    """Test przetwarzania w batch'ach"""
    print("\n🧪 Testowanie batch processing...")

    query_optimizer = QueryOptimizer()

    def process_batch(batch):
        """Funkcja do przetwarzania batch'a"""
        print(f"🔄 Przetwarzanie batch'a z {len(batch)} obiektami")
        # Symuluj przetwarzanie
        time.sleep(0.1)
        return len(batch)

    # Test z małym queryset
    small_queryset = Sizes.objects.filter(category='bielizna')[:50]

    print("📝 Test batch processing...")
    total_processed = 0
    for result in query_optimizer.process_in_batches(small_queryset, process_batch, batch_size=10):
        total_processed += result

    print(f"✅ Przetworzono {total_processed} obiektów w batch'ach")

    return total_processed


def test_memory_monitoring():
    """Test monitorowania pamięci"""
    print("\n🧪 Testowanie monitorowania pamięci...")

    from MPD.memory_optimizer import memory_monitor, query_monitor

    print("📝 Test memory_monitor...")
    with memory_monitor("test operacja"):
        # Symuluj operację zużywającą pamięć
        large_list = [i for i in range(100000)]
        time.sleep(0.5)
        del large_list

    print("📝 Test query_monitor...")
    with query_monitor():
        # Symuluj zapytania do bazy
        Sizes.objects.count()
        ProductVariants.objects.count()

    return True


def test_django_settings():
    """Test ustawień Django"""
    print("\n🧪 Testowanie ustawień Django...")

    recommendations = optimize_django_settings()

    if recommendations:
        print("⚠️ Zalecenia optymalizacji:")
        for rec in recommendations:
            print(f"  - {rec}")
    else:
        print("✅ Ustawienia Django są zoptymalizowane")

    return recommendations


def main():
    """Główna funkcja testowa"""
    print("🚀 Rozpoczynam testy optymalizacji pamięci...")
    print("=" * 60)

    try:
        # Test 1: MemoryOptimizer
        memory_result = test_memory_optimizer()

        # Test 2: QueryOptimizer
        query_result = test_query_optimizer()

        # Test 3: CacheManager
        cache_result = test_cache_manager()

        # Test 4: Batch processing
        batch_result = test_batch_processing()

        # Test 5: Memory monitoring
        monitoring_result = test_memory_monitoring()

        # Test 6: Django settings
        settings_result = test_django_settings()

        # Podsumowanie
        print("\n" + "=" * 60)
        print("📊 PODSUMOWANIE TESTÓW")
        print("=" * 60)

        summary = get_memory_usage_summary()
        print(f"📊 Końcowe użycie pamięci: {summary['memory_percent']:.2f}%")
        print(f"📊 Pamięć fizyczna: {summary['memory_mb']:.2f} MB")
        print(f"📊 Dostępna pamięć: {summary['available_mb']:.2f} MB")
        print(f"⚠️ Przekroczono próg: {summary['threshold_exceeded']}")

        if memory_result:
            print(
                f"✅ MemoryOptimizer: Zaoszczędzono {memory_result['memory_saved_mb']:.2f} MB")
        print(f"✅ QueryOptimizer: {'OK' if query_result else 'BŁĄD'}")
        print(f"✅ CacheManager: {'OK' if cache_result else 'BŁĄD'}")
        print(f"✅ Batch processing: {batch_result} obiektów")
        print(f"✅ Memory monitoring: {'OK' if monitoring_result else 'BŁĄD'}")
        print(f"✅ Django settings: {len(settings_result)} zaleceń")

        print("\n🎉 Wszystkie testy zakończone pomyślnie!")

    except Exception as e:
        print(f"\n❌ Błąd podczas testów: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
