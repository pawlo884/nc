# Przewodnik optymalizacji pamięci dla aplikacji MPD

## Wprowadzenie

Ten przewodnik opisuje wprowadzone optymalizacje pamięci w aplikacji MPD, które mają na celu zmniejszenie zużycia RAM i poprawę wydajności.

## Wprowadzone optymalizacje

### 1. Konfiguracja bazy danych

#### Connection Pooling
- Dodano `CONN_MAX_AGE=600` (10 minut) dla wszystkich baz danych
- Skonfigurowano `MAX_CONNS=20` i `MIN_CONNS=5` dla connection pooling
- Włączono `CONN_HEALTH_CHECKS=True` dla monitorowania połączeń

#### Przykład konfiguracji:
```python
DATABASES = {
    'MPD': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('MPD_DB_NAME'),
        'USER': os.getenv('MPD_DB_USER'),
        'PASSWORD': os.getenv('MPD_DB_PASSWORD'),
        'HOST': os.getenv('MPD_DB_HOST'),
        'PORT': os.getenv('MPD_DB_PORT'),
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
        },
        'CONN_MAX_AGE': 600,  # 10 minut
        'CONN_HEALTH_CHECKS': True,
    }
}
```

### 2. Cache Redis

#### Konfiguracja cache:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://:dev_password@redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        },
        'KEY_PREFIX': 'nc_cache',
        'TIMEOUT': 300,  # 5 minut domyślnie
    }
}
```

### 3. Optymalizacje zapytań

#### Używanie iterator() dla dużych querysetów:
```python
# Przed optymalizacją
sizes_queryset = Sizes.objects.filter(category='bielizna')

# Po optymalizacji
sizes_queryset = Sizes.objects.filter(category='bielizna').iterator(chunk_size=1000)
```

#### Batch processing:
```python
def process_sizes_batch(sizes_batch, batch_number, total_batches):
    """Przetwarza batch rozmiarów z optymalizacją pamięci"""
    for size in sizes_batch:
        # Przetwarzanie pojedynczego rozmiaru
        pass
    
    # Czyszczenie pamięci po batch
    gc.collect()
```

### 4. Narzędzia optymalizacji pamięci

#### MemoryOptimizer
Klasa do zarządzania optymalizacją pamięci:

```python
from MPD.memory_optimizer import MemoryOptimizer

optimizer = MemoryOptimizer()

# Sprawdź użycie pamięci
memory_info = optimizer.get_memory_usage()
print(f"Użycie pamięci: {memory_info['percent']:.2f}%")

# Wykonaj optymalizację
result = optimizer.optimize_memory()
print(f"Zaoszczędzono {result['memory_saved_mb']:.2f} MB")
```

#### QueryOptimizer
Klasa do optymalizacji zapytań:

```python
from MPD.memory_optimizer import QueryOptimizer

query_optimizer = QueryOptimizer()

# Optymalizuj queryset
optimized_queryset = query_optimizer.optimize_queryset(
    ProductVariants.objects.all(),
    use_iterator=True,
    batch_size=1000
)

# Przetwarzaj w batch'ach
for result in query_optimizer.process_in_batches(
    ProductVariants.objects.all(),
    process_func=my_processing_function
):
    pass
```

### 5. Context Managers

#### Monitorowanie pamięci:
```python
from MPD.memory_optimizer import memory_monitor, query_monitor

with memory_monitor("eksport XML"):
    with query_monitor():
        # Twój kod tutaj
        exporter.export()
```

### 6. Zadania Celery z optymalizacją

#### Przykład zoptymalizowanego taska:
```python
@shared_task(bind=True, name='mpd.export_full_xml_hourly')
def export_full_xml_hourly(self):
    with memory_monitor("eksport full.xml"):
        try:
            exporter = FullXMLExporter()
            with query_monitor():
                result = exporter.export()
            return result
        except Exception as e:
            # Obsługa błędów
            pass
```

## Najlepsze praktyki

### 1. Używanie iterator() dla dużych zbiorów danych
```python
# ✅ Dobrze - używa iterator()
for product in ProductVariants.objects.all().iterator(chunk_size=1000):
    process_product(product)

# ❌ Źle - ładuje wszystko do pamięci
for product in ProductVariants.objects.all():
    process_product(product)
```

### 2. Batch processing
```python
# ✅ Dobrze - przetwarza w batch'ach
batch_size = 1000
for offset in range(0, total_count, batch_size):
    batch = list(queryset[offset:offset + batch_size])
    process_batch(batch)
    del batch  # Wyczyść pamięć
    gc.collect()
```

### 3. Używanie select_related i prefetch_related
```python
# ✅ Dobrze - optymalizuje zapytania
queryset = ProductVariants.objects.select_related(
    'product', 'size', 'color'
).prefetch_related('images')

# ❌ Źle - N+1 problem
for variant in ProductVariants.objects.all():
    print(variant.product.name)  # Dodatkowe zapytanie dla każdego wariantu
```

### 4. Czyszczenie pamięci
```python
# Regularne czyszczenie pamięci
import gc

# Po przetworzeniu dużych obiektów
del large_object
gc.collect()

# W taskach Celery
@shared_task
def my_task():
    try:
        # Przetwarzanie
        pass
    finally:
        gc.collect()  # Zawsze wyczyść pamięć
```

### 5. Cache'owanie często używanych danych
```python
from django.core.cache import cache

# Cache'uj wyniki zapytań
def get_popular_products():
    cache_key = 'popular_products'
    products = cache.get(cache_key)
    
    if products is None:
        products = list(ProductVariants.objects.filter(
            stock__gt=0
        ).select_related('product')[:100])
        cache.set(cache_key, products, 300)  # 5 minut
    
    return products
```

## Monitorowanie wydajności

### 1. Sprawdzanie użycia pamięci
```python
from MPD.memory_optimizer import get_memory_usage_summary

summary = get_memory_usage_summary()
print(f"Użycie pamięci: {summary['memory_percent']:.2f}%")
print(f"Pamięć fizyczna: {summary['memory_mb']:.2f} MB")
print(f"Przekroczono próg: {summary['threshold_exceeded']}")
```

### 2. Logowanie optymalizacji
```python
import logging

logger = logging.getLogger(__name__)

# W taskach Celery
logger.info(f"Rozpoczynam task - użycie pamięci: {memory_percent:.2f}%")
logger.info(f"Zakończono task - zaoszczędzono {memory_saved:.2f} MB")
```

## Konfiguracja produkcji

### 1. Ustawienia Django
```python
# settings/prod.py
DEBUG = False
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
        },
        'TIMEOUT': 600,  # 10 minut
    }
}

# Optymalizacje pamięci
MEMORY_OPTIMIZATION = {
    'ENABLE_QUERY_LOGGING': False,
    'ENABLE_SQL_LOGGING': False,
    'MAX_MEMORY_USAGE': 0.8,  # 80% maksymalnego użycia RAM
}

DATABASE_OPTIMIZATION = {
    'QUERY_TIMEOUT': 30,
    'MAX_QUERY_RESULTS': 10000,
    'BATCH_SIZE': 2000,  # Większy batch w produkcji
}
```

### 2. Konfiguracja Celery
```python
# celery.py
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Restart worker'a co 1000 tasków
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Pobieraj jeden task na raz
```

### 3. Monitorowanie w produkcji
```python
# Periodic task do optymalizacji pamięci
CELERY_BEAT_SCHEDULE = {
    'optimize-memory': {
        'task': 'mpd.optimize_memory',
        'schedule': crontab(minute=0, hour='*/2'),  # Co 2 godziny
    },
}
```

## Rozwiązywanie problemów

### 1. Wysokie użycie pamięci
```python
# Sprawdź użycie pamięci
from MPD.memory_optimizer import MemoryOptimizer

optimizer = MemoryOptimizer()
if optimizer.check_memory_threshold():
    print("Przekroczono próg pamięci!")
    optimizer.optimize_memory()
```

### 2. Wolne zapytania
```python
# Użyj query_monitor do debugowania
from MPD.memory_optimizer import query_monitor

with query_monitor():
    # Twój kod tutaj
    result = expensive_query()
```

### 3. Memory leaks
```python
# Regularne czyszczenie w taskach
@shared_task
def my_task():
    try:
        # Przetwarzanie
        pass
    finally:
        # Zawsze wyczyść pamięć
        gc.collect()
        # Zamknij połączenia z bazą
        from django.db import connection
        connection.close()
```

## Podsumowanie

Wprowadzone optymalizacje powinny znacząco zmniejszyć zużycie pamięci aplikacji poprzez:

1. **Connection pooling** - efektywne zarządzanie połączeniami z bazą danych
2. **Cache Redis** - przechowywanie często używanych danych w pamięci
3. **Iterator i batch processing** - przetwarzanie dużych zbiorów danych bez ładowania wszystkiego do pamięci
4. **Automatyczne czyszczenie pamięci** - regularne garbage collection
5. **Monitorowanie** - śledzenie użycia pamięci i wydajności

Te optymalizacje są szczególnie ważne dla aplikacji przetwarzających duże ilości danych, takich jak eksport XML czy import produktów.
