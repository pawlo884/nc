# Nginx Security Guide

## Przegląd

Ten przewodnik opisuje zabezpieczenia nginx zaimplementowane w projekcie NC, które chronią przed typowymi atakami i nieprawidłowymi żądaniami HTTP.

## Problem

W logach nginx pojawiały się błędy:
```
2025/10/04 13:54:11 [info] 30#30: *418 client sent invalid request while reading client request line, client: 172.18.0.1, server: _, request: "CONNECT www.shadowserver.org:443⁠ HTTP/1.1"
```

To typowe próby ataków lub skanowania portów, które nginx powinien blokować.

## Rozwiązanie

### 1. Konfiguracja nginx.conf

#### Rate Limiting
```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=static:10m rate=30r/s;
```

#### Blokowanie podejrzanych metod HTTP
```nginx
# Map for blocking suspicious requests
map $request_method $blocked_method {
    default 0;
    CONNECT 1;
    TRACE 1;
    OPTIONS 1;
}
```

#### Zabezpieczenia
- **Security headers**: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- **Blokowanie path traversal**: `(\.\./|\.\.\\|\.\.%2f|\.\.%5c)`
- **Blokowanie żądań do portów**: `:\d+$`
- **Ochrona plików wrażliwych**: `.env`, `.log`, `.conf`

### 2. Monitoring bezpieczeństwa

#### nginx_monitor.py
Skrypt monitorujący logi nginx w czasie rzeczywistym:

```bash
# Analiza ostatnich 1000 linii
python3 nginx_monitor.py --log-file /var/log/nginx/access.log --lines 1000

# Monitoring w czasie rzeczywistym
python3 nginx_monitor.py --realtime
```

#### Funkcje monitora:
- **Wykrywanie podejrzanych żądań**: CONNECT, TRACE, OPTIONS, path traversal, XSS, SQL injection
- **Rate limiting**: Automatyczne blokowanie IP przekraczających limity
- **Raportowanie**: Statystyki IP, podejrzane żądania, wskaźniki błędów
- **Automatyczne blokowanie**: IP z wysokim wskaźnikiem ataków

### 3. Automatyzacja

#### nginx_security_setup.sh
Skrypt konfigurujący nginx z zabezpieczeniami:

```bash
# Uruchomienie setup
./nginx_security_setup.sh
```

#### Funkcje setup:
- Konfiguracja rate limiting
- Utworzenie katalogów logów
- Konfiguracja cron jobs
- Ustawienie logrotate
- Automatyczne blokowanie IP

### 4. Docker Integration

#### Dockerfile
- Instalacja nginx, cron, iptables
- Konfiguracja uprawnień
- Kopiowanie skryptów bezpieczeństwa

#### docker-compose.yml
- Nginx z zabezpieczeniami
- Automatyczne uruchomienie monitora
- Volumes dla logów i konfiguracji

## Konfiguracja

### Rate Limits
- **API**: 10 żądań/sekundę (burst: 20)
- **Static files**: 30 żądań/sekundę (burst: 50)
- **Login**: 5 żądań/minutę

### Blokowane wzorce
- `CONNECT` requests (proxy tunneling)
- `TRACE` requests (XSS attacks)
- `OPTIONS` requests (reconnaissance)
- Path traversal: `../`, `..\\`, `..%2f`, `..%5c`
- XSS attempts: `<script`
- SQL injection: `union select`, `drop table`
- Command injection: `exec(`, `eval(`

### Monitoring
- **Real-time**: Analiza nowych żądań
- **Batch**: Analiza ostatnich N linii
- **Cron**: Automatyczne raporty co 5 minut
- **Logrotate**: Rotacja logów co 30 dni

## Użycie

### 1. Uruchomienie z zabezpieczeniami
```bash
# Development
docker-compose -f docker-compose.dev.yml up nginx

# Production
docker-compose up nginx
```

### 2. Monitoring
```bash
# Sprawdź logi bezpieczeństwa
tail -f /var/log/nginx/security.log

# Uruchom monitor ręcznie
python3 nginx_monitor.py --realtime
```

### 3. Blokowanie IP
```bash
# Zablokuj IP
/usr/local/bin/nginx_block_ip.sh 192.168.1.100 "Suspicious activity"

# Sprawdź zablokowane IP
cat /etc/nginx/conf.d/security/blocked_ips.conf
```

## Logi

### Lokalizacje logów
- **Access log**: `/var/log/nginx/access.log`
- **Error log**: `/var/log/nginx/error.log`
- **Security log**: `/var/log/nginx/security.log`
- **Monitor log**: `logs/nginx_security.log`

### Przykłady logów
```
2025-10-04 13:54:11 - WARNING - Suspicious request from 172.18.0.1: CONNECT www.shadowserver.org:443 HTTP/1.1 - Pattern: CONNECT\s+\w+:\d+
2025-10-04 13:54:11 - WARNING - BLOCKING IP: 172.18.0.1 - Reason: Rate limit exceeded
```

## Troubleshooting

### 1. Nginx nie startuje
```bash
# Sprawdź konfigurację
nginx -t

# Sprawdź logi
tail -f /var/log/nginx/error.log
```

### 2. Monitor nie działa
```bash
# Sprawdź uprawnienia
ls -la nginx_monitor.py

# Uruchom z debug
python3 nginx_monitor.py --log-file /var/log/nginx/access.log --lines 100
```

### 3. Zbyt wiele blokowanych IP
```bash
# Wyczyść zablokowane IP
echo "" > /etc/nginx/conf.d/security/blocked_ips.conf
nginx -s reload
```

## Bezpieczeństwo

### Zalecenia
1. **Regularne monitorowanie** logów bezpieczeństwa
2. **Aktualizacja** wzorców ataków
3. **Backup** konfiguracji nginx
4. **Testowanie** nowych reguł przed wdrożeniem

### Uwagi
- Rate limiting może wpływać na legalnych użytkowników
- Automatyczne blokowanie może być zbyt agresywne
- Monitorowanie w czasie rzeczywistym zużywa zasoby

## Podsumowanie

Nowa konfiguracja nginx zapewnia:
- ✅ Blokowanie podejrzanych żądań HTTP
- ✅ Rate limiting dla ochrony przed DDoS
- ✅ Monitoring bezpieczeństwa w czasie rzeczywistym
- ✅ Automatyczne blokowanie atakujących IP
- ✅ Szczegółowe logowanie i raportowanie
- ✅ Integracja z Docker i Docker Compose

Błędy typu "client sent invalid request" powinny być teraz blokowane na poziomie nginx, a podejrzane IP automatycznie blokowane.
