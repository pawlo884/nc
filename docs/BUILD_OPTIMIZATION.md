# Optymalizacja budowania obrazów Docker

## 🚀 Problem
Budowanie obrazów Docker trwało bardzo długo, ponieważ za każdym razem pobierane były pakiety systemowe (apt) i pakiety Python (pip).

## ✅ Rozwiązanie
Zastosowano **BuildKit cache mounts**, które cache'ują pobrane pakiety między buildami.

## 📦 Co zostało zoptymalizowane?

### 1. Cache dla apt (pakiety systemowe)
```dockerfile
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y gcc g++ libpq-dev ...
```

### 2. Cache dla pip (pakiety Python)
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --break-system-packages -r requirements.txt
```

### 3. Prawidłowa kolejność warstw
1. ✅ Najpierw pakiety systemowe (zmieniane rzadko)
2. ✅ Potem requirements.txt + pip install (zmieniane rzadko)
3. ✅ Na końcu kod aplikacji (zmieniane często)

## 🎯 Efekty

### Pierwszy build (cold cache)
- Czas: ~5-10 minut
- Pobierane są wszystkie pakiety

### Kolejne buildy (warm cache)
- **Tylko zmiana kodu**: ~30 sekund - 1 minuta
- **Zmiana requirements.txt**: ~2-3 minuty
- **Zmiana pakietów systemowych**: ~3-4 minuty

### Przykład optymalizacji:
```
PRZED: 10 minut za każdym razem
PO: 30 sekund gdy zmienia się tylko kod
OSZCZĘDNOŚĆ: ~95% czasu przy codziennej pracy!
```

## 🛠️ Jak używać?

### Metoda 1: Szybkie skrypty (ZALECANE)
```powershell
# Windows PowerShell
.\build-fast.ps1

# Linux/Mac
./build-fast.sh
```

### Metoda 2: Ręcznie z BuildKit
```powershell
# Windows PowerShell
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"
docker-compose -f docker-compose.dev.yml build --parallel
```

```bash
# Linux/Mac
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
docker-compose -f docker-compose.dev.yml build --parallel
```

### Metoda 3: Bez BuildKit (stare podejście - WOLNE)
```bash
docker-compose -f docker-compose.dev.yml build
```

## 📝 Wymagania
- Docker Engine 18.09+ (BuildKit support)
- Docker Compose 1.25+

## 🔍 Jak to działa?

### BuildKit cache mounts
- `--mount=type=cache,target=/root/.cache/pip` - tworzy persystentny cache dla pip
- `sharing=locked` - pozwala na bezpieczne współdzielenie cache między buildami
- Cache jest przechowywany na hoście i używany ponownie

### Przykład działania:

#### Build 1 (pierwszy):
```
1. Pobierz obraz bazowy Python
2. Zainstaluj gcc, g++, libpq-dev (POBIERZ z internetu)
3. Zainstaluj pakiety pip (POBIERZ z PyPI)
4. Skopiuj kod
```

#### Build 2 (po zmianie kodu):
```
1. Użyj cache obrazu bazowego ✅
2. Użyj cache pakietów systemowych ✅
3. Użyj cache pakietów pip ✅
4. Skopiuj NOWY kod (tylko ta warstwa się zmienia)
```

#### Build 3 (po dodaniu nowego pakietu do requirements.txt):
```
1. Użyj cache obrazu bazowego ✅
2. Użyj cache pakietów systemowych ✅
3. Zainstaluj tylko NOWE pakiety pip (stare są w cache) ⚡
4. Skopiuj kod
```

## 🎨 Zaawansowane użycie

### Czyszczenie cache (gdy potrzebny rebuild od zera)
```bash
# Wyczyść cache buildx
docker buildx prune -a

# Rebuild bez cache
docker-compose -f docker-compose.dev.yml build --no-cache
```

### Sprawdzenie rozmiaru cache
```bash
docker system df -v
```

### Czyszczenie tylko build cache
```bash
docker builder prune
```

## 💡 Dodatkowe tipy

1. **Nie zmieniaj requirements.txt zbyt często** - dodawaj pakiety partiami
2. **Grupuj RUN commands** - każdy RUN to osobna warstwa
3. **Używaj .dockerignore** - nie kopiuj zbędnych plików
4. **Multi-stage builds** - jeszcze lepsza optymalizacja dla produkcji

## 🐛 Rozwiązywanie problemów

### Cache nie działa?
```bash
# Sprawdź czy BuildKit jest włączony
docker buildx version

# Sprawdź czy używasz nowej składni
head -n 1 Dockerfile
# Powinno być: # syntax=docker/dockerfile:1.4
```

### Build nadal wolny?
```bash
# Upewnij się że BuildKit jest włączony
echo $env:DOCKER_BUILDKIT  # Windows
echo $DOCKER_BUILDKIT      # Linux/Mac

# Powinno zwrócić: 1
```

### Błąd "unknown flag: --mount"?
- Aktualizuj Docker Engine do wersji 18.09+
- Upewnij się że pierwsza linia Dockerfile to: `# syntax=docker/dockerfile:1.4`

## 🚀 Zero-Downtime Deployment

Chcesz aby stary obraz działał podczas budowania nowego?

**Zobacz:** [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md)

Nasz system orkiestracji zapewnia:
- ✅ Stary obraz działa podczas budowania nowego
- ✅ Tylko 2-5 sekund downtime (zamiast 5-10 minut!)
- ✅ Automatyczny rollback w przypadku błędów
- ✅ Backup obrazów i łatwy powrót do poprzednich wersji

```powershell
# Uruchom zero-downtime deployment
.\deploy-zero-downtime.ps1 -Environment dev
```

## 📚 Więcej informacji
- [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md) - Orkiestracja deploymentu
- [BuildKit documentation](https://docs.docker.com/build/buildkit/)
- [Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker layer caching](https://docs.docker.com/build/cache/)

