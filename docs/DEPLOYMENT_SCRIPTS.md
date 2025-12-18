# 🚀 Przewodnik po skryptach deployment

## Szybki wybór - który skrypt użyć?

### 🎯 Chcę zero-downtime deployment (ZALECANE)
```powershell
./scripts/deploy/deploy-blue-green.sh deploy
```
- ✅ Stary obraz działa podczas budowania
- ✅ Tylko 2-5s downtime
- ✅ Automatyczny rollback
- ✅ Backup obrazów

**Dokumentacja:** [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md)

---

### ⚡ Chcę tylko szybki build (bez orchestracji)
```powershell
.\scripts\build\build-fast.ps1
```
- ✅ BuildKit cache (bardzo szybkie kolejne buildy)
- ✅ Cache dla apt i pip
- ✅ Idealne podczas development

**Dokumentacja:** [BUILD_OPTIMIZATION.md](BUILD_OPTIMIZATION.md)

---

### 🔙 Chcę rollback do poprzedniej wersji
```powershell
./scripts/deploy/deploy-blue-green.sh rollback
```
- ✅ Wybór z dostępnych backupów
- ✅ Szybkie przywrócenie
- ✅ Bez utraty danych

---

### 🔨 Chcę pełny rebuild (od zera, bez cache)
```bash
# Linux/Mac
./scripts/build/build-no-cache.sh

# Lub ręcznie
docker-compose build --no-cache
```
- Użyj gdy coś jest zepsute
- Dłużej trwa (5-10 minut)

---

## 📊 Porównanie skryptów

| Skrypt | Downtime | Czas | Cache | Rollback | Use Case |
|--------|----------|------|-------|----------|----------|
| `deploy-blue-green` | 2-5s | ~1min | ✅ | ✅ | **Production deploy (blue-green)** |
| `build-fast` | N/A | ~30s-1min | ✅ | ❌ | **Development** |
| `rollback` | 2-5s | ~10s | ✅ | ✅ | **Przywracanie (blue-green)** |
| `build-no-cache` | N/A | ~10min | ❌ | ❌ | **Troubleshooting** |

---

## 🎯 Typowe scenariusze

### Scenario 1: Codzienne development
```powershell
# Zmieniasz kod
# ... edytujesz pliki ...

# Szybki rebuild
.\scripts\build\build-fast.ps1

# Start kontenerów
docker-compose -f docker-compose.dev.yml up -d
```

### Scenario 2: Production deployment
```powershell
# Blue-green deploy
./scripts/deploy/deploy-blue-green.sh deploy

# Sprawdź czy działa
Start-Process "http://localhost"

# Jeśli coś nie tak - rollback
./scripts/deploy/deploy-blue-green.sh rollback
```

### Scenario 3: Dodałeś nowy pakiet do requirements.txt
```powershell
# Rebuild z cache (tylko nowy pakiet się pobierze)
.\scripts\build\build-fast.ps1

# Restart kontenerów
docker-compose -f docker-compose.dev.yml up -d --force-recreate
```

### Scenario 4: Problem z cache (coś się zepsuło)
```bash
# Wyczyść cache i zbuduj od zera
./scripts/build/build-no-cache.sh
```

---

## 📁 Struktura plików

```
nc_project/
│
├── 🎯 DEPLOYMENT SCRIPTS
│   ├── scripts/build/build-fast.ps1              # Szybki build z cache (Windows)
│   ├── scripts/build/build-fast.sh               # Szybki build z cache (Linux/Mac)
│   ├── scripts/deploy/deploy-blue-green.sh       # Blue-green deploy + rollback
│   └── scripts/build/build-no-cache.sh           # Build bez cache
│
├── 📚 DOKUMENTACJA
│   ├── ZERO_DOWNTIME_DEPLOYMENT.md # Orkiestracja deployment
│   ├── BUILD_OPTIMIZATION.md       # Optymalizacja buildów
│   └── DEPLOYMENT_SCRIPTS.md       # Ten plik
│
├── 🐳 DOCKER CONFIG
│   ├── Dockerfile                  # Development
│   ├── Dockerfile.prod             # Production
│   ├── docker-compose.dev.yml      # Development compose
│   └── docker-compose.yml          # Production compose
│
└── 📦 DEPENDENCIES
    └── requirements.txt            # Python packages
```

---

## 💡 Best Practices

### ✅ DO:
- Używaj `deploy-blue-green` dla production
- Używaj `build-fast` dla development
- Testuj deployment na dev przed production
- Regularnie sprawdzaj dostępne backupy
- Monitoruj logi po deployment

### ❌ DON'T:
- Nie używaj `build-no-cache` bez powodu (wolny)
- Nie rób deployment bez backupu
- Nie ignoruj błędów health check
- Nie wyłączaj automatycznego rollback

---

## 🔧 Konfiguracja

### Wymagania systemowe
- Docker Engine 18.09+
- Docker Compose 1.25+
- PowerShell 5.1+ (Windows) lub Bash (Linux/Mac)

### Zmienne środowiskowe
```powershell
# BuildKit (automatycznie ustawiane przez skrypty)
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"
```

---

## 🐛 Troubleshooting

### Problem: "docker-compose: command not found"
```bash
# Zainstaluj Docker Compose
# https://docs.docker.com/compose/install/
```

### Problem: Skrypt nie ma uprawnień
```bash
# Linux/Mac
chmod +x *.sh

# Windows - uruchom PowerShell jako Administrator
```

### Problem: BuildKit nie działa
```powershell
# Sprawdź wersję Docker
docker version

# Powinno być >= 18.09
```

### Problem: Build trwa zbyt długo
1. Sprawdź czy BuildKit jest włączony
2. Sprawdź czy używasz `build-fast` a nie `build-no-cache`
3. Sprawdź dostępne zasoby: `docker system df`

---

## 📈 Metryki

### Build times (z cache):
- **Pierwszy build:** ~5-10 minut (cold cache)
- **Zmiana kodu:** ~30-60 sekund (warm cache)
- **Dodanie pakietu:** ~2-3 minuty (partial cache)
- **No cache rebuild:** ~10 minut (no cache)

### Deployment downtime:
- **Tradycyjny:** 6-11 minut ❌
- **Zero-downtime:** 2-5 sekund ✅
- **Rollback:** ~10 sekund ✅

---

## 🎓 Learn More

### Dokumentacja
1. [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md) - Szczegóły orkiestracji
2. [BUILD_OPTIMIZATION.md](BUILD_OPTIMIZATION.md) - Jak działa cache

### External resources
- [Docker BuildKit](https://docs.docker.com/build/buildkit/)
- [Blue-Green Deployment](https://martinfowler.com/bliki/BlueGreenDeployment.html)
- [Docker Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

## 🆘 Pomoc

Masz problem? Sprawdź:
1. Logi: `docker-compose logs -f`
2. Status: `docker-compose ps`
3. System resources: `docker system df`
4. Health: `docker inspect <container_name>`

---

## 📝 Quick Reference

```powershell
# DEVELOPMENT
.\scripts\build\build-fast.ps1                                      # Szybki build
docker-compose -f docker-compose.dev.yml up -d       # Start
docker-compose -f docker-compose.dev.yml logs -f     # Logi
docker-compose -f docker-compose.dev.yml down        # Stop

# PRODUCTION DEPLOY
./scripts/deploy/deploy-blue-green.sh deploy             # Deploy
./scripts/deploy/deploy-blue-green.sh rollback           # Rollback

# TROUBLESHOOTING
docker-compose ps                                     # Status
docker-compose logs web                               # Logi web
docker system prune -a                                # Cleanup
./scripts/build/build-no-cache.sh                                   # Full rebuild

# MONITORING
docker stats                                          # Resources
docker-compose top                                    # Processes
Start-Process "http://localhost:5555"                 # Flower (Celery)
```

---

**Happy deploying! 🚀**

