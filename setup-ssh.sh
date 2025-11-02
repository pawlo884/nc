#!/bin/bash
# 🔐 Konfiguracja SSH na Ubuntu Server
# Użycie: sudo bash setup-ssh.sh

set -e

echo "🔐 KONFIGURACJA SSH"
echo "==================="
echo ""

# Kolory
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

# Krok 1: Sprawdź czy SSH jest zainstalowany
echo "📦 KROK 1: Sprawdzam SSH..."
if systemctl is-active --quiet ssh; then
    log_info "SSH już działa"
elif systemctl is-enabled --quiet ssh; then
    log_info "SSH jest włączony ale nie działa - uruchamiam..."
    systemctl start ssh
else
    log_info "Instaluję SSH server..."
    apt-get update -qq
    apt-get install -y -qq openssh-server
    systemctl enable ssh
    systemctl start ssh
    log_info "SSH zainstalowany i uruchomiony"
fi
echo ""

# Krok 2: Status SSH
echo "📊 KROK 2: Status SSH..."
systemctl status ssh --no-pager | head -n 10
echo ""

# Krok 3: Sprawdź adres IP
echo "🌐 KROK 3: Adresy IP maszyny..."
echo ""
echo "Wszystkie adresy IP tej maszyny:"
ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || hostname -I
echo ""

# Krok 4: Konfiguracja SSH
echo "⚙️ KROK 4: Konfiguracja SSH..."
read -p "Czy chcesz zmienić konfigurację SSH? (y/n, domyślnie y): " CONFIG_SSH

CONFIG_SSH=${CONFIG_SSH:-y}

if [ "$CONFIG_SSH" = "y" ] || [ "$CONFIG_SSH" = "Y" ]; then
    log_info "Tworzę backup konfiguracji SSH..."
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)
    
    echo ""
    echo "Wybierz opcje konfiguracji:"
    echo ""
    
    # Port SSH
    read -p "Port SSH (domyślnie 22): " SSH_PORT
    SSH_PORT=${SSH_PORT:-22}
    
    if [ "$SSH_PORT" != "22" ]; then
        sed -i "s/#Port 22/Port $SSH_PORT/" /etc/ssh/sshd_config
        if ! grep -q "^Port $SSH_PORT" /etc/ssh/sshd_config; then
            echo "Port $SSH_PORT" >> /etc/ssh/sshd_config
        fi
        log_info "Port SSH zmieniony na: $SSH_PORT"
    fi
    
    # Root login
    read -p "Zezwolić na logowanie root przez SSH? (y/n, domyślnie n): " ROOT_LOGIN
    ROOT_LOGIN=${ROOT_LOGIN:-n}
    
    if [ "$ROOT_LOGIN" = "n" ] || [ "$ROOT_LOGIN" = "N" ]; then
        sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
        sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
        if ! grep -q "^PermitRootLogin" /etc/ssh/sshd_config; then
            echo "PermitRootLogin no" >> /etc/ssh/sshd_config
        fi
        log_info "Logowanie root wyłączone"
    fi
    
    # Password authentication
    read -p "Zezwolić na logowanie hasłem? (y/n, domyślnie y): " PASSWORD_AUTH
    PASSWORD_AUTH=${PASSWORD_AUTH:-y}
    
    if [ "$PASSWORD_AUTH" = "n" ] || [ "$PASSWORD_AUTH" = "N" ]; then
        sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
        sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
        if ! grep -q "^PasswordAuthentication" /etc/ssh/sshd_config; then
            echo "PasswordAuthentication no" >> /etc/ssh/sshd_config
        fi
        log_warn "Logowanie hasłem wyłączone - będziesz potrzebował klucza SSH!"
    else
        sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
        sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
        if ! grep -q "^PasswordAuthentication" /etc/ssh/sshd_config; then
            echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config
        fi
        log_info "Logowanie hasłem włączone"
    fi
    
    # Pubkey authentication
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
    if ! grep -q "^PubkeyAuthentication" /etc/ssh/sshd_config; then
        echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config
    fi
    
    # Empty passwords
    if ! grep -q "^PermitEmptyPasswords" /etc/ssh/sshd_config; then
        echo "PermitEmptyPasswords no" >> /etc/ssh/sshd_config
    fi
    
    log_info "Konfiguracja SSH zaktualizowana"
    
    # Restart SSH
    echo ""
    read -p "Zrestartować SSH teraz? (y/n, domyślnie y): " RESTART_SSH
    RESTART_SSH=${RESTART_SSH:-y}
    
    if [ "$RESTART_SSH" = "y" ] || [ "$RESTART_SSH" = "Y" ]; then
        log_info "Restartuję SSH..."
        systemctl restart ssh
        sleep 2
        
        if systemctl is-active --quiet ssh; then
            log_info "SSH zrestartowany pomyślnie"
        else
            log_error "Błąd podczas restartu SSH - sprawdź konfigurację!"
            exit 1
        fi
    else
        log_warn "SSH nie został zrestartowany - uruchom ręcznie: systemctl restart ssh"
    fi
else
    log_info "Pomijam konfigurację SSH"
fi
echo ""

# Krok 5: Firewall
echo "🔥 KROK 5: Konfiguracja Firewall..."
if command -v ufw &> /dev/null; then
    read -p "Czy skonfigurować firewall (UFW) dla SSH? (y/n, domyślnie y): " CONFIG_FW
    CONFIG_FW=${CONFIG_FW:-y}
    
    if [ "$CONFIG_FW" = "y" ] || [ "$CONFIG_FW" = "Y" ]; then
        # Sprawdź port SSH z konfiguracji
        SSH_PORT_CONFIG=$(grep "^Port" /etc/ssh/sshd_config | awk '{print $2}' | head -n 1)
        SSH_PORT_CONFIG=${SSH_PORT_CONFIG:-22}
        
        log_info "Dodaję regułę firewall dla portu $SSH_PORT_CONFIG..."
        ufw allow $SSH_PORT_CONFIG/tcp comment 'SSH'
        
        read -p "Czy włączyć firewall? (y/n, domyślnie y): " ENABLE_FW
        ENABLE_FW=${ENABLE_FW:-y}
        
        if [ "$ENABLE_FW" = "y" ] || [ "$ENABLE_FW" = "Y" ]; then
            ufw --force enable
            log_info "Firewall włączony"
            ufw status verbose
        else
            log_warn "Firewall nie został włączony"
        fi
    fi
else
    log_warn "UFW nie jest zainstalowany - pomijam konfigurację firewall"
fi
echo ""

# Krok 6: Sprawdź użytkowników
echo "👤 KROK 6: Użytkownicy systemu..."
echo ""
echo "Dostępni użytkownicy:"
cut -d: -f1 /etc/passwd | grep -v "^#" | sort
echo ""

read -p "Czy chcesz zmienić hasło dla użytkownika? (y/n): " CHANGE_PASS
if [ "$CHANGE_PASS" = "y" ] || [ "$CHANGE_PASS" = "Y" ]; then
    read -p "Nazwa użytkownika: " USERNAME
    if id "$USERNAME" &>/dev/null; then
        passwd "$USERNAME"
        log_info "Hasło zmienione dla użytkownika: $USERNAME"
    else
        log_error "Użytkownik $USERNAME nie istnieje!"
    fi
fi
echo ""

# Krok 7: Informacje o połączeniu
echo "📋 KROK 7: Informacje o połączeniu..."
echo ""
IP_ADDRESS=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v "127.0.0.1" | head -n 1)
SSH_PORT_FINAL=$(grep "^Port" /etc/ssh/sshd_config | awk '{print $2}' | head -n 1)
SSH_PORT_FINAL=${SSH_PORT_FINAL:-22}
CURRENT_USER=$(whoami)

echo "========================================"
echo "✅ SSH SKONFIGUROWANY!"
echo "========================================"
echo ""
echo "📡 Aby połączyć się z tego komputera:"
echo ""
echo "   ssh $CURRENT_USER@$IP_ADDRESS"
if [ "$SSH_PORT_FINAL" != "22" ]; then
    echo "   (port: $SSH_PORT_FINAL)"
    echo ""
    echo "   Lub z Windows PowerShell:"
    echo "   ssh -p $SSH_PORT_FINAL $CURRENT_USER@$IP_ADDRESS"
fi
echo ""
echo "🌐 Adres IP serwera: $IP_ADDRESS"
echo "🔌 Port SSH: $SSH_PORT_FINAL"
echo "👤 Użytkownik: $CURRENT_USER"
echo ""
echo "🔐 Sposób połączenia:"
if grep -q "^PasswordAuthentication yes" /etc/ssh/sshd_config || ! grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config; then
    echo "   ✓ Logowanie hasłem: TAK"
else
    echo "   ✗ Logowanie hasłem: NIE (wymagany klucz SSH)"
fi

if grep -q "^PubkeyAuthentication yes" /etc/ssh/sshd_config || ! grep -q "^PubkeyAuthentication no" /etc/ssh/sshd_config; then
    echo "   ✓ Logowanie kluczem SSH: TAK"
fi
echo ""

# Krok 8: Test połączenia (opcjonalnie)
echo "🧪 KROK 8: Test SSH..."
if systemctl is-active --quiet ssh; then
    log_info "SSH działa poprawnie"
    echo ""
    echo "Możesz teraz połączyć się z innego komputera:"
    echo "   ssh $CURRENT_USER@$IP_ADDRESS"
else
    log_error "SSH nie działa - sprawdź: systemctl status ssh"
fi
echo ""

echo "💡 WAŻNE:"
echo "- Jeśli zmieniłeś port SSH, upewnij się że firewall go przepuszcza"
echo "- Jeśli wyłączyłeś logowanie hasłem, skonfiguruj klucz SSH"
echo "- Backup konfiguracji znajduje się w: /etc/ssh/sshd_config.backup.*"
echo ""

