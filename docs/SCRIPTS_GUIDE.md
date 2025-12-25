# 📜 Przewodnik po skryptach projektu

## 🎯 Główne skrypty deployment

### 🚀 Production (GitHub Actions)
```bash
scripts/deploy/deploy-blue-green.sh
```
**Używany przez:** GitHub Actions na serwerze  
**Kiedy:** Automatycznie po `git push origin main`  
**Co robi:** Zero-downtime deployment z Docker Hub  
**Downtime:** 3-5 sekund

**Nie uruchamiaj ręcznie** - GitHub Actions robi to automatycznie!

---

### 💻 Development (lokalne)
```bash
# Linux/Mac
./scripts/build/build-fast.sh

# Windows
.\scripts\build\build-fast.ps1
```
**Używany przez:** Developer lokalnie  
**Kiedy:** Po zmianach w kodzie/requirements.txt  
**Co robi:** Szybki build z cache (30s-1min)  

**Przykład:**
```bash
# Zmieniłeś requirements.txt?
.\scripts\build\build-fast.ps1
docker-compose -f docker-compose.dev.yml up -d --force-recreate
```

---

## 🔙 Rollback

### Na serwerze (przez SSH)
```bash
scripts/deploy/deploy-blue-green.sh rollback
```
**Używany przez:** Ręcznie na serwerze lub przez GitHub Actions  
**Kiedy:** Gdy deployment się nie powiódł  
**Co robi:** Przywraca poprzednią wersję z backupu

**Przykład:**
```bash
ssh user@server
cd /srv/app
./scripts/deploy/deploy-blue-green.sh rollback
```

---

## 🔧 Utility Scripts

### Build od zera (troubleshooting)
```bash
scripts/build/build-no-cache.sh
```
**Kiedy:** Gdy cache się zepsuł lub potrzebujesz czystego buildu  
**Downside:** Trwa ~10 minut (pobiera wszystko od nowa)

**Przykład:**
```bash
# Coś nie działa? Spróbuj rebuildu bez cache
./scripts/build/build-no-cache.sh
```

---

### Monitoring
```bash
scripts/monitoring/monitor.sh
```
**Co robi:** Monitoruje zasoby systemowe i kontenery  
**Przykład:**
```bash
./scripts/monitoring/monitor.sh
# Pokazuje CPU, memory, disk dla kontenerów
```

---

### Security Setup
```bash
scripts/security/nginx_security_setup.sh
scripts/security/redis-firewall-rules.sh
```
**Kiedy:** Setup produkcji, konfiguracja security  
**Co robią:**
- `scripts/security/nginx_security_setup.sh` - konfiguruje Nginx security headers
- `scripts/security/redis-firewall-rules.sh` - ustawia firewall dla Redis

---

### Testing
```bash
# Linux/Mac
scripts/test_nginx_dev.sh

# Windows  
scripts/test_nginx_dev.ps1
```
**Co robią:** Testują konfigurację Nginx w development

---

## 🚫 Usunięte (niepotrzebne)

✅ Usunięte podczas cleanup:
- ~~`deploy-zero-downtime.sh`~~ → zastąpiony przez `scripts/deploy/deploy-blue-green.sh`
- ~~`deploy-zero-downtime.ps1`~~ → używamy GitHub Actions
- ~~`rollback.ps1`~~ → używamy GitHub Actions lub `scripts/deploy/deploy-blue-green.sh rollback` na serwerze
- ~~`deploy.sh`~~ → stary menu skrypt
- ~~`deploy-smart.sh`~~ → stary
- ~~`deploy-force-rebuild.sh`~~ → stary

---

## 📋 Quick Reference

### Codzienne użycie:

```bash
# ===== DEVELOPMENT =====
# Zmiana kodu (auto-reload działa!)
# → Nic nie rób, Gunicorn przeładuje kod

# Zmiana requirements.txt
.\scripts\build\build-fast.ps1
docker-compose -f docker-compose.dev.yml up -d --force-recreate

# ===== PRODUCTION =====
# Deployment
git push origin main
# → GitHub Actions robi resztę automatycznie!

# Rollback (jeśli coś poszło nie tak)
ssh user@server
cd /srv/app
./scripts/deploy/deploy-blue-green.sh rollback

# ===== TROUBLESHOOTING =====
# Build nie działa? Spróbuj bez cache
./scripts/build/build-no-cache.sh

# Sprawdź zasoby
./scripts/monitoring/monitor.sh
```

---

## 🗂️ Struktura plików po cleanup

```
nc_project/
├── 🚀 DEPLOYMENT
│   ├── scripts/deploy/deploy-blue-green.sh       # Blue-green deploy + rollback
│   └── .github/workflows/
│       └── deploy.yml             # Automatyczny workflow
│
├── 💻 DEVELOPMENT  
│   ├── scripts/build/build-fast.sh              # Szybki build (Linux/Mac)
│   ├── scripts/build/build-fast.ps1             # Szybki build (Windows)
│   └── docker-compose.dev.yml     # Dev environment
│
├── 🔧 UTILITIES
│   ├── scripts/build/build-no-cache.sh          # Full rebuild (troubleshooting)
│   ├── scripts/monitoring/monitor.sh            # System monitoring
│   ├── scripts/security/nginx_security_setup.sh # Nginx security
│   ├── scripts/security/redis-firewall-rules.sh # Redis security
│   ├── scripts/test_nginx_dev.sh  # Nginx testing (Linux)
│   └── scripts/test_nginx_dev.ps1 # Nginx testing (Windows)
│
├── 🐳 DOCKER
│   ├── docker/docker-entrypoint.sh       # Container entrypoint
│   ├── Dockerfile                 # Dev dockerfile
│   ├── Dockerfile.prod            # Prod dockerfile
│   ├── docker-compose.yml         # Production
│   └── docker-compose.dev.yml     # Development
│
└── 📚 DOKUMENTACJA
    ├── SCRIPTS_GUIDE.md           # Ten plik
    ├── ZERO_DOWNTIME_DEPLOYMENT.md
    ├── BUILD_OPTIMIZATION.md
    ├── DEPLOYMENT_SCRIPTS.md
    ├── GITHUB_AUTO_DEPLOY.md
    ├── UPGRADE_NOTES.md
    └── QUICK_START.md
```

---

## ❓ FAQ

**Q: Który skrypt używać do deployment?**  
A: Żaden ręcznie! `git push origin main` → GitHub Actions robi automatycznie.

**Q: Jak zrobić rollback?**  
A: SSH na serwer → `./scripts/deploy/deploy-blue-green.sh rollback` lub GitHub Actions zrobi automatycznie jeśli fail.

**Q: Zmieniłem requirements.txt - co robić?**  
A: `.\scripts\build\build-fast.ps1` + `docker-compose up -d --force-recreate`

**Q: Build trwa wieki, co robić?**  
A: Sprawdź czy używasz `scripts/build/build-fast.ps1` (z cache), nie `scripts/build/build-no-cache.sh`

**Q: Skąd wiem czy używam cache?**  
A: `scripts/build/build-fast.ps1` = z cache (szybki), `scripts/build/build-no-cache.sh` = bez cache (wolny)

**Q: Gdzie są stare skrypty deploy-zero-downtime?**  
A: Usunięte - zastąpione przez `scripts/deploy/deploy-blue-green.sh` (prod działa tylko w trybie blue-green)

---

## 🎓 Więcej informacji

- **Dla developerów:** [QUICK_START.md](QUICK_START.md)
- **Dla deployment:** [GITHUB_AUTO_DEPLOY.md](GITHUB_AUTO_DEPLOY.md)
- **Dla optymalizacji:** [BUILD_OPTIMIZATION.md](BUILD_OPTIMIZATION.md)
- **Dla zero-downtime:** [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md)

---

## ✅ Checklist

Po cleanup powinieneś mieć:

- [x] `scripts/deploy/deploy-blue-green.sh` - główny deployment
- [x] `scripts/build/build-fast.ps1` / `scripts/build/build-fast.sh` - dev builds
- [x] `scripts/deploy/deploy-blue-green.sh rollback` - rollback
- [x] `docker/docker-entrypoint.sh` - Docker entrypoint
- [x] Utility scripts (monitor, security, testing)
- [x] Brak starych/zduplikowanych skryptów

**Wszystko uporządkowane! 🎉**

