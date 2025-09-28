#!/bin/bash
# Redis Firewall Rules
# Skrypt do konfiguracji firewall dla Redis

echo "Konfiguracja firewall dla Redis..."

# Sprawdź czy ufw jest zainstalowany
if ! command -v ufw &> /dev/null; then
    echo "UFW nie jest zainstalowany. Instalowanie..."
    sudo apt update
    sudo apt install -y ufw
fi

# Resetuj ufw do domyślnych ustawień
sudo ufw --force reset

# Ustaw domyślne polityki
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Zezwól na SSH (ważne!)
sudo ufw allow ssh
sudo ufw allow 22/tcp

# Zezwól na HTTP i HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Zezwól na port Django (tylko lokalnie)
sudo ufw allow from 127.0.0.1 to any port 8000

# Zezwól na port Flower (tylko lokalnie)
sudo ufw allow from 127.0.0.1 to any port 5555

# BLOKUJ Redis - nie zezwalaj na zewnętrzne połączenia
# Redis powinien być dostępny tylko wewnątrz sieci Docker
sudo ufw deny 6379/tcp

# Zezwól na połączenia wewnętrzne Docker
sudo ufw allow from 172.16.0.0/12
sudo ufw allow from 192.168.0.0/16
sudo ufw allow from 10.0.0.0/8

# Rate limiting dla SSH
sudo ufw limit ssh

# Włącz firewall
sudo ufw --force enable

# Pokaż status
echo "Status firewall:"
sudo ufw status verbose

echo "Firewall skonfigurowany dla Redis!"
echo "Redis jest teraz dostępny tylko wewnątrz sieci Docker."

