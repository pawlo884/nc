# 🤖 ML Container - TODO List

## 📋 Plan implementacji osobnego kontenera ML

### Cel:
Osobny kontener Docker dla tasków ML (embeddings, semantic search) z PyTorch, aby **nie spowalniać** standardowych deploymentów.

---

## ✅ TODO Lista:

### 1. Dockerfile.ml ✅
- [x] Stworzyć `Dockerfile.ml` z Python 3.13-slim
- [x] Instalacja requirements.txt (podstawowe)
- [x] Instalacja requirements.ml.txt (PyTorch ~2-3GB)
- [x] BuildKit cache dla obu warstw pip

### 2. requirements.ml.txt ✅
- [x] `torch==2.8.0` (najnowszy, kompatybilny z Python 3.13)
- [x] `torchvision==0.23.0` (najnowszy, kompatybilny z torch 2.8.0)
- [x] `torchaudio==2.8.0` (najnowszy, kompatybilny z torch 2.8.0)
- [x] `sentence-transformers==3.3.1`
- [x] `qdrant-client==1.12.0`
- [x] `scikit-learn==1.5.2`
- [x] `numpy==2.2.0`

### 3. docker-compose.blue-green.ml.yml i docker-compose.dev.ml.yml ✅
- [x] Serwis `celery-ml` z Dockerfile.ml
- [x] Kolejka: `-Q ml`
- [x] Memory: 2GB limit, 1GB reservation
- [x] Zależności: redis, web
- [x] Network: nc_network / app_network

### 4. Celery routing (nc/celery.py) ✅
```python
app.conf.task_routes = {
    # Import → kolejka 'import'
    'matterhorn1.tasks.full_import_and_update': {'queue': 'import'},

    # Reszta → kolejka 'default'
    'matterhorn1.tasks.*': {'queue': 'default'},
    'MPD.tasks.*': {'queue': 'default'},
}
# Kolejka 'ml' zostanie dodana razem z pierwszym zadaniem ML.
```

### 5. GitHub Actions ✅
- [x] Dodać job do buildu ML image
- [x] Build tylko gdy zmieni się: `requirements.ml.txt` lub `Dockerfile.ml`
- [x] Cache: `pawlo884/django-app-ml:buildcache`
- [x] Push: `pawlo884/django-app-ml:latest`
- [x] **NIE** trigger przy zmianie `tasks.py` (kod kopiowany w runtime)

### 6. Przykładowe taski ML ⏭️
**POMINIĘTE** - Taski ML dodamy w przyszłości gdy będą potrzebne.  
Osobny kontener jest już gotowy!

### 7. Dokumentacja ✅
- [x] `ML_CONTAINER_SETUP.md` - instrukcje
- [x] Przykłady użycia
- [x] Deployment guide
- [x] Troubleshooting

---

## 🎯 Korzyści:

| Aspekt | Bez osobnego kontenera | Z osobnym kontenerem |
|--------|------------------------|----------------------|
| Build (zmiana kodu) | ~20-25 min | ~3-5 min ⚡ |
| Build (zmiana ML) | ~20-25 min | ~20-25 min (ML osobno) |
| Deployment | Zawsze wolny | 99% szybki |
| RAM usage | Zawsze ~2GB | Tylko gdy ML działa |
| Skalowanie | Trudne | Łatwe (0-N workerów) |

---

## ⏱️ Szacowany czas implementacji:
**~2-3 godziny** (wszystkie kroki)

---

## 📚 Powiązane dokumenty:
- [DOCKER_STRUCTURE.md](DOCKER_STRUCTURE.md) - aktualna struktura
- [DOCKER_QUICK_GUIDE.md](DOCKER_QUICK_GUIDE.md) - jak używać
- [BUILD_OPTIMIZATION.md](BUILD_OPTIMIZATION.md) - optymalizacje

---

## 🚀 Quick Deploy (przyszłość):

### Bez ML (standardowy):
```bash
./scripts/deploy/deploy-blue-green.sh deploy
```

### Z ML (gdy potrzebny):
```bash
docker-compose -f docker-compose.blue-green.yml -f docker-compose.blue-green.ml.yml up -d celery-ml
```

---

**Status**: ✅ GOTOWE - Infrastruktura ML zaimplementowana!
**Data utworzenia**: 2025-10-07
**Data ukończenia**: 2025-10-07
**Priorytet**: ✅ Zrealizowane

## 📦 Utworzone pliki:
- ✅ `requirements.ml.txt` - zależności ML
- ✅ `Dockerfile.ml` - kontener ML z PyTorch
- ✅ `docker-compose.blue-green.ml.yml` - konfiguracja ML dla produkcji (blue-green)
- ✅ `docker-compose.dev.ml.yml` - konfiguracja ML dla dev
- ✅ `ML_CONTAINER_SETUP.md` - pełna dokumentacja
- ✅ `nc/celery.py` - zaktualizowany routing
- ✅ `.github/workflows/deploy.yml` - warunkowy build ML

## 🚀 Jak używać:
```bash
# DEV - Standardowy deploy (szybki, BEZ ML)
docker-compose -f docker-compose.dev.yml up -d --build

# DEV - Deploy Z ML (gdy potrzebny)
docker-compose -f docker-compose.dev.yml -f docker-compose.dev.ml.yml up -d --build

# PROD - Standardowy deploy (szybki, BEZ ML)
./scripts/deploy/deploy-blue-green.sh deploy

# PROD - Deploy Z ML (gdy potrzebny)
docker-compose -f docker-compose.blue-green.yml -f docker-compose.blue-green.ml.yml up -d celery-ml
```



