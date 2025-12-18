# Zero-Downtime Deployment - Orkiestracja

## 🎯 Problem
Podczas standardowego budowania obrazu Docker:
- ❌ Stary obraz jest zastępowany
- ❌ Trzeba zatrzymać aplikację
- ❌ Downtime podczas budowania (5-10 minut)
- ❌ Brak łatwego rollbacku

## ✅ Rozwiązanie: Blue-Green Deployment

Nasz system orkiestracji zapewnia:
- ✅ **Zero downtime** - stary obraz działa podczas budowania nowego
- ✅ **Szybkie przełączenie** - tylko 2-5 sekund downtime
- ✅ **Automatyczny rollback** - w przypadku błędów
- ✅ **Backup obrazów** - możliwość powrotu do dowolnej wersji
- ✅ **BuildKit cache** - szybkie buildy dzięki cache'owaniu

## 🏗️ Jak to działa?

### Faza 1: Budowanie (stary obraz działa)
```
┌─────────────────────────┐
│   STARY OBRAZ           │
│   nc-app:current        │  ← Aplikacja DZIAŁA
│   Serwuje ruch          │
└─────────────────────────┘
           ↓
    [W TLE BUDOWANIE]
           ↓
┌─────────────────────────┐
│   NOWY OBRAZ            │
│   nc-app:new-20250107   │  ← Build w tle
│   Nie jest używany      │
└─────────────────────────┘
```

### Faza 2: Backup i tagowanie
```
┌─────────────────────────┐
│   BACKUP                │
│   nc-app:backup-123456  │  ← Backup starego
└─────────────────────────┘

┌─────────────────────────┐
│   NOWY OBRAZ            │
│   nc-app:current        │  ← Nowy oznaczony jako current
└─────────────────────────┘
```

### Faza 3: Szybkie przełączenie (2-5s downtime)
```
1. Stop kontenerów (1-2s)
2. Remove kontenerów (0s)
3. Start nowych kontenerów z nowym obrazem (1-3s)
```

### Faza 4: Health check i rollback (jeśli potrzebny)
```
✅ Health check OK → Deployment zakończony
❌ Health check FAIL → Automatyczny rollback
```

## 🚀 Użycie

### Deploy z zero-downtime

#### Windows PowerShell:
```powershell
# Development
.\deploy-zero-downtime.ps1 -Environment dev

# Production
.\deploy-zero-downtime.ps1 -Environment prod
```

#### Linux/Mac:
```bash
# Development
./deploy-zero-downtime.sh dev

# Production
./deploy-zero-downtime.sh prod
```

### Rollback do poprzedniej wersji

#### Windows PowerShell:
```powershell
./scripts/deploy/deploy-blue-green.sh rollback
```

#### Linux/Mac:
```bash
./scripts/deploy/deploy-blue-green.sh rollback
```

## 📊 Przykładowy przebieg deployment

```
🚀 ZERO-DOWNTIME DEPLOYMENT
=====================================

📋 Konfiguracja:
   Środowisko: dev
   Compose file: docker-compose.dev.yml
   Nowy tag: nc-app:new-20250107-143022
   Stary tag: nc-app:current

🔍 Sprawdzam działające kontenery...
✅ Znaleziono działające kontenery - będą działać podczas budowania

🔨 Buduję NOWY obraz (stary nadal działa)...
   To może potrwać kilka minut...
[... build output ...]
✅ Nowy obraz zbudowany w 45.32 sekund

💾 Tworzę backup starego obrazu...
✅ Backup utworzony: nc-app:backup-20250107-143022

🏷️  Oznaczam nowy obraz jako current...
✅ Nowy obraz oznaczony jako: nc-app:current

🔄 Przełączam na nowy obraz (restart kontenerów)...
   Maksymalny downtime: ~2-5 sekund
✅ Przełączono na nowy obraz w 3.45 sekund

🏥 Sprawdzam health status...
✅ Health check passed!

📊 Status kontenerów:
NAME                       STATUS              PORTS
nc_project-web-1          Up 5 seconds        0.0.0.0:8000->8000/tcp
nc_project-celery-1       Up 5 seconds        
nc_project-redis-1        Up 5 seconds        

🎉 DEPLOYMENT ZAKOŃCZONY POMYŚLNIE!
=====================================

📈 Statystyki:
   Czas budowania: 45.32s
   Czas przełączenia: 3.45s
   Całkowity czas: 48.77s
   Downtime: ~3.45s

💡 Backup obrazu dostępny jako: nc-app:backup-20250107-143022
```

## 🔧 Konfiguracja

### Wymagania
- Docker Engine 18.09+ (BuildKit support)
- Docker Compose 1.25+
- Bash (Linux/Mac) lub PowerShell (Windows)

### Opcje środowiska
- `dev` - Development (docker-compose.dev.yml + Dockerfile)
- `prod` - Production (docker-compose.yml + Dockerfile.prod)

## 📝 Szczegóły techniczne

### Tagowanie obrazów

#### Nowy obraz podczas budowania:
```
nc-app:new-20250107-143022
```

#### Aktualnie używany obraz:
```
nc-app:current
```

#### Backup starych obrazów:
```
nc-app:backup-20250107-143022
nc-app:backup-20250106-091234
nc-app:backup-20250105-184512
```

### Proces przełączania

1. **Stop kontenerów**
   ```bash
   docker-compose stop
   ```

2. **Remove kontenerów** (volumes pozostają!)
   ```bash
   docker-compose rm -f
   ```

3. **Start nowych kontenerów**
   ```bash
   docker-compose up -d
   ```

### Health check

Skrypt sprawdza:
- Status kontenerów (Up/Exit/Unhealthy)
- Maksymalnie 12 prób co 5 sekund (60s total)
- Automatyczny rollback jeśli fail

### Cleanup

Automatycznie:
- Usuwa tymczasowe pliki
- Zachowuje 3 ostatnie obrazy
- Usuwa starsze obrazy

## 🎯 Porównanie z tradycyjnym deploy

### Tradycyjny deploy:
```
1. docker-compose down          [30s downtime]
2. docker-compose build         [5-10 minut downtime]
3. docker-compose up -d         [30s downtime]

Total downtime: 6-11 MINUT ❌
```

### Zero-downtime deploy:
```
1. Build w tle (aplikacja działa)  [0s downtime]
2. Szybkie przełączenie             [2-5s downtime]
3. Health check lub rollback        [0s downtime]

Total downtime: 2-5 SEKUND ✅
```

### Oszczędność:
```
PRZED: 6-11 minut downtime
PO: 2-5 sekund downtime
POPRAWA: 99.9% mniej downtime! 🎉
```

## 🔙 Rollback

### Automatyczny rollback
Jeśli health check nie przejdzie, skrypt automatycznie:
1. Wykrywa problem
2. Przywraca backup
3. Restartuje kontenery ze starym obrazem

### Manualny rollback
```powershell
# Windows
./scripts/deploy/deploy-blue-green.sh rollback

# Linux/Mac
./scripts/deploy/deploy-blue-green.sh rollback
```

Rollback pozwala wybrać dowolny backup:
```
📦 Dostępne backupy:
   1) nc-app:backup-20250107-143022
   2) nc-app:backup-20250106-091234
   3) nc-app:backup-20250105-184512

Wybierz numer backupu (Enter = najnowszy):
```

## 🛡️ Bezpieczeństwo

### Zachowane dane
- ✅ Volumes (bazy danych, pliki)
- ✅ Konfiguracja (.env files)
- ✅ Logi

### Backup
- ✅ Automatyczny backup przed deployment
- ✅ Zachowywane 3 ostatnie wersje
- ✅ Możliwość powrotu do dowolnej wersji

## 💡 Best Practices

### 1. Testuj przed deploymentem
```bash
# Uruchom testy w CI/CD przed wywołaniem skryptu
python manage.py test
```

### 2. Monitoruj deployment
- Sprawdź logi po deployment: `docker-compose logs -f`
- Monitoruj metryki w Flower: http://localhost:5555
- Sprawdź health endpoints

### 3. Regularnie czyść stare obrazy
```bash
# Skrypt automatycznie zachowuje 3 ostatnie
# Możesz ręcznie wyczyścić jeszcze starsze:
docker image prune -a
```

### 4. Backup przed dużymi zmianami
```bash
# Przed dużymi zmianami zrób dodatkowy backup
docker tag nc-app:current nc-app:pre-major-change
```

## 🐛 Troubleshooting

### Problem: Build trwa zbyt długo
**Rozwiązanie:** Upewnij się że BuildKit jest włączony
```powershell
$env:DOCKER_BUILDKIT = "1"
```

### Problem: Health check zawsze failuje
**Rozwiązanie:** Sprawdź logi kontenerów
```bash
docker-compose logs web
```

### Problem: Nie ma backupów do rollback
**Rozwiązanie:** Pierwszy deployment nie ma backupu - to normalne

### Problem: Containers nie startują
**Rozwiązanie:** Sprawdź zasoby systemowe
```bash
docker system df
docker stats
```

## 📚 Powiązane dokumenty

- [BUILD_OPTIMIZATION.md](BUILD_OPTIMIZATION.md) - Optymalizacja buildów
- [DEPLOY_FIX_INSTRUCTIONS.md](DEPLOY_FIX_INSTRUCTIONS.md) - Instrukcje deployment
- [docker-compose.dev.yml](docker-compose.dev.yml) - Konfiguracja development
- [docker-compose.yml](docker-compose.yml) - Konfiguracja production

## 🎓 Jak to działa pod spodem?

### Blue-Green Deployment Pattern

To jest implementacja **Blue-Green Deployment**:
- **Blue** (Stary) - Aktualnie działająca wersja
- **Green** (Nowy) - Nowa wersja budowana w tle
- **Switch** - Szybkie przełączenie ruchu z Blue na Green
- **Rollback** - W razie problemu wracamy do Blue

### Dlaczego to działa?

1. **Docker image layers** - warstwy są cache'owane
2. **BuildKit cache mounts** - pakiety są cache'owane między buildami
3. **Docker tags** - pozwalają na szybkie przełączanie między obrazami
4. **Docker Compose** - zarządza orkiestracją kontenerów

### Alternatywy

Inne podejścia do zero-downtime:
- **Rolling updates** (Kubernetes) - stopniowa wymiana podów
- **Canary deployment** - stopniowe przekierowanie ruchu
- **A/B testing** - ruch rozdzielony między wersje
- **Feature flags** - włączanie funkcji bez deployment

Nasz system to uproszczona wersja idealna dla:
- ✅ Małe/średnie projekty
- ✅ Docker Compose setup
- ✅ Single server deployment
- ✅ Development i staging

Dla dużych projektów rozważ:
- Kubernetes (rolling updates built-in)
- Docker Swarm
- AWS ECS/EKS
- Cloud-native solutions

## 🌟 Podsumowanie

Zero-downtime deployment daje Ci:
- 🚀 **Szybkie deploymenty** - kilka sekund downtime
- 🛡️ **Bezpieczeństwo** - automatyczny rollback
- 💾 **Backup** - łatwy powrót do poprzednich wersji
- ⚡ **Wydajność** - BuildKit cache dla szybkich buildów
- 😊 **Wygoda** - jeden skrypt robi wszystko

Wypróbuj teraz:
```powershell
.\deploy-zero-downtime.ps1 -Environment dev
```

