# Redis Security Checklist

## ✅ Zaimplementowane zabezpieczenia

### 1. Konfiguracja Redis (redis.conf)
- [x] `bind 127.0.0.1` - Redis nasłuchuje tylko lokalnie
- [x] `protected-mode yes` - Włączony tryb chroniony
- [x] `requirepass` - Wymagane hasło
- [x] Wyłączone niebezpieczne komendy:
  - `FLUSHDB`, `FLUSHALL` - czyszczenie bazy
  - `KEYS` - wyszukiwanie kluczy
  - `CONFIG` - zmiana konfiguracji
  - `SHUTDOWN` - wyłączenie serwera
  - `DEBUG` - tryb debugowania
  - `EVAL`, `SCRIPT` - wykonywanie skryptów Lua
- [x] `maxclients 100` - ograniczenie liczby klientów
- [x] `timeout 300` - timeout połączeń
- [x] `slowlog` - logowanie wolnych zapytań

### 2. Docker Network Security
- [x] Usunięty publiczny port 6379 w produkcji
- [x] Redis dostępny tylko wewnątrz sieci Docker
- [x] W development: `127.0.0.1:6379:6379` - tylko lokalnie
- [x] Użycie pliku konfiguracyjnego Redis

### 3. Monitoring i Logowanie
- [x] `scripts/monitoring/redis-security-monitor.py` - monitor bezpieczeństwa
- [x] Logowanie wolnych zapytań
- [x] Monitorowanie połączeń klientów
- [x] Wykrywanie ataków brute force
- [x] Raporty bezpieczeństwa

### 4. Firewall Rules
- [x] `scripts/security/redis-firewall-rules.sh` - skrypt konfiguracji firewall
- [x] Blokada portu 6379 dla zewnętrznych połączeń
- [x] Rate limiting dla SSH
- [x] Zezwolenie tylko na potrzebne porty

## 🔒 Dodatkowe zalecenia

### 1. Silne hasła
```bash
# Generuj silne hasło
openssl rand -base64 32

# Ustaw w .env.prod
REDIS_PASSWORD=twoje_bardzo_silne_haslo_32_znaki
```

### 2. SSL/TLS (opcjonalnie)
```bash
# Generuj certyfikaty
openssl req -x509 -newkey rsa:4096 -keyout redis.key -out redis.crt -days 365 -nodes

# Dodaj do redis.conf
tls-port 6380
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
```

### 3. Redis ACL (Redis 6+)
```bash
# Utwórz użytkownika z ograniczonymi uprawnieniami
ACL SETUSER celery_user on >password +@read +@write +@list +@set +@hash +@string -@dangerous
```

### 4. Monitoring zewnętrzny
- [ ] Integracja z Prometheus/Grafana
- [ ] Alerty w przypadku ataków
- [ ] Logowanie do centralnego systemu

### 5. Backup i Recovery
- [ ] Automatyczne kopie zapasowe RDB
- [ ] Testowanie przywracania
- [ ] Szyfrowanie kopii zapasowych

## 🚨 Wykrywanie ataków

### Typowe ataki na Redis:
1. **Brute Force** - wielokrotne próby logowania
2. **Command Injection** - wykonywanie niebezpiecznych komend
3. **Memory Exhaustion** - wyczerpanie pamięci
4. **Slow Query** - wolne zapytania DoS
5. **Unauthorized Access** - nieautoryzowany dostęp

### Sygnały ostrzegawcze:
- Wiele nieudanych prób logowania
- Wolne zapytania (>10ms)
- Wysokie użycie pamięci (>90%)
- Podejrzane połączenia
- Nieoczekiwane komendy

## 📊 Monitoring Commands

```bash
# Sprawdź połączenia
redis-cli -a password CLIENT LIST

# Sprawdź wolne zapytania
redis-cli -a password SLOWLOG GET 10

# Sprawdź użycie pamięci
redis-cli -a password INFO memory

# Sprawdź konfigurację
redis-cli -a password CONFIG GET "*"

# Sprawdź logi
tail -f logs/redis-security.log
```

## 🔧 Uruchomienie monitora

```bash
# Uruchom monitor bezpieczeństwa
python3 scripts/monitoring/redis-security-monitor.py

# Uruchom w tle
nohup python3 scripts/monitoring/redis-security-monitor.py > redis-monitor.log 2>&1 &

# Sprawdź status
ps aux | grep redis-security-monitor
```

## 📝 Regularne audyty

### Codziennie:
- [ ] Sprawdź logi bezpieczeństwa
- [ ] Sprawdź połączenia klientów
- [ ] Sprawdź użycie pamięci

### Tygodniowo:
- [ ] Przejrzyj raporty bezpieczeństwa
- [ ] Sprawdź konfigurację
- [ ] Zaktualizuj hasła

### Miesięcznie:
- [ ] Pełny audit bezpieczeństwa
- [ ] Test penetracyjny
- [ ] Aktualizacja dokumentacji

