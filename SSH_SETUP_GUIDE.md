# 🔐 Konfiguracja SSH na Ubuntu Server

Przewodnik do skonfigurowania SSH, aby móc się połączyć z serwerem zdalnie.

---

## 🚀 Szybki start (automatyczny)

Jeśli masz już terminal otwarty na serwerze, uruchom:

```bash
# Pobierz i uruchom skrypt konfiguracji
wget https://raw.githubusercontent.com/pawlo884/nc/main/setup-ssh.sh
# Lub jeśli masz lokalnie:
sudo bash setup-ssh.sh
```

Skrypt automatycznie:
- ✅ Zainstaluje SSH server (jeśli nie ma)
- ✅ Skonfiguruje SSH
- ✅ Sprawdzi adres IP
- ✅ Skonfiguruje firewall
- ✅ Pokaże jak się połączyć

---

## 📝 Instrukcja krok po kroku (ręczna)

### Krok 1: Sprawdź czy SSH jest zainstalowany

```bash
# Sprawdź status SSH
sudo systemctl status ssh
```

Jeśli widzisz `active (running)`, SSH już działa! Przejdź do Kroku 2.

Jeśli nie ma SSH, zainstaluj:

```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh
```

---

### Krok 2: Sprawdź adres IP serwera

```bash
# Sprawdź adres IP
ip addr show

# Lub krócej:
hostname -I

# Lub jeszcze prościej:
ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
```

Zapisz adres IP (np. `192.168.1.100` lub podobny).

---

### Krok 3: Sprawdź nazwę użytkownika

```bash
# Sprawdź obecnego użytkownika
whoami

# Lub zobacz wszystkich użytkowników
cat /etc/passwd | cut -d: -f1
```

Zapisz nazwę użytkownika (np. `ubuntu`, `admin`, `deploy`).

---

### Krok 4: Ustaw hasło użytkownika (jeśli potrzeba)

```bash
# Zmień hasło dla obecnego użytkownika
passwd

# Lub dla innego użytkownika (jako root/sudo):
sudo passwd nazwa_uzytkownika
```

⚠️ **WAŻNE**: Zapamiętaj to hasło - będziesz go potrzebować do logowania!

---

### Krok 5: Sprawdź czy firewall przepuszcza SSH

```bash
# Sprawdź czy UFW jest włączony
sudo ufw status

# Jeśli firewall jest aktywny, sprawdź czy SSH jest dozwolone
# Jeśli nie, dodaj:
sudo ufw allow 22/tcp comment 'SSH'

# Sprawdź status
sudo ufw status verbose
```

---

### Krok 6: Sprawdź konfigurację SSH

```bash
# Zobacz konfigurację SSH
sudo nano /etc/ssh/sshd_config
```

Ważne opcje:
- `Port 22` - port SSH (domyślnie 22)
- `PermitRootLogin no` - zalecane wyłączyć logowanie root
- `PasswordAuthentication yes` - zezwalaj na logowanie hasłem
- `PubkeyAuthentication yes` - zezwalaj na klucze SSH

Po zmianach zrestartuj SSH:
```bash
sudo systemctl restart ssh
```

---

## 🌐 Połączenie z serwera

### Z Windows (PowerShell lub CMD)

```powershell
# Podstawowe połączenie
ssh uzytkownik@192.168.1.100

# Z podaniem portu (jeśli zmieniony)
ssh -p 22 uzytkownik@192.168.1.100
```

### Z Linux/Mac

```bash
# Podstawowe połączenie
ssh uzytkownik@192.168.1.100

# Z podaniem portu
ssh -p 22 uzytkownik@192.168.1.100
```

### Z Visual Studio Code / Cursor

1. Zainstaluj rozszerzenie **Remote - SSH**
2. Naciśnij `Ctrl+Shift+P` (lub `Cmd+Shift+P` na Mac)
3. Wybierz **Remote-SSH: Connect to Host**
4. Wpisz: `uzytkownik@192.168.1.100`
5. Połącz się i wprowadź hasło

---

## 🔑 Konfiguracja klucza SSH (opcjonalne, zalecane)

### Na swoim komputerze (Windows/Linux/Mac):

```bash
# 1. Wygeneruj klucz SSH (jeśli nie masz)
ssh-keygen -t ed25519 -C "twoj-email@example.com"

# 2. Skopiuj klucz na serwer
ssh-copy-id uzytkownik@192.168.1.100

# 3. Teraz możesz się logować bez hasła!
ssh uzytkownik@192.168.1.100
```

### Z Windows (PowerShell):

```powershell
# 1. Wygeneruj klucz (jeśli nie masz)
ssh-keygen -t ed25519

# 2. Skopiuj zawartość pliku publicznego
Get-Content ~\.ssh\id_ed25519.pub

# 3. Na serwerze dodaj klucz ręcznie:
ssh uzytkownik@192.168.1.100

# Na serwerze:
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
# Wklej zawartość id_ed25519.pub
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

---

## 🔒 Zabezpieczenie SSH

### 1. Zmień port SSH (opcjonalne)

```bash
sudo nano /etc/ssh/sshd_config
# Zmień: Port 22 na Port 2222 (lub inny)

sudo systemctl restart ssh
sudo ufw allow 2222/tcp comment 'SSH custom port'
```

### 2. Wyłącz logowanie root

```bash
sudo nano /etc/ssh/sshd_config
# Ustaw: PermitRootLogin no

sudo systemctl restart ssh
```

### 3. Ograniczenie do konkretnych użytkowników

```bash
sudo nano /etc/ssh/sshd_config
# Dodaj: AllowUsers uzytkownik1 uzytkownik2

sudo systemctl restart ssh
```

### 4. Fail2Ban (ochrona przed brute force)

```bash
sudo apt install -y fail2ban

# Konfiguracja dla SSH
sudo nano /etc/fail2ban/jail.local
```

Dodaj:
```ini
[sshd]
enabled = true
port = 22
maxretry = 3
bantime = 3600
```

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 🧪 Testowanie połączenia

### Sprawdź czy SSH działa

```bash
# Na serwerze:
sudo systemctl status ssh
```

### Test z lokalnego komputera

```bash
# Test połączenia
ssh -v uzytkownik@IP_ADRES

# Test z konkretnym portem
ssh -v -p 22 uzytkownik@IP_ADRES
```

Flaga `-v` pokazuje szczegóły połączenia (debug).

---

## 🔧 Troubleshooting

### "Connection refused"

```bash
# Sprawdź czy SSH działa
sudo systemctl status ssh

# Sprawdź czy port jest otwarty
sudo netstat -tlnp | grep :22
# lub
sudo ss -tlnp | grep :22

# Sprawdź firewall
sudo ufw status
```

### "Permission denied"

- Sprawdź czy użytkownik istnieje: `id uzytkownik`
- Sprawdź hasło: `passwd uzytkownik`
- Sprawdź `/etc/ssh/sshd_config` - opcja `PasswordAuthentication yes`

### Nie mogę się połączyć z sieci zewnętrznej

- Sprawdź czy masz publiczne IP (nie tylko lokalne 192.168.x.x)
- Sprawdź router/firewall - port forwarding dla portu 22
- Sprawdź firewall na serwerze: `sudo ufw status`

### SSH wolno się łączy

```bash
# Wyłącz DNS lookup w SSH
sudo nano /etc/ssh/sshd_config
# Dodaj: UseDNS no

sudo systemctl restart ssh
```

---

## 📋 Przykładowa sesja

```bash
# Na serwerze - sprawdź IP
$ hostname -I
192.168.1.100

# Sprawdź użytkownika
$ whoami
ubuntu

# Sprawdź SSH
$ sudo systemctl status ssh
● ssh.service - OpenBSD Secure Shell server
     Loaded: loaded
     Active: active (running)

# Na komputerze lokalnym (Windows PowerShell):
PS> ssh ubuntu@192.168.1.100
The authenticity of host '192.168.1.100' can't be established.
Are you sure you want to continue connecting (yes/no)? yes
ubuntu@192.168.1.100's password: ********

# Zalogowano!
ubuntu@server:~$
```

---

## ✅ Checklist konfiguracji

- [ ] SSH server zainstalowany
- [ ] SSH działa (`systemctl status ssh`)
- [ ] Znam adres IP serwera
- [ ] Ustawiłem hasło użytkownika
- [ ] Firewall przepuszcza SSH (port 22)
- [ ] Mogę się połączyć z lokalnego komputera
- [ ] (Opcjonalnie) Skonfigurowałem klucz SSH
- [ ] (Opcjonalnie) Zmieniłem domyślny port SSH
- [ ] (Opcjonalnie) Wyłączyłem logowanie root

---

**Gotowe!** Po skonfigurowaniu SSH możesz połączyć się zdalnie i uruchomić `setup-vps.sh` do pełnej konfiguracji VPS.

