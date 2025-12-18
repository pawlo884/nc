# 📜 Przewodnik po skryptach projektu

## 🎯 Główne skrypty deployment

### 🚀 Production (GitHub Actions)
```bash
deploy-from-registry.sh
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
./build-fast.sh

# Windows
.\build-fast.ps1
```
**Używany przez:** Developer lokalnie  
**Kiedy:** Po zmianach w kodzie/requirements.txt  
**Co robi:** Szybki build z cache (30s-1min)  

**Przykład:**
```bash
# Zmieniłeś requirements.txt?
.\build-fast.ps1
docker-compose -f docker-compose.dev.yml up -d --force-recreate
```

---

## 🔙 Rollback

### Na serwerze (przez SSH)
```bash
rollback.sh
```
**Używany przez:** Ręcznie na serwerze lub przez GitHub Actions  
**Kiedy:** Gdy deployment się nie powiódł  
**Co robi:** Przywraca poprzednią wersję z backupu

**Przykład:**
```bash
ssh user@server
cd /srv/app
bash rollback.sh
```

---

## 🔧 Utility Scripts

### Build od zera (troubleshooting)
```bash
build-no-cache.sh
```
**Kiedy:** Gdy cache się zepsuł lub potrzebujesz czystego buildu  
**Downside:** Trwa ~10 minut (pobiera wszystko od nowa)

**Przykład:**
```bash
# Coś nie działa? Spróbuj rebuildu bez cache
./build-no-cache.sh
```

---

### Monitoring
```bash
monitor.sh
```
**Co robi:** Monitoruje zasoby systemowe i kontenery  
**Przykład:**
```bash
./monitor.sh
# Pokazuje CPU, memory, disk dla kontenerów
```

---

### Security Setup
```bash
nginx_security_setup.sh
redis-firewall-rules.sh
```
**Kiedy:** Setup produkcji, konfiguracja security  
**Co robią:**
- `nginx_security_setup.sh` - konfiguruje Nginx security headers
- `redis-firewall-rules.sh` - ustawia firewall dla Redis

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
- ~~`deploy-zero-downtime.sh`~~ → zastąpiony przez `deploy-from-registry.sh`
- ~~`deploy-zero-downtime.ps1`~~ → używamy GitHub Actions
- ~~`rollback.ps1`~~ → używamy GitHub Actions lub `rollback.sh` na serwerze
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
.\build-fast.ps1
docker-compose -f docker-compose.dev.yml up -d --force-recreate

# ===== PRODUCTION =====
# Deployment
git push origin main
# → GitHub Actions robi resztę automatycznie!

# Rollback (jeśli coś poszło nie tak)
ssh user@server
cd /srv/app
bash rollback.sh

# ===== TROUBLESHOOTING =====
# Build nie działa? Spróbuj bez cache
./build-no-cache.sh

# Sprawdź zasoby
./monitor.sh
```

---

## 🗂️ Struktura plików po cleanup

```
nc_project/
├── 🚀 DEPLOYMENT
│   ├── deploy-from-registry.sh    # GitHub Actions (production)
│   ├── rollback.sh                # Rollback na serwerze
│   └── .github/workflows/
│       └── deploy.yml             # Automatyczny workflow
│
├── 💻 DEVELOPMENT  
│   ├── build-fast.sh              # Szybki build (Linux/Mac)
│   ├── build-fast.ps1             # Szybki build (Windows)
│   └── docker-compose.dev.yml     # Dev environment
│
├── 🔧 UTILITIES
│   ├── build-no-cache.sh          # Full rebuild (troubleshooting)
│   ├── monitor.sh                 # System monitoring
│   ├── nginx_security_setup.sh    # Nginx security
│   ├── redis-firewall-rules.sh    # Redis security
│   ├── scripts/test_nginx_dev.sh  # Nginx testing (Linux)
│   └── scripts/test_nginx_dev.ps1 # Nginx testing (Windows)
│
├── 🐳 DOCKER
│   ├── docker-entrypoint.sh       # Container entrypoint
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
A: SSH na serwer → `bash rollback.sh` lub GitHub Actions zrobi automatycznie jeśli fail.

**Q: Zmieniłem requirements.txt - co robić?**  
A: `.\build-fast.ps1` + `docker-compose up -d --force-recreate`

**Q: Build trwa wieki, co robić?**  
A: Sprawdź czy używasz `build-fast.ps1` (z cache), nie `build-no-cache.sh`

**Q: Skąd wiem czy używam cache?**  
A: `build-fast.ps1` = z cache (szybki), `build-no-cache.sh` = bez cache (wolny)

**Q: Gdzie są stare skrypty deploy-zero-downtime?**  
A: Usunięte - zastąpione przez `deploy-from-registry.sh` (lepszy dla Docker Hub)

---

## 🎓 Więcej informacji

- **Dla developerów:** [QUICK_START.md](QUICK_START.md)
- **Dla deployment:** [GITHUB_AUTO_DEPLOY.md](GITHUB_AUTO_DEPLOY.md)
- **Dla optymalizacji:** [BUILD_OPTIMIZATION.md](BUILD_OPTIMIZATION.md)
- **Dla zero-downtime:** [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md)

---

## ✅ Checklist

Po cleanup powinieneś mieć:

- [x] `deploy-from-registry.sh` - główny deployment
- [x] `build-fast.ps1` / `build-fast.sh` - dev builds
- [x] `rollback.sh` - rollback
- [x] `docker-entrypoint.sh` - Docker entrypoint
- [x] Utility scripts (monitor, security, testing)
- [x] Brak starych/zduplikowanych skryptów

**Wszystko uporządkowane! 🎉**

