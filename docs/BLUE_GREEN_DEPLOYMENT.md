# 🔵🟢 Blue-Green Deployment - Zero Downtime

## Czym jest Blue-Green Deployment?

Blue-Green deployment to strategia gdzie mamy **dwa identyczne środowiska produkcyjne**:
- 🔵 **BLUE** - jedno środowisko (np. aktualna wersja)
- 🟢 **GREEN** - drugie środowisko (np. nowa wersja)

W każdym momencie **tylko jedno** środowisko obsługuje ruch produkcyjny.

### Zalety:
- ✅ **Zero downtime** - aplikacja działa cały czas
- ✅ **Instant rollback** - wrócenie do starej wersji w 2 sekundy
- ✅ **Bezpieczne testy** - nowa wersja testowana przed przełączeniem ruchu
- ✅ **Redukcja ryzyka** - problemy wykrywane przed przełączeniem

## Architektura

```
                    ┌─────────────────┐
                    │  NGINX Router   │
                    │    (Switch)     │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
         ┌──────▼──────┐          ┌──────▼──────┐
         │   🔵 BLUE   │          │   🟢 GREEN  │
         │   web-blue  │          │  web-green  │
         │   (Active)  │          │  (Standby)  │
         └──────┬──────┘          └──────┬──────┘
                │                         │
                └────────────┬────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
       ┌──────▼──────┐              ┌──────▼──────┐
       │  PostgreSQL  │              │    Redis    │
       │  (Shared)    │              │  (Shared)   │
       └──────────────┘              └─────────────┘
```

### Komponenty:

**Duplikowane (Blue + Green):**
- `web-blue` / `web-green` - aplikacja Django
- Różne porty wewnętrzne

**Wspólne (Shared):**
- `postgres` - baza danych (jedna dla obu)
- `redis` - cache i Celery broker
- `celery-*` - workery (jedna instancja)
- `flower` - monitoring

**Postgres/Redis w innym stacku:** W `docker-compose.blue-green.yml` serwisy `postgres` i `redis` mają `profiles: ["shared"]`. Dzięki temu Compose **nie** uruchamia ani nie tworzy tych kontenerów przy zwykłym deployu – zakłada się, że działają już (np. w innym stacku). Skrypt deploy tylko sprawdza, że `nc-postgres-1` i `nc-redis-1` działają. Jeśli chcesz uruchomić postgres/redis z tego pliku: `docker-compose -f docker-compose.blue-green.yml --profile shared up -d postgres redis`.

**Router:**
- `nginx-router` - przełącza ruch między blue/green

## Instalacja

### 1. Skopiuj pliki

Masz już:
- ✅ `docker-compose.blue-green.yml` - konfiguracja Docker
- ✅ `nginx-blue-green.conf` - konfiguracja NGINX
- ✅ `scripts/deploy/deploy-blue-green.sh` - skrypt deployment

### 2. Utwórz katalog dla stanu NGINX

```bash
mkdir -p /mnt/data2tb/docker/volumes/nc_nginx_state
```

### 3. Pierwszy deploy

```bash
# Uruchom oba środowiska pierwszy raz
docker-compose -f docker-compose.blue-green.yml up -d

# Sprawdź status
./scripts/deploy/deploy-blue-green.sh status
```

## Użycie

### Deploy nowej wersji

```bash
# Podstawowy deploy
./scripts/deploy/deploy-blue-green.sh deploy
```

**Co się dzieje:**
1. 🔍 Sprawdza który environment jest aktywny (blue/green)
2. 🔨 Builduje nowy obraz dla nieaktywnego
3. ▶️  Uruchamia nowy kontener
4. 🏥 Wykonuje health check
5. 🔄 Przełącza NGINX na nowy environment
6. ⏳ Czeka 30s
7. 🛑 Zatrzymuje stary environment
8. ✅ Sukces!

### Status

```bash
./scripts/deploy/deploy-blue-green.sh status
```

**Output:**
```
==================================
BLUE-GREEN DEPLOYMENT STATUS
==================================

🔵 BLUE environment:
  Status: ✅ RUNNING
  Health: ✅ HEALTHY

🟢 GREEN environment:
  Status: ⭕ STOPPED

🔀 Active environment: blue
==================================
```

### Rollback (awaryjny powrót)

```bash
./scripts/deploy/deploy-blue-green.sh rollback
```

**Czas rollback: ~5 sekund** ⚡

## Integracja z GitHub Actions

### Opcja 1: Zastąp istniejący workflow

W `.github/workflows/deploy-vps.yml` zmień deploy na:

```yaml
- name: Blue-Green Deploy
  uses: appleboy/ssh-action@master
  with:
    host: ${{ secrets.VPS_HOST }}
    username: ${{ secrets.VPS_USER }}
    key: ${{ secrets.VPS_SSH_KEY }}
    script: |
      cd /home/pawel/apps/nc
      git pull origin main
      ./scripts/deploy/deploy-blue-green.sh deploy
```

### Opcja 2: Nowy workflow tylko dla blue-green

Utwórz `.github/workflows/deploy-blue-green.yml`:

```yaml
name: Deploy Blue-Green

on:
  workflow_dispatch:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /home/pawel/apps/nc
            git pull origin main
            
            # Deploy blue-green
            ./scripts/deploy/deploy-blue-green.sh deploy
            
            # Sprawdź status
            ./scripts/deploy/deploy-blue-green.sh status
```

## Monitoring

### Health checks

NGINX automatycznie sprawdza health każdego kontenera.

Endpoint Django dla health check (opcjonalnie dodaj):

```python
# nc/views.py
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'environment': os.getenv('DEPLOYMENT_COLOR', 'unknown')
    })

# nc/urls.py
urlpatterns = [
    path('health/', health_check, name='health'),
    # ... reszta
]
```

### Sprawdź aktywny environment

```bash
# W NGINX
curl http://localhost/deployment-status

# W aplikacji
curl http://localhost/health/
```

## Scenariusze

### Scenariusz 1: Normalny deploy

```bash
# 1. Deploy
./scripts/deploy/deploy-blue-green.sh deploy

# Output:
🚀 Rozpoczynam Blue-Green Deployment
==================================
🔵 Aktywny: BLUE → 🟢 Deploy na: GREEN
🔨 Budowanie nowego obrazu...
▶️  Uruchamianie nowego kontenera GREEN...
🏥 Health check dla green...
✅ green jest zdrowy!
🔄 Przełączanie NGINX na green...
✅ NGINX przełączony na green
⏳ Czekam 30s przed zatrzymaniem blue...
🛑 Zatrzymywanie starego środowiska blue...
🎉 Deployment zakończony pomyślnie!
```

### Scenariusz 2: Deploy z problemem (auto rollback)

```bash
./scripts/deploy/deploy-blue-green.sh deploy

# Output:
🚀 Rozpoczynam Blue-Green Deployment
🟢 Aktywny: GREEN → 🔵 Deploy na: BLUE
🔨 Budowanie nowego obrazu...
▶️  Uruchamianie nowego kontenera BLUE...
🏥 Health check dla blue...
❌ blue nie przeszedł health check!
❌ Deployment failed - health check nie przeszedł
🔙 Rollback: blue nie zostanie aktywowany
```

**Wynik:** GREEN dalej obsługuje ruch, zero downtime! ✅

### Scenariusz 3: Rollback po deploy

```bash
# Deploy przeszedł ale znalazłeś bug
./scripts/deploy/deploy-blue-green.sh rollback

# Output:
🔙 ROLLBACK - przywracanie poprzedniego environment
Rollback z green na blue...
🏥 Health check dla blue...
✅ blue jest zdrowy!
🔄 Przełączanie NGINX na blue...
✅ Rollback zakończony - aktywny: blue
```

**Czas: ~5 sekund** ⚡

## Zarządzanie zasobami

### Oba environments running = 2x RAM?

**TAK**, ale można zoptymalizować:

1. **Po deploy zatrzymaj stary** (domyślne):
   ```bash
   # W scripts/deploy/deploy-blue-green.sh już jest:
   docker-compose -f docker-compose.blue-green.yml stop web-${ACTIVE}
   ```

2. **Zmniejsz resources dla standby**:
   ```yaml
   # W docker-compose.blue-green.yml
   web-green:
     deploy:
       resources:
         limits:
           memory: 512M  # Mniej niż active
   ```

3. **Używaj tylko podczas deploy**:
   - Normalnie: tylko BLUE running
   - Deploy: uruchom GREEN, test, switch, zatrzymaj BLUE

## Testowanie przed przełączeniem

### Bezpośredni dostęp do GREEN (przed switch)

```bash
# Otwórz tunel SSH
ssh -L 8001:localhost:8000 pawel@VPS_IP

# Testuj GREEN bezpośrednio
docker exec nc-web-green curl http://localhost:8000/admin/

# Lub przez port forwarding
curl http://localhost:8001/admin/
```

### Smoke tests

Dodaj do `scripts/deploy/deploy-blue-green.sh` przed przełączeniem:

```bash
# Po health_check, przed switch_nginx
run_smoke_tests() {
    local environment=$1
    
    log_info "🧪 Smoke tests dla ${environment}..."
    
    # Test 1: Admin dostępny
    docker exec nc-web-${environment} curl -sf http://localhost:8000/admin/ > /dev/null
    
    # Test 2: API działa
    docker exec nc-web-${environment} curl -sf http://localhost:8000/api/ > /dev/null
    
    # Test 3: Database connection
    docker exec nc-web-${environment} python manage.py check --database default
    
    log_success "✅ Smoke tests passed"
}
```

## Porównanie ze standardowym deploy

| Aspekt | Standardowy | Blue-Green |
|--------|-------------|------------|
| Downtime | 10-30s | **0s** ✅ |
| Rollback time | 2-5min | **5s** ✅ |
| Ryzyko | Średnie | **Niskie** ✅ |
| RAM usage | 1x | 2x (chwilowo) |
| Complexity | Niska | Średnia |
| Testing | Po deploy | Przed switch ✅ |

## Troubleshooting

### Problem: Health check fails

```bash
# Sprawdź logi
docker logs nc-web-green --tail 100

# Sprawdź czy migracje przeszły
docker exec nc-web-green python manage.py showmigrations

# Sprawdź połączenie z DB
docker exec nc-web-green python manage.py check --database default
```

### Problem: NGINX nie przełącza

```bash
# Sprawdź konfigurację
docker exec nc-nginx-router nginx -t

# Sprawdź logi
docker logs nc-nginx-router --tail 50

# Ręczne przełączenie
docker exec nc-nginx-router nginx -s reload
```

### Problem: Oba environments stopped

```bash
# Uruchom oba
docker-compose -f docker-compose.blue-green.yml up -d web-blue web-green

# Sprawdź który działa
./scripts/deploy/deploy-blue-green.sh status
```

## Migracja z obecnego setup

### Krok 1: Backup

```bash
# Backup bazy
docker exec nc-postgres-1 pg_dumpall -U postgres > backup_before_bluegreen.sql
```

### Krok 2: Deploy blue-green pierwszy raz

```bash
# Zatrzymaj stary stack (single-stack) jeśli jeszcze istnieje na serwerze
# (w repo usunęliśmy docker-compose.prod.yml, bo prod działa tylko blue-green)

# Uruchom blue-green
docker-compose -f docker-compose.blue-green.yml up -d

# Sprawdź status
./scripts/deploy/deploy-blue-green.sh status
```

### Krok 3: Test

```bash
# Test aplikacji
curl http://VPS_IP/admin/

# Test API
curl http://VPS_IP/api/

# Test Flower
curl http://VPS_IP:5555/
```

### Krok 4: Zaktualizuj GitHub Actions

```yaml
# W .github/workflows/deploy-vps.yml
# Używaj docker-compose.blue-green.yml (prod działa tylko blue-green)
# Zmień komendy deploy na ./scripts/deploy/deploy-blue-green.sh deploy
```

## Best Practices

1. **Zawsze testuj GREEN przed switch** - smoke tests
2. **Monitoruj przez 5-10min po switch** - sprawdź errory
3. **Zachowaj rollback gotowy** - przez minimum 1h po deploy
4. **Database migrations** - wykonuj PRZED deploy (backwards compatible)
5. **Shared resources** - postgres/redis nigdy nie są duplikowane

## Podsumowanie

**Blue-Green deployment daje Ci:**
- ✅ Zero downtime podczas deploy
- ✅ Instant rollback w 5 sekund
- ✅ Bezpieczne testowanie przed przełączeniem ruchu
- ✅ Ochrona PostgreSQL i Redis (shared resources)

**Użycie:**
```bash
./scripts/deploy/deploy-blue-green.sh deploy    # Deploy nowej wersji
./scripts/deploy/deploy-blue-green.sh rollback  # Awaryjny powrót
./scripts/deploy/deploy-blue-green.sh status    # Status środowisk
```

🎉 **Zero downtime, maximum safety!**

