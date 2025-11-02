#!/bin/bash
# 🚀 Kompletna konfiguracja VPS od podstaw dla Django + Docker
# Użycie: sudo bash setup-vps.sh

set -e

echo "🚀 KONFIGURACJA VPS OD PODSTAW"
echo "================================"
echo ""

# Kolory dla outputu
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funkcja do logowania
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Sprawdź czy jesteś root
if [ "$EUID" -ne 0 ]; then 
    log_error "Uruchom skrypt jako root lub z sudo!"
    exit 1
fi

# Krok 1: Aktualizacja systemu
echo ""
echo "📦 KROK 1: Aktualizacja systemu..."
log_info "Aktualizuję pakiety systemowe..."

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    ufw \
    fail2ban \
    htop \
    nano \
    wget \
    unzip

log_info "System zaktualizowany"
echo ""

# Krok 2: Instalacja Docker
echo "🐳 KROK 2: Instalacja Docker..."
if command -v docker &> /dev/null; then
    log_warn "Docker już jest zainstalowany"
    docker --version
else
    log_info "Instaluję Docker..."
    
    # Dodaj Docker repository
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Start Docker
    systemctl enable docker
    systemctl start docker
    
    log_info "Docker zainstalowany: $(docker --version)"
fi
echo ""

# Krok 3: Instalacja Docker Compose (standalone)
echo "🐙 KROK 3: Instalacja Docker Compose..."
if command -v docker-compose &> /dev/null; then
    log_warn "Docker Compose już jest zainstalowany"
    docker-compose --version
else
    log_info "Instaluję Docker Compose..."
    
    DOCKER_COMPOSE_VERSION="v2.24.0"
    curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    log_info "Docker Compose zainstalowany: $(docker-compose --version)"
fi
echo ""

# Krok 4: Konfiguracja użytkownika
echo "👤 KROK 4: Konfiguracja użytkownika..."
read -p "Nazwa użytkownika do utworzenia (lub naciśnij Enter aby pominąć): " USERNAME

if [ -n "$USERNAME" ]; then
    if id "$USERNAME" &>/dev/null; then
        log_warn "Użytkownik $USERNAME już istnieje"
    else
        log_info "Tworzę użytkownika: $USERNAME"
        useradd -m -s /bin/bash "$USERNAME"
        
        # Dodaj do grupy docker (aby mógł uruchamiać Docker bez sudo)
        usermod -aG docker "$USERNAME"
        
        # Dodaj do grupy sudo
        usermod -aG sudo "$USERNAME"
        
        log_info "Utworzono użytkownika $USERNAME (dodano do grup: docker, sudo)"
        log_warn "Pamiętaj aby ustawić hasło: passwd $USERNAME"
    fi
else
    log_info "Pomijam tworzenie użytkownika"
fi
echo ""

# Krok 5: Konfiguracja Firewall (UFW)
echo "🔥 KROK 5: Konfiguracja Firewall..."
log_info "Konfiguruję UFW..."

# Reset UFW (jeśli był wcześniej skonfigurowany)
ufw --force reset

# Domyślne polityki
ufw default deny incoming
ufw default allow outgoing

# SSH (WARUNEK KONIECZNY - inaczej stracisz dostęp!)
log_warn "UWAGA: Otwieram port 22 dla SSH!"
ufw allow 22/tcp comment 'SSH'

# HTTP i HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Port dla Flower (Celery monitoring) - opcjonalnie
read -p "Otworzyć port 5555 dla Flower? (y/n, domyślnie n): " OPEN_FLOWER
if [ "$OPEN_FLOWER" = "y" ] || [ "$OPEN_FLOWER" = "Y" ]; then
    ufw allow 5555/tcp comment 'Flower (Celery)'
    log_info "Port 5555 otwarty dla Flower"
else
    log_info "Port 5555 zamknięty (dostęp lokalny)"
fi

# Włącz firewall
ufw --force enable

log_info "Firewall skonfigurowany"
ufw status verbose
echo ""

# Krok 6: Konfiguracja Fail2Ban
echo "🛡️ KROK 6: Konfiguracja Fail2Ban..."
log_info "Konfiguruję Fail2Ban dla SSH..."

# Utwórz konfigurację Fail2Ban dla SSH
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = 22
logpath = %(sshd_log)s
maxretry = 3
bantime = 7200
EOF

systemctl enable fail2ban
systemctl restart fail2ban

log_info "Fail2Ban skonfigurowany"
echo ""

# Krok 7: Konfiguracja SSH (opcjonalne ulepszenia)
echo "🔐 KROK 7: Konfiguracja SSH..."
read -p "Czy chcesz zaktualizować konfigurację SSH? (y/n, domyślnie n): " CONFIG_SSH

if [ "$CONFIG_SSH" = "y" ] || [ "$CONFIG_SSH" = "Y" ]; then
    log_info "Tworzę backup /etc/ssh/sshd_config..."
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)
    
    # Podstawowe zabezpieczenia SSH
    sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
    
    # Wyłącz puste hasła
    if ! grep -q "PermitEmptyPasswords no" /etc/ssh/sshd_config; then
        echo "PermitEmptyPasswords no" >> /etc/ssh/sshd_config
    fi
    
    log_info "Konfiguracja SSH zaktualizowana"
    log_warn "Aby zastosować zmiany, uruchom: systemctl restart sshd"
else
    log_info "Pomijam konfigurację SSH"
fi
echo ""

# Krok 8: Przygotowanie katalogów
echo "📁 KROK 8: Przygotowanie katalogów..."
APP_DIR="/srv/app"

if [ -d "$APP_DIR" ]; then
    log_warn "Katalog $APP_DIR już istnieje"
else
    log_info "Tworzę katalog: $APP_DIR"
    mkdir -p "$APP_DIR"
    
    if [ -n "$USERNAME" ]; then
        chown "$USERNAME:$USERNAME" "$APP_DIR"
        log_info "Właścicielem katalogu jest: $USERNAME"
    fi
fi

log_info "Katalog gotowy: $APP_DIR"
echo ""

# Krok 9: Optymalizacja systemu
echo "⚡ KROK 9: Optymalizacja systemu..."
log_info "Konfiguruję limity dla Docker..."

# Zwiększ limity dla Docker
cat >> /etc/sysctl.conf << 'EOF'

# Docker optimizations
vm.max_map_count=262144
fs.file-max=2097152
EOF

sysctl -p > /dev/null

log_info "Optymalizacje zastosowane"
echo ""

# Krok 10: Konfiguracja logrotate dla Docker
echo "📝 KROK 10: Konfiguracja logrotate..."
log_info "Konfiguruję rotację logów Docker..."

cat > /etc/logrotate.d/docker-containers << 'EOF'
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=10M
    missingok
    delaycompress
    copytruncate
}
EOF

log_info "Logrotate skonfigurowany"
echo ""

# Podsumowanie
echo ""
echo "========================================"
echo "✅ KONFIGURACJA ZAKOŃCZONA!"
echo "========================================"
echo ""
echo "📋 Podsumowanie:"
echo ""
echo "✓ System zaktualizowany"
echo "✓ Docker zainstalowany: $(docker --version 2>/dev/null || echo 'N/A')"
echo "✓ Docker Compose zainstalowany: $(docker-compose --version 2>/dev/null || echo 'N/A')"
if [ -n "$USERNAME" ]; then
    echo "✓ Użytkownik utworzony: $USERNAME"
    echo "  ⚠️  Pamiętaj: passwd $USERNAME"
fi
echo "✓ Firewall (UFW) skonfigurowany"
echo "✓ Fail2Ban włączony"
echo "✓ Katalog aplikacji: $APP_DIR"
echo ""
echo "🔐 NASTĘPNE KROKI:"
echo ""
echo "1. Jeśli utworzyłeś użytkownika, ustaw hasło:"
echo "   passwd $USERNAME"
echo ""
echo "2. Skonfiguruj klucz SSH dla użytkownika (jeśli potrzeba):"
if [ -n "$USERNAME" ]; then
    echo "   sudo -u $USERNAME mkdir -p /home/$USERNAME/.ssh"
    echo "   sudo -u $USERNAME chmod 700 /home/$USERNAME/.ssh"
fi
echo ""
echo "3. Sklonuj projekt w $APP_DIR:"
echo "   cd $APP_DIR"
if [ -n "$USERNAME" ]; then
    echo "   sudo -u $USERNAME git clone <twoje-repo> ."
else
    echo "   git clone <twoje-repo> ."
fi
echo ""
echo "4. Skonfiguruj plik .env.prod z ustawieniami bazy danych"
echo ""
echo "5. Uruchom deployment:"
echo "   cd $APP_DIR"
echo "   docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "⚠️  WAŻNE:"
echo "- Sprawdź czy masz dostęp SSH przed zamknięciem sesji!"
echo "- Jeśli zmieniłeś konfigurację SSH, uruchom: systemctl restart sshd"
echo "- Firewall jest włączony - sprawdź: ufw status"
echo ""
echo "📚 Dokumentacja projektu znajduje się w repozytorium"
echo ""

