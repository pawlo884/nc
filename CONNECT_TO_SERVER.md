# 🔌 Jak połączyć się z serwerem przez SSH

## 📋 Krok 1: Sprawdź informacje na serwerze

Na serwerze (w terminalu Ubuntu) wykonaj te komendy:

```bash
# 1. Sprawdź adres IP serwera
hostname -I

# 2. Sprawdź nazwę użytkownika
whoami

# 3. Sprawdź czy SSH działa
sudo systemctl status ssh
```

**Zapisz sobie:**
- Adres IP (np. `192.168.1.100` lub `10.0.0.5`)
- Nazwę użytkownika (np. `ubuntu`, `admin`, `deploy`)

---

## 🪟 Krok 2: Połączenie z Windows

### Opcja A: PowerShell (najprostsze)

1. **Otwórz PowerShell** na Windows:
   - Naciśnij `Win + X`
   - Wybierz **Windows PowerShell** lub **Terminal**

2. **Połącz się:**
```powershell
ssh uzytkownik@IP_ADRES
```

**Przykład:**
```powershell
ssh ubuntu@192.168.1.100
```

3. **Pierwsze połączenie:**
   - Zobaczysz pytanie: `The authenticity of host... can't be established. Are you sure you want to continue connecting (yes/no)?`
   - Wpisz: **`yes`** i naciśnij Enter

4. **Wprowadź hasło:**
   - Wpisz hasło użytkownika (naciśnij Enter, hasło nie będzie widoczne)
   - Jeśli wszystko OK, zobaczysz prompt serwera: `uzytkownik@serwer:~$`

---

### Opcja B: Windows Terminal

1. **Zainstaluj Windows Terminal** (jeśli nie masz):
   - Microsoft Store → Windows Terminal

2. **Utwórz nowy profil SSH:**
   - Otwórz ustawienia (Ctrl + ,)
   - Dodaj nowy profil → SSH

3. **Lub użyj bezpośrednio:**
```powershell
ssh uzytkownik@IP_ADRES
```

---

### Opcja C: PuTTY (jeśli wolisz GUI)

1. **Pobierz PuTTY:**
   - https://www.putty.org/

2. **Konfiguracja:**
   - **Host Name (or IP address)**: wpisz IP serwera
   - **Port**: 22 (domyślnie)
   - **Connection type**: SSH
   - Kliknij **Open**

3. **Pierwsze połączenie:**
   - Kliknij **Yes** przy ostrzeżeniu

4. **Logowanie:**
   - Login as: `uzytkownik`
   - Password: wpisz hasło

---

### Opcja D: Visual Studio Code / Cursor (dla programistów)

1. **Zainstaluj rozszerzenie:**
   - Remote - SSH

2. **Połącz się:**
   - Naciśnij `F1` lub `Ctrl+Shift+P`
   - Wpisz: `Remote-SSH: Connect to Host`
   - Wpisz: `uzytkownik@IP_ADRES`
   - Wybierz plik konfiguracyjny SSH (domyślny)
   - Wprowadź hasło

3. **Efekt:**
   - VS Code/Cursor połączy się z serwerem
   - Możesz edytować pliki zdalnie!

---

## 🔍 Jak znaleźć adres IP serwera

### Jeśli serwer jest w tej samej sieci (lokalnej):

Na serwerze:
```bash
hostname -I
ip addr show
```

Zwykle będzie to coś jak:
- `192.168.1.xxx`
- `10.0.0.xxx`
- `172.16.0.xxx`

### Jeśli serwer ma publiczne IP (VPS/DigitalOcean/AWS):

1. **Sprawdź w panelu dostawcy** (DigitalOcean, AWS, itp.)
2. **Lub na serwerze:**
```bash
curl ifconfig.me
curl ipinfo.io/ip
```

---

## 🧪 Test połączenia

### Przed połączeniem sprawdź czy serwer jest dostępny:

**Z Windows PowerShell:**
```powershell
# Sprawdź czy serwer odpowiada na ping
ping IP_ADRES

# Test portu SSH (jeśli masz telnet)
Test-NetConnection -ComputerName IP_ADRES -Port 22
```

### Jeśli ping nie działa:

- Sprawdź czy serwer i komputer są w tej samej sieci
- Sprawdź firewall na serwerze: `sudo ufw status`
- Sprawdź czy SSH działa: `sudo systemctl status ssh`

---

## 🔐 Jeśli nie możesz się połączyć

### Problem: "Connection timed out"

**Rozwiązanie:**
```bash
# Na serwerze sprawdź:
sudo systemctl status ssh
sudo ufw status
sudo ufw allow 22/tcp
```

### Problem: "Permission denied"

**Rozwiązanie:**
- Sprawdź czy używasz poprawnej nazwy użytkownika
- Sprawdź hasło: `passwd` (na serwerze)
- Sprawdź czy PasswordAuthentication jest włączone:
```bash
sudo grep PasswordAuthentication /etc/ssh/sshd_config
# Powinno być: PasswordAuthentication yes
```

### Problem: "Host key verification failed"

**Rozwiązanie:**
```powershell
# Na Windows usuń stary klucz:
ssh-keygen -R IP_ADRES
```

---

## 📱 Przykładowa sesja

```powershell
# Na Windows PowerShell:
PS C:\Users\pawlo> ssh ubuntu@192.168.1.100

The authenticity of host '192.168.1.100 (192.168.1.100)' can't be established.
ED25519 key fingerprint is SHA256:xxxxx...
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
Warning: Permanently added '192.168.1.100' (ED25519) to the list of known hosts.

ubuntu@192.168.1.100's password: ********

Welcome to Ubuntu 24.04 LTS...
Last login: ...

ubuntu@server:~$  # ← JESTEŚ ZALOGOWANY!
```

---

## 💡 Wskazówki

### 1. Zapisz połączenie w pliku SSH config (opcjonalnie)

Na Windows utwórz plik: `C:\Users\pawlo\.ssh\config`

```ssh-config
Host myserver
    HostName 192.168.1.100
    User ubuntu
    Port 22
```

Potem możesz się łączyć krócej:
```powershell
ssh myserver
```

### 2. Klucz SSH zamiast hasła (zalecane)

Na Windows PowerShell:
```powershell
# Wygeneruj klucz
ssh-keygen -t ed25519

# Skopiuj na serwer
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh uzytkownik@IP_ADRES "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Teraz możesz się logować bez hasła!

---

## ✅ Checklist przed połączeniem

- [ ] Znam adres IP serwera (`hostname -I`)
- [ ] Znam nazwę użytkownika (`whoami`)
- [ ] Mam hasło użytkownika
- [ ] SSH działa na serwerze (`sudo systemctl status ssh`)
- [ ] Firewall przepuszcza port 22 (`sudo ufw status`)
- [ ] Mam PowerShell/Terminal otwarty na Windows

---

## 🚀 Gdy już jesteś połączony

Po zalogowaniu możesz:

```bash
# Sprawdzić gdzie jesteś
pwd

# Zobaczyć zawartość katalogu
ls -la

# Sprawdzić status systemu
sudo systemctl status ssh

# Uruchomić pełną konfigurację VPS
sudo bash setup-vps.sh
```

**Powodzenia!** 🎉






