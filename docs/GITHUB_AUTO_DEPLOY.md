# 🤖 Automatyczny Deployment z GitHub Actions

> ⚠️ **HISTORYCZNE / NIEUŻYWANE (częściowo)**
>
> Ten dokument powstał dla starszego podejścia „zero‑downtime” i plików/skryptów, które w repo zostały już wycofane.
> Aktualnie produkcja działa **wyłącznie w trybie blue‑green**.
>
> **Aktualny proces (obowiązujący):**
> - Workflow: `.github/workflows/deploy-vps.yml`
> - Skrypt: `./scripts/deploy/deploy-blue-green.sh deploy`
> - Sekrety: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
>
> Reszta dokumentu poniżej jest **archiwalna** i może zawierać nieaktualne nazwy plików i komendy.

## 🎯 Jak to działa?

Po każdym `git push` na branch `main`:
1. ✅ GitHub Actions automatycznie się uruchamia
2. 📤 Kopiuje pliki na serwer produkcyjny
3. 🚀 Uruchamia blue‑green deploy (`./scripts/deploy/deploy-blue-green.sh deploy`)
4. 🏥 Sprawdza health check
5. ✅ Deployment zakończony (downtime tylko 2-5s!)
6. 🔙 W razie błędu - automatyczny rollback

## 📋 Konfiguracja (3 kroki)

### Krok 1: Dodaj plik workflow
```bash
# Plik już jest: .github/workflows/deploy-vps.yml
# Jest gotowy do użycia!
```

### Krok 2: Dodaj GitHub Secrets
Idź do: **GitHub → Twoje Repo → Settings → Secrets and variables → Actions**

Dodaj te secrets:

```
VPS_SSH_KEY     = Twój klucz SSH do serwera
VPS_USER        = użytkownik na serwerze
VPS_HOST        = IP / domena serwera
```

### Krok 3: Wygeneruj klucz SSH (jeśli nie masz)
```bash
# Na lokalnym komputerze:
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_deploy

# Skopiuj PUBLICZNY klucz na serwer:
ssh-copy-id -i ~/.ssh/github_deploy.pub user@twoj-serwer.pl

# Skopiuj PRYWATNY klucz do GitHub Secrets:
cat ~/.ssh/github_deploy
# Całą zawartość wklej jako VPS_SSH_KEY w GitHub
```

## 🚀 Użycie

### Automatyczny deployment:
```bash
# Zwykły workflow:
git add .
git commit -m "Dodano nową funkcję"
git push origin main

# GitHub Actions automatycznie:
# 1. Wykrywa push na main
# 2. Kopiuje pliki na serwer
# 3. Uruchamia zero-downtime deployment
# 4. Sprawdza czy działa
# 5. W razie błędu robi rollback
```

### Zobacz status deployment:
```
GitHub → Actions → Zobacz bieżący workflow
```

## 📊 Przykładowy przebieg

```
🚀 Auto Deploy na Production

✅ Checkout kod                      [3s]
✅ Setup SSH                         [2s]
✅ Skopiuj pliki na serwer          [15s]
✅ Uruchom Zero-Downtime Deployment [60s]
   │
   ├─ 🔨 Buduję nowy obraz w tle    [45s]
   ├─ 💾 Tworzę backup starego      [2s]
   ├─ 🔄 Przełączam (2-5s downtime) [3s]
   └─ 🏥 Health check               [10s]
   
✅ Health Check                      [10s]
✅ Deployment sukces!                [1s]

Total: ~91s
Downtime: ~3s
```

## 🎛️ Zaawansowane opcje

### Deployment tylko dla konkretnych plików
```yaml
on:
  push:
    branches:
      - main
    paths:
      - 'matterhorn1/**'
      - 'requirements.txt'
      - 'Dockerfile.prod'
```

### Ręczne uruchomienie deployment
Dodaj do workflow:
```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment'
        required: true
        default: 'prod'
```

Potem możesz uruchomić ręcznie z GitHub UI.

### Deployment z approval
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://twoja-domena.pl
```

Idź do Settings → Environments → production → Required reviewers

## 🔔 Notyfikacje

### Slack notification
Dodaj na końcu workflow:
```yaml
- name: Slack Notification
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Discord notification
```yaml
- name: Discord Notification
  if: always()
  uses: sarisia/actions-status-discord@v1
  with:
    webhook: ${{ secrets.DISCORD_WEBHOOK }}
```

### Email notification
GitHub automatycznie wysyła email jeśli deployment fail.

## 🛡️ Bezpieczeństwo

### Best practices:
1. ✅ **Używaj SSH keys** (nie haseł)
2. ✅ **Ogranicz uprawnienia** SSH usera
3. ✅ **Nie commituj .env** plików
4. ✅ **Używaj GitHub Secrets** dla wrażliwych danych
5. ✅ **Włącz 2FA** na GitHubie

### Bezpieczny SSH user:
```bash
# Na serwerze:
# Stwórz dedykowanego usera dla deployment
sudo useradd -m -s /bin/bash deployer
sudo usermod -aG docker deployer

# Pozwól tylko na deployment (bez sudo)
# Użytkownik może tylko docker-compose i deployment
```

## 🧪 Testowanie

### Test deployment bez pushowania na main:
```bash
# Stwórz branch testowy:
git checkout -b test-deployment

# Zmień workflow żeby triggerował na test-deployment:
on:
  push:
    branches:
      - test-deployment

# Push i zobacz czy działa:
git push origin test-deployment

# Zobacz w GitHub Actions
```

## 📝 Przykłady workflow

### 1. Deployment z testami
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: python manage.py test
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        run: ssh ... ./scripts/deploy/deploy-blue-green.sh deploy
```

### 2. Multi-environment
```yaml
jobs:
  deploy-staging:
    if: github.ref == 'refs/heads/develop'
    # Deploy to staging
  
  deploy-production:
    if: github.ref == 'refs/heads/main'
    # Deploy to production
```

### 3. Scheduled deployment
```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Codziennie o 2:00
```

## 🐛 Troubleshooting

### Problem: SSH connection failed
```bash
# Sprawdź połączenie ręcznie:
ssh -i ~/.ssh/github_deploy user@serwer

# Sprawdź czy klucz jest dodany na serwerze:
cat ~/.ssh/authorized_keys
```

### Problem: rsync failed
```bash
# Sprawdź uprawnienia:
ls -la /deploy/path/

# Sprawdź czy rsync jest zainstalowany:
which rsync
```

### Problem: Docker permission denied
```bash
# Dodaj usera do grupy docker:
sudo usermod -aG docker $USER

# Wyloguj i zaloguj ponownie
```

### Problem: Health check failed
```bash
# Sprawdź logi:
ssh user@serwer
cd /deploy/path
docker-compose logs web
```

## 📈 Monitoring

### Zobacz deployment history:
```
GitHub → Actions → Workflows → production-deploy
```

### Zobacz logi na serwerze:
```bash
ssh user@serwer
cd /deploy/path
docker-compose logs -f
```

### Status kontenerów:
```bash
docker-compose ps
docker stats
```

## ✅ Checklist

Przed pierwszym użyciem sprawdź:

- [ ] Workflow file istnieje: `.github/workflows/deploy-vps.yml`
- [ ] GitHub Secrets są dodane (VPS_SSH_KEY, VPS_USER, VPS_HOST)
- [ ] SSH klucz działa: `ssh user@serwer`
- [ ] Folder deployment istnieje na serwerze
- [ ] Docker jest zainstalowany na serwerze
- [ ] User ma uprawnienia do docker
- [ ] Pliki `.env.prod` są na serwerze
- [ ] Port 80/443 jest otwarty
- [ ] Health check endpoint działa

## 🎉 Gotowe!

Teraz każdy `git push` na `main` automatycznie wdroży nową wersję z **zero-downtime**!

```bash
git add .
git commit -m "Deploy automatyczny!"
git push origin main

# GitHub Actions robi resztę! 🚀
```

---

**Potrzebujesz pomocy?** Zobacz:
- [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md)
- [DEPLOYMENT_SCRIPTS.md](DEPLOYMENT_SCRIPTS.md)
- [GitHub Actions Docs](https://docs.github.com/actions)

