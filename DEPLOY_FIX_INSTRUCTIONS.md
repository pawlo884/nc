# 🚀 Instrukcje Naprawy Błędu Cache Docker w Deploy

## ❌ **Problem**
```
ERROR: failed to build: failed to solve: failed to compute cache key: failed to calculate checksum of ref fzwupeph1wj4vrb6m6ua470he::jvqnx17le0qgu9b0uxyjlqlcl: "/||": not found
```

## ✅ **Rozwiązania**

### **Rozwiązanie 1: Użyj Dockerfile.simple**

Zamień `Dockerfile` na `Dockerfile.simple`:

```bash
# W platformie deploy:
# 1. Zmień nazwę pliku
mv Dockerfile Dockerfile.old
mv Dockerfile.simple Dockerfile

# 2. Zbuduj bez cache
docker build --no-cache -t your-app .
```

### **Rozwiązanie 2: Wyczyść Cache w Platformie Deploy**

#### **Render:**
1. Idź do ustawień aplikacji
2. Wyłącz "Docker Layer Caching"
3. Zrestartuj deploy

#### **Railway:**
1. W ustawieniach projektu wyłącz cache
2. Lub dodaj do build command: `--no-cache`

#### **DigitalOcean App Platform:**
1. Wyłącz "Build Cache" w ustawieniach
2. Lub usuń i stwórz nową aplikację

#### **Heroku:**
1. Dodaj do `app.json`:
```json
{
  "buildpacks": [
    {
      "url": "heroku/python"
    }
  ],
  "stack": "heroku-22"
}
```

### **Rozwiązanie 3: Użyj docker-compose.yml z no_cache**

Jeśli używasz docker-compose, użyj zaktualizowanego pliku:

```bash
# Zbuduj bez cache
docker-compose build --no-cache

# Uruchom
docker-compose up -d
```

### **Rozwiązanie 4: Zmień Strategię Build**

#### **Opcja A: Build lokalnie i push**
```bash
# Lokalnie:
docker build --no-cache -t your-username/your-app:latest .
docker push your-username/your-app:latest

# W deploy użyj gotowego obrazu
```

#### **Opcja B: Użyj GitHub Actions**
Stwórz `.github/workflows/build.yml`:
```yaml
name: Build and Deploy
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: |
          docker build --no-cache -t your-app .
          docker tag your-app your-registry/your-app:latest
          docker push your-registry/your-app:latest
```

### **Rozwiązanie 5: Zmień Platformę Deploy**

Jeśli problem nadal występuje, rozważ:

1. **Railway** - ma lepsze zarządzanie cache
2. **Render** - z wyłączonym cache
3. **DigitalOcean App Platform** - z custom build
4. **AWS ECS** - z własnym pipeline

## 🔧 **Dodatkowe Kroki**

### **1. Sprawdź .dockerignore**
Upewnij się, że `.dockerignore` nie blokuje ważnych plików:
```dockerignore
# Nie blokuj tych plików:
!requirements.txt
!manage.py
!nc/
!matterhorn/
!matterhorn1/
!MPD/
!web_agent/
!static/
!nginx.conf
!redis.conf
!docker-entrypoint.sh
```

### **2. Sprawdź Zmienne Środowiskowe**
W platformie deploy ustaw:
```bash
DOCKER_BUILDKIT=0
COMPOSE_DOCKER_CLI_BUILD=0
```

### **3. Użyj Starszego BuildKit**
W Dockerfile dodaj na początku:
```dockerfile
# syntax=docker/dockerfile:1.4
```

## 🎯 **Rekomendowane Rozwiązanie**

**Najszybsze rozwiązanie:**
1. Użyj `Dockerfile.simple`
2. Wyłącz cache w platformie deploy
3. Zbuduj z `--no-cache`

**Długoterminowe rozwiązanie:**
1. Przejdź na GitHub Actions do budowania obrazów
2. Użyj gotowych obrazów w deploy
3. Zaimplementuj CI/CD pipeline

## 📞 **Jeśli Nic Nie Pomaga**

1. **Usuń aplikację** i stwórz nową w platformie deploy
2. **Zmień nazwę obrazu** Docker
3. **Użyj innej platformy** deploy
4. **Skontaktuj się z supportem** platformy

---

**Status**: ✅ Gotowe do implementacji
**Czas**: 5-10 minut
**Trudność**: Łatwa
