# Celery Security Guide

## ✅ Naprawiono problem z uruchamianiem jako root

### Zmiany w konfiguracji:

#### 1. Dockerfile
- Utworzono użytkownika `celery` z UID/GID 1001
- Ustawiono właściciela plików na `celery:celery`
- Przełączono na użytkownika `celery` na końcu Dockerfile

#### 2. docker-compose.yml (produkcja)
- Usunięto `C_FORCE_ROOT=true` ze wszystkich serwisów Celery
- Dodano `--uid=1001 --gid=1001` do komend Celery
- Dodano `user: "1001:1001"` do wszystkich serwisów Celery

#### 3. docker-compose.dev.yml (development)
- Usunięto `C_FORCE_ROOT=true` ze wszystkich serwisów Celery
- Dodano `--uid=1001 --gid=1001` do komend Celery
- Dodano `user: "1001:1001"` do wszystkich serwisów Celery

## 🔒 Bezpieczeństwo użytkownika

### Użytkownik Celery:
- **Nazwa**: `celery`
- **UID**: `1001`
- **GID**: `1001`
- **Typ**: System user (nie ma shell)
- **Uprawnienia**: Tylko do katalogów aplikacji

### Katalogi z uprawnieniami:
- `/app` - katalog aplikacji
- `/var/lib/celery` - dane Celery
- `/app/logs` - logi aplikacji
- `/app/staticfiles` - pliki statyczne

## 🚀 Jak uruchomić z nową konfiguracją

### 1. Przebuduj obrazy Docker
```bash
# W produkcji
docker-compose build

# W development
docker-compose -f docker-compose.dev.yml build
```

### 2. Uruchom serwisy
```bash
# W produkcji
docker-compose up -d

# W development
docker-compose -f docker-compose.dev.yml up -d
```

### 3. Sprawdź logi
```bash
# Sprawdź logi Celery worker
docker-compose logs celery-default

# Sprawdź logi Celery beat
docker-compose logs celery-beat

# Sprawdź logi Flower
docker-compose logs flower
```

## 🧪 Testowanie bezpieczeństwa

### Uruchom test bezpieczeństwa:
```bash
python3 celery-security-test.py
```

### Test sprawdza:
- ✅ Czy procesy Celery nie działają jako root
- ✅ Czy połączenie z Celery działa
- ✅ Czy taski są wykonywane poprawnie
- ✅ Czy kontenery Docker działają

## 📊 Monitoring

### Sprawdź procesy Celery:
```bash
# Sprawdź procesy w kontenerze
docker-compose exec celery-default ps aux

# Sprawdź użytkownika procesu
docker-compose exec celery-default whoami

# Sprawdź UID/GID
docker-compose exec celery-default id
```

### Sprawdź logi bezpieczeństwa:
```bash
# Sprawdź logi Celery
docker-compose logs celery-default | grep -i "security\|warning\|error"

# Sprawdź logi systemowe
docker-compose exec celery-default dmesg | grep -i "security"
```

## ⚠️ Rozwiązywanie problemów

### Problem: "Permission denied"
```bash
# Sprawdź uprawnienia katalogów
docker-compose exec celery-default ls -la /app
docker-compose exec celery-default ls -la /var/lib/celery

# Napraw uprawnienia
docker-compose exec celery-default chown -R celery:celery /app
docker-compose exec celery-default chown -R celery:celery /var/lib/celery
```

### Problem: "Worker nie startuje"
```bash
# Sprawdź logi
docker-compose logs celery-default

# Sprawdź konfigurację
docker-compose exec celery-default celery -A nc.celery inspect stats
```

### Problem: "Brak uprawnień do plików"
```bash
# Sprawdź właściciela plików
docker-compose exec celery-default ls -la /app/staticfiles

# Napraw uprawnienia
docker-compose exec celery-default chown -R celery:celery /app/staticfiles
```

## 🔧 Konfiguracja zaawansowana

### Dodatkowe zabezpieczenia:

#### 1. Ograniczenie uprawnień użytkownika
```dockerfile
# W Dockerfile
RUN usermod -s /bin/false celery  # Wyłącz shell
RUN usermod -L celery             # Zablokuj konto
```

#### 2. Ograniczenie zasobów
```yaml
# W docker-compose.yml
services:
  celery-default:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

#### 3. Read-only filesystem
```yaml
# W docker-compose.yml
services:
  celery-default:
    read_only: true
    tmpfs:
      - /tmp
      - /var/lib/celery
```

## 📝 Checklist bezpieczeństwa

### Przed wdrożeniem:
- [ ] Obrazy Docker przebudowane
- [ ] Test bezpieczeństwa przeszedł
- [ ] Logi nie zawierają ostrzeżeń o root
- [ ] Taski Celery działają poprawnie
- [ ] Flower dostępny i działa
- [ ] Uprawnienia plików poprawne

### Po wdrożeniu:
- [ ] Monitorowanie procesów Celery
- [ ] Sprawdzanie logów bezpieczeństwa
- [ ] Testowanie tasków
- [ ] Sprawdzanie wydajności
- [ ] Backup konfiguracji

## 🚨 Alerty bezpieczeństwa

### Sygnały ostrzegawcze:
- Procesy Celery działające jako root
- Błędy uprawnień w logach
- Nieudane uruchomienia workerów
- Problemy z dostępem do plików
- Wysokie użycie zasobów

### Automatyczne monitorowanie:
```bash
# Skrypt monitorujący
#!/bin/bash
while true; do
    if docker-compose exec celery-default ps aux | grep -q "root.*celery"; then
        echo "ALERT: Celery worker działa jako root!"
        # Wyślij alert
    fi
    sleep 60
done
```

## 📚 Dokumentacja

### Przydatne linki:
- [Celery Security](https://docs.celeryproject.org/en/stable/userguide/security.html)
- [Docker Security](https://docs.docker.com/engine/security/)
- [Linux User Management](https://www.cyberciti.biz/faq/understanding-etcpasswd-file-format/)

### Komendy diagnostyczne:
```bash
# Sprawdź konfigurację Celery
docker-compose exec celery-default celery -A nc.celery inspect config

# Sprawdź aktywnych workerów
docker-compose exec celery-default celery -A nc.celery inspect active

# Sprawdź statystyki
docker-compose exec celery-default celery -A nc.celery inspect stats
```

