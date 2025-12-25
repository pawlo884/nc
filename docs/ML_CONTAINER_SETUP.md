# 🤖 ML Container - Dokumentacja

## 📋 Cel i uzasadnienie

Osobny kontener Docker dla tasków ML (embeddings, semantic search) z PyTorch, aby **NIE spowalniać** standardowych deploymentów.

### Problem:
- PyTorch + sentence-transformers = ~2-3GB do pobrania
- Każdy deploy z ML w requirements.txt = **20-25 minut** buildu
- 99% zmian w kodzie **NIE wymaga** reinstalacji ML

### Rozwiązanie:
- **2 osobne kontenery**:
  - `django-app` (Dockerfile.prod) - szybki build **3-5 min**
  - `django-app-ml` (Dockerfile.ml) - wolny build **20-25 min**, ale RZADKO

---

## 📂 Struktura plików

```
nc_project/
├── Dockerfile.dev              # Dev kontener (bez ML)
├── Dockerfile.prod             # Prod kontener (bez ML)
├── Dockerfile.ml               # ML kontener (z PyTorch) - dla dev i prod
├── requirements.txt            # Podstawowe zależności
├── requirements.ml.txt         # ML zależności (PyTorch, sentence-transformers)
├── docker-compose.dev.yml      # Dev - standardowe serwisy
├── docker-compose.dev.ml.yml   # Dev - ML serwis (opcjonalny)
├── docker-compose.blue-green.yml     # Prod - blue-green
├── docker-compose.blue-green.ml.yml  # Prod - ML worker (opcjonalny)
└── .github/workflows/deploy.yml # CI/CD z warunkowym buildem ML
```

---

## 🐳 Pliki Docker

### 1. `Dockerfile.ml`
- Bazuje na `python:3.13-slim`
- **Warstwa 1**: Instaluje `requirements.txt` (cache podstawowy)
- **Warstwa 2**: Instaluje `requirements.ml.txt` (cache ML - osobno!)
- **Warstwa 3**: Kopiuje kod aplikacji

### 2. `requirements.ml.txt`
```txt
# PyTorch - najnowsze wersje kompatybilne z Python 3.13
torch==2.8.0  # ~2-3GB
torchvision==0.23.0
torchaudio==2.8.0

sentence-transformers==3.3.1
qdrant-client==1.12.0
scikit-learn==1.5.2
numpy==2.2.0
```

### 3. `docker-compose.blue-green.ml.yml` i `docker-compose.dev.ml.yml`
- Serwis: `celery-ml`
- Kolejka: `-Q ml`
- Pamięć: 2GB limit, 1GB reservation
- Cache modeli: `/app/ml_models` volume

---

## ⚙️ Konfiguracja Celery

### Routing tasków (`nc/celery.py`)
```python
app.conf.task_routes = {
    # Import → kolejka 'import'
    'matterhorn1.tasks.full_import_and_update': {'queue': 'import'},

    # Reszta → kolejka 'default'
    'matterhorn1.tasks.*': {'queue': 'default'},
    'MPD.tasks.*': {'queue': 'default'},
}
# Kolejka 'ml' zostanie dodana przy pierwszym zadaniu ML.
```

---

## 🚀 Deployment

### 💻 DEVELOPMENT:

#### Standardowy dev (BEZ ML):
```bash
# Build i start wszystkich serwisów
docker-compose -f docker-compose.dev.yml up -d --build

# Tylko rebuild bez start
docker-compose -f docker-compose.dev.yml build

# Logi
docker-compose -f docker-compose.dev.yml logs -f
```
**Czas buildu**: ~3-5 minut ⚡

#### Dev Z ML (gdy potrzebny):
```bash
# Build i start z ML worker
docker-compose -f docker-compose.dev.yml -f docker-compose.dev.ml.yml up -d --build

# Tylko ML worker
docker-compose -f docker-compose.dev.ml.yml up -d --build celery-ml

# Rebuild tylko ML
docker-compose -f docker-compose.dev.ml.yml build celery-ml
```
**Czas buildu ML**: ~20-25 minut (pierwsza instalacja)

#### Zatrzymanie:
```bash
# Stop wszystko (bez ML)
docker-compose -f docker-compose.dev.yml down

# Stop ML worker
docker-compose -f docker-compose.dev.ml.yml down

# Stop wszystko z czyszczeniem volumes
docker-compose -f docker-compose.dev.yml -f docker-compose.dev.ml.yml down -v
```

---

### 🏭 PRODUCTION:

#### Standardowy deploy (BEZ ML):
```bash
./scripts/deploy/deploy-blue-green.sh deploy
```
**Czas buildu**: ~3-5 minut ⚡

#### Deploy Z ML (gdy potrzebny):
```bash
# Uruchom tylko ML worker (nie dotykając postgres/redis)
docker-compose -f docker-compose.blue-green.yml -f docker-compose.blue-green.ml.yml up -d celery-ml
```
**Czas buildu ML**: ~20-25 minut (pierwsza instalacja lub zmiana ML)

#### Zatrzymanie ML workera:
```bash
docker-compose -f docker-compose.blue-green.yml -f docker-compose.blue-green.ml.yml stop celery-ml
```

---

## 🔄 GitHub Actions - Warunkowy build

### Automatyka:
1. **Każdy push** → Build `django-app` (szybki)
2. **Zmiana ML plików** → Build `django-app-ml` (wolny)

### Pliki monitorowane (trigger buildu ML):
- `requirements.ml.txt` - nowe pakiety ML
- `Dockerfile.ml` - zmiana konfiguracji kontenera

**NIE monitorowane**: moduły z zadaniami ML (kod kopiowany w runtime, PyTorch już jest!)

### Rezultat:
- 99% deploymentów: **3-5 minut** ⚡
- 1% deploymentów (ML): **20-25 minut** (tylko gdy trzeba)

---

## 📊 Porównanie wydajności

| Aspekt | Bez osobnego kontenera | Z osobnym kontenerem |
|--------|------------------------|----------------------|
| Build (zmiana kodu) | ~20-25 min | ~3-5 min ⚡ |
| Build (zmiana ML) | ~20-25 min | ~20-25 min (ML osobno) |
| Deployment | Zawsze wolny | 99% szybki |
| RAM usage | Zawsze ~2GB | Tylko gdy ML działa |
| Skalowanie | Trudne | Łatwe (0-N workerów ML) |

---

## 🛠️ Przykład użycia (przyszłość)

### Tworzenie taska ML:
```python
# ml_tasks.py
from celery import shared_task

@shared_task(queue='ml', bind=True)
def generate_embeddings(self, texts):
    """
    Task działa TYLKO w kontenerze celery-ml (ma PyTorch)
    """
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(texts)
    return embeddings.tolist()

@shared_task(queue='ml')
def semantic_search(query, documents):
    """
    Wyszukiwanie semantyczne produktów
    """
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode([query])
    doc_embeddings = model.encode(documents)

    similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
    top_indices = similarities.argsort()[-5:][::-1]

    return [{'index': int(i), 'score': float(similarities[i])} for i in top_indices]
```

### Wywołanie:
```python
# Z dowolnego miejsca w Django
from ml_tasks import generate_embeddings

result = generate_embeddings.delay(['tekst 1', 'tekst 2'])
embeddings = result.get(timeout=30)
```

---

## 🐛 Troubleshooting

### Problem: ML worker nie startuje
```bash
# DEV - Sprawdź logi
docker-compose -f docker-compose.dev.ml.yml logs celery-ml

# PROD - Sprawdź logi
docker-compose -f docker-compose.blue-green.yml -f docker-compose.blue-green.ml.yml logs celery-ml

# Sprawdź czy obraz istnieje
docker images | grep django-app-ml

# DEV - Rebuild ML image
docker-compose -f docker-compose.dev.ml.yml build celery-ml

# PROD - Rebuild ML image
docker-compose -f docker-compose.blue-green.yml -f docker-compose.blue-green.ml.yml build celery-ml
```

### Problem: Brak miejsca na dysku (ML pobiera 2-3GB)
```bash
# Wyczyść stare obrazy
docker system prune -a

# Sprawdź zajęte miejsce
docker system df
```

### Problem: Task nie trafia do ML queue
```bash
# Sprawdź routing w Flower
http://localhost:5555

# Sprawdź konfigurację Celery
docker exec -it <container> python manage.py shell
>>> from nc.celery import app
>>> print(app.conf.task_routes)
```

---

## 📈 Monitoring

### Flower (Celery UI):
- URL: `http://localhost:5555`
- Login: `${FLOWER_USER}:${FLOWER_PASSWORD}`
- Widok kolejek: `default`, `import`, `ml`

### Sprawdzenie ML workera:
```bash
# DEV - Lista workerów
docker-compose -f docker-compose.dev.ml.yml ps

# PROD - Lista workerów
docker-compose -f docker-compose.blue-green.yml -f docker-compose.blue-green.ml.yml ps

# DEV - Logi ML workera
docker-compose -f docker-compose.dev.ml.yml logs -f celery-ml

# PROD - Logi ML workera
docker-compose -f docker-compose.blue-green.yml -f docker-compose.blue-green.ml.yml logs -f celery-ml

# Statystyki pamięci (DEV)
docker stats $(docker-compose -f docker-compose.dev.ml.yml ps -q celery-ml)

# Statystyki pamięci (PROD)
docker stats $(docker-compose -f docker-compose.blue-green.yml -f docker-compose.blue-green.ml.yml ps -q celery-ml)
```

---

## 🔐 Bezpieczeństwo

### Cache modeli ML:
- Volume: `ml_models`
- Ścieżka: `/app/ml_models`
- **NIE commitować** do Git
- Dodaj do `.gitignore`: `ml_models/`

### Zmienne środowiskowe:
```bash
# .env.prod
TRANSFORMERS_CACHE=/app/ml_models/transformers
TORCH_HOME=/app/ml_models/torch
```

---

## 📝 TODO - Implementacja tasków ML

Gdy będzie potrzeba ML, dodaj taski w dedykowanym module (np. `ml_tasks.py`):

- [ ] `generate_embeddings` - generowanie embeddingów dla tekstów
- [ ] `semantic_search` - wyszukiwanie semantyczne
- [ ] `generate_product_embeddings` - embeddingi dla produktów
- [ ] `find_similar_products` - znajdowanie podobnych produktów
- [ ] Integracja z Qdrant (vector database)

**Uwaga**: Osobny kontener jest już gotowy, taski dodamy gdy będą potrzebne!

---

## 🎯 Korzyści finalne

✅ **Szybkie deploymenty** - 99% przypadków to 3-5 min zamiast 20-25 min  
✅ **Elastyczność** - ML worker można włączać/wyłączać na żądanie  
✅ **Skalowanie** - 0-N ML workerów niezależnie od głównej aplikacji  
✅ **Cache** - PyTorch pobierany raz, używany wielokrotnie  
✅ **Izolacja** - Problemy z ML nie wpływają na główną aplikację  

---

**Status**: ✅ Gotowe do użycia  
**Data utworzenia**: 2025-10-07  
**Wersja**: 1.0  

