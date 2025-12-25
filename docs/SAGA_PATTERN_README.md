# 🚀 Saga Pattern Implementation

## Opis

Ten projekt implementuje **Saga Pattern** do bezpiecznego wykonywania operacji między różnymi bazami danych (matterhorn1, MPD) z automatyczną kompensacją.

## Problem

**Przed implementacją Saga Pattern:**
```python
# ❌ NIEBEZPIECZNE - operacje na dwóch bazach bez atomowej transakcji
def create_product():
    # Krok 1: Zapisz w matterhorn1
    product.mapped_product_id = mpd_product_id
    product.save()  # COMMIT!
    
    # Krok 2: Zapisz w MPD
    with connections['MPD'].cursor() as cursor:
        cursor.execute("INSERT INTO product_variants...")  # COMMIT!
    
    # ❌ Jeśli błąd w kroku 2, dane w matterhorn1 są nieaktualne!
```

**Po implementacji Saga Pattern:**
```python
# ✅ BEZPIECZNE - automatyczna kompensacja
def create_product():
    saga_result = SagaService.create_product_with_mapping(
        matterhorn_data, mpd_data
    )
    # Jeśli błąd, wszystkie kroki są automatycznie cofnięte!
```

## Architektura

### Komponenty

1. **SagaOrchestrator** - zarządza wykonywaniem kroków i kompensacją
2. **SagaService** - gotowe implementacje typowych operacji
3. **Saga Models** - logowanie i monitorowanie
4. **SagaStep** - pojedynczy krok z funkcją execute i compensate

### Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Krok 1        │    │   Krok 2        │    │   Krok 3        │
│   MPD Create    │───►│   Matterhorn    │───►│   Add Attrs     │
│                 │    │   Mapping       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Krok 1 ✅     │    │   Krok 2 ✅     │    │   Krok 3 ❌     │
│   Completed     │    │   Completed     │    │   Failed        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KOMPENSACJA (odwrotna kolejność)            │
│                                                                 │
│   Krok 2: Cofnij Mapping  ◄──  Krok 1: Usuń z MPD             │
└─────────────────────────────────────────────────────────────────┘
```

## Użycie

### 1. Gotowe operacje

```python
from matterhorn1.saga import SagaService

# Tworzenie produktu z mapping
result = SagaService.create_product_with_mapping(
    matterhorn_product_data={
        'product_id': 12345,
        'mpd_product_id': 67890
    },
    mpd_product_data={
        'name': 'Test Product',
        'attributes': [1, 2, 3]
    }
)

# Tworzenie wariantów z mapping
result = SagaService.create_variants_with_mapping(
    product_id=12345,
    mpd_product_id=67890,
    variants_data=[
        {
            'variant_id': 'var_001',
            'color_id': 1,
            'size_id': 1
        }
    ]
)
```

### 2. Własna Saga

```python
from matterhorn1.saga import SagaOrchestrator

def my_execute_function(data):
    # Logika wykonania kroku
    return {'result': 'success'}

def my_compensate_function(data):
    # Logika kompensacji
    pass

# Utwórz Saga
saga = SagaOrchestrator(saga_type="my_operation")

# Dodaj kroki
saga.add_step(
    name="step1",
    execute_func=my_execute_function,
    compensate_func=my_compensate_function,
    data={'param': 'value'}
)

# Wykonaj
result = saga.execute()
```

### 3. Sprawdzanie wyniku

```python
if result.status.value == 'completed':
    print("✅ Saga zakończona pomyślnie")
    print(f"Saga ID: {result.saga_id}")
    
    # Sprawdź wyniki kroków
    for step in result.steps:
        print(f"  - {step.name}: {step.status.value}")
        
elif result.status.value == 'compensated':
    print("🔄 Saga skompensowana")
    print(f"Błąd: {result.error}")
    
    # Sprawdź które kroki się nie powiodły
    for step in result.steps:
        if step.status.value == 'failed':
            print(f"  ❌ {step.name}: {step.error}")
```

## Logowanie i Monitorowanie

### Modele

```python
from matterhorn1.saga_models import Saga, SagaStep

# Sprawdź status Saga
saga = Saga.objects.get(saga_id="your-saga-id")
print(f"Status: {saga.status}")
print(f"Utworzona: {saga.created_at}")
print(f"Zakończona: {saga.completed_at}")

# Sprawdź kroki
for step in saga.steps.all():
    print(f"  - {step.step_name}: {step.status}")
    if step.error_message:
        print(f"    Błąd: {step.error_message}")
```

### Logi

Wszystkie operacje Saga są logowane:

```
🚀 Saga abc123: Rozpoczynam wykonanie 3 kroków
🔄 Saga abc123: Wykonuję krok 'create_mpd_product'
✅ Saga abc123: Krok 'create_mpd_product' wykonany pomyślnie
🔄 Saga abc123: Wykonuję krok 'create_matterhorn_product_with_mapping'
❌ Saga abc123: Błąd w kroku 'create_matterhorn_product_with_mapping': Connection timeout
🔄 Saga abc123: Rozpoczynam kompensację
🔄 Saga abc123: Kompensuję krok 'create_mpd_product'
✅ Saga abc123: Krok 'create_mpd_product' skompensowany
✅ Saga abc123: Kompensacja zakończona
```

## Migracja z istniejącego kodu

### Przed (problematiczny kod):

```python
# matterhorn1/admin.py
def create_product_in_mpd(self, request, product_id):
    # 1. Zapisz w matterhorn1
    product.mapped_product_id = mpd_product_id
    product.save()  # COMMIT!
    
    # 2. Zapisz w MPD
    with connections['MPD'].cursor() as cursor:
        cursor.execute("INSERT INTO product_variants...")  # COMMIT!
    
    # 3. Jeśli błąd w kroku 2, dane w matterhorn1 są nieaktualne!
```

### Po (bezpieczny kod):

```python
# matterhorn1/admin.py
def create_product_in_mpd(self, request, product_id):
    from matterhorn1.saga import SagaService
    
    # Przygotuj dane
    matterhorn_data = {
        'product_id': product_id,
        'mpd_product_id': mpd_product_id
    }
    
    mpd_data = {
        'mpd_product_id': mpd_product_id,
        'attributes': request.POST.getlist('mpd_attributes')
    }
    
    # Użyj Saga Pattern
    saga_result = SagaService.create_product_with_mapping(
        matterhorn_data, mpd_data
    )
    
    if saga_result.status.value != 'completed':
        return JsonResponse({
            'success': False, 
            'error': f"Saga failed: {saga_result.error}"
        })
    
    return JsonResponse({'success': True})
```

## Zalety

### ✅ Bezpieczeństwo
- **Automatyczna kompensacja** - jeśli któryś krok się nie powiedzie, wszystkie poprzednie kroki są cofnięte
- **Consistency** - dane pozostają spójne między bazami
- **No partial state** - nie ma stanów częściowo zaktualizowanych

### ✅ Monitorowanie
- **Pełne logowanie** - każdy krok jest logowany
- **Status tracking** - można śledzić postęp Saga
- **Error details** - szczegółowe informacje o błędach

### ✅ Elastyczność
- **Gotowe operacje** - typowe scenariusze są już zaimplementowane
- **Custom Saga** - można tworzyć własne Saga
- **Composable** - kroki można łączyć w różne kombinacje

### ✅ Maintainability
- **Centralized logic** - logika kompensacji w jednym miejscu
- **Reusable** - te same kroki można używać w różnych Saga
- **Testable** - każdy krok można testować osobno

## Przykłady

Zobacz plik `matterhorn1/saga_example.py` dla pełnych przykładów użycia.

## Status implementacji

- ✅ **SagaOrchestrator** - podstawowa implementacja
- ✅ **SagaService** - gotowe operacje (product creation, variant creation)
- ✅ **Logging** - pełne logowanie do bazy danych
- ✅ **Models** - modele do monitorowania
- ✅ **Integration** - integracja z istniejącym kodem
- 🔄 **Testing** - testy jednostkowe (w trakcie)
- 🔄 **Admin interface** - interfejs do monitorowania Saga (planowane)

## Następne kroki

1. **Dodaj modele do admin.py** - interfejs do monitorowania Saga
2. **Napisz testy** - testy jednostkowe dla Saga operations
3. **Dokumentacja API** - szczegółowa dokumentacja funkcji
4. **Performance monitoring** - metryki wydajności Saga
5. **Alerting** - powiadomienia o błędach Saga

