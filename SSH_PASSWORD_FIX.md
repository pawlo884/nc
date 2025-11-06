# 🔐 Rozwiązywanie problemu z hasłem SSH

Jeśli hasło wydaje się nieprawidłowe, sprawdźmy co może być nie tak.

---

## 🔍 Krok 1: Sprawdź na serwerze (jesli masz dostęp fizyczny)

### 1.1. Sprawdź czy użytkownik istnieje i ma hasło

```bash
# Sprawdź użytkowników
cat /etc/passwd | grep uzytkownik

# Sprawdź czy możesz zalogować się lokalnie
su - uzytkownik
# Wpisz hasło - jeśli tutaj nie działa, problem jest z hasłem
```

### 1.2. Zmień hasło użytkownika

```bash
# Zmień hasło (z root/sudo)
sudo passwd uzytkownik

# Lub zmień swoje hasło (jeśli jesteś zalogowany jako ten użytkownik)
passwd
```

**WAŻNE:**
- Hasło nie będzie widoczne podczas wpisywania
- Wpisz hasło 2 razy (potwierdzenie)
- Użyj silnego hasła (min. 8 znaków, litery, cyfry)

### 1.3. Sprawdź czy hasło jest aktywne

```bash
# Sprawdź status konta użytkownika
sudo chage -l uzytkownik

# Sprawdź czy konto nie jest wygasłe
sudo passwd -S uzytkownik
```

---

## 🔧 Krok 2: Sprawdź konfigurację SSH

### 2.1. Sprawdź czy PasswordAuthentication jest włączone

```bash
# Sprawdź konfigurację SSH
sudo grep PasswordAuthentication /etc/ssh/sshd_config
```

**Musi być:**
```
PasswordAuthentication yes
```

**NIE może być:**
```
PasswordAuthentication no
```

### 2.2. Jeśli PasswordAuthentication jest wyłączone:

```bash
# Edytuj konfigurację
sudo nano /etc/ssh/sshd_config

# Znajdź linię (usuń # jeśli jest):
#PasswordAuthentication yes
# I upewnij się że jest:
PasswordAuthentication yes

# Zapisz (Ctrl+O, Enter, Ctrl+X)

# Zrestartuj SSH
sudo systemctl restart ssh
```

### 2.3. Sprawdź inne ważne opcje SSH

```bash
# Sprawdź pełną konfigurację
sudo grep -E "PasswordAuthentication|PubkeyAuthentication|PermitRootLogin|AllowUsers" /etc/ssh/sshd_config
```

**Powinno być:**
```
PasswordAuthentication yes
PubkeyAuthentication yes
PermitRootLogin no
# AllowUsers - opcjonalne, jeśli jest, twój użytkownik musi być na liście
```

### 2.4. Jeśli AllowUsers blokuje dostęp:

```bash
# Sprawdź czy twój użytkownik jest dozwolony
sudo grep AllowUsers /etc/ssh/sshd_config

# Jeśli jest lista i twojego użytkownika nie ma:
sudo nano /etc/ssh/sshd_config

# Dodaj swojego użytkownika:
AllowUsers uzytkownik1 uzytkownik2 twoj_uzytkownik

# Zrestartuj SSH
sudo systemctl restart ssh
```

---

## 🔄 Krok 3: Reset hasła (jeśli masz dostęp fizyczny)

### 3.1. Zmień hasło jako root/sudo

```bash
# Jako root lub z sudo
sudo passwd uzytkownik

# Wprowadź nowe hasło 2 razy
```

### 3.2. Sprawdź czy hasło się zmieniło

```bash
# Przetestuj lokalnie
su - uzytkownik
# Wpisz nowe hasło - powinno działać
exit
```

---

## 🧪 Krok 4: Test połączenia

### 4.1. Z Windows PowerShell

```powershell
# Połącz się (użyj nowego hasła)
ssh uzytkownik@IP_ADRES

# Jeśli dalej nie działa, sprawdź szczegóły:
ssh -v uzytkownik@IP_ADRES
```

Flaga `-v` pokaże szczegóły i pomoże zdiagnozować problem.

### 4.2. Sprawdź logi SSH na serwerze

```bash
# Zobacz ostatnie próby logowania
sudo tail -f /var/log/auth.log

# Lub na nowszych systemach:
sudo journalctl -u ssh -f
```

Teraz spróbuj połączyć się z Windows - zobaczysz co SSH zapisuje w logach.

---

## ⚠️ Najczęstsze błędy i rozwiązania

### Błąd: "Permission denied (password)"

**Możliwe przyczyny:**
1. ❌ Złe hasło
2. ❌ PasswordAuthentication wyłączone
3. ❌ Użytkownik zablokowany w AllowUsers
4. ❌ Konto wygasłe

**Rozwiązanie:**
```bash
# 1. Sprawdź konfigurację
sudo grep PasswordAuthentication /etc/ssh/sshd_config

# 2. Włącz jeśli wyłączone
sudo nano /etc/ssh/sshd_config
# Ustaw: PasswordAuthentication yes
sudo systemctl restart ssh

# 3. Zmień hasło
sudo passwd uzytkownik

# 4. Sprawdź AllowUsers
sudo grep AllowUsers /etc/ssh/sshd_config
```

### Błąd: "Authentication failed"

**Możliwe przyczyny:**
1. ❌ Złe hasło (sprawdź wielkie/małe litery, cyfry)
2. ❌ Klawiatura ustawiona na inną lokalizację (QWERTY vs QWERTZ)
3. ❌ Hasło zawiera specjalne znaki które są źle interpretowane

**Rozwiązanie:**
```bash
# Ustaw proste hasło bez specjalnych znaków
sudo passwd uzytkownik
# Użyj tylko liter i cyfr (bez !@#$% itp.)
```

### Błąd: "Too many authentication failures"

**Rozwiązanie:**
```bash
# Poczekaj chwilę (fail2ban zablokował)
# Lub sprawdź fail2ban:
sudo fail2ban-client status sshd

# Odblokuj swoje IP:
sudo fail2ban-client set sshd unban IP_ADRES
```

---

## 🔐 Krok 5: Ustaw nowe, proste hasło

```bash
# Na serwerze wykonaj:
sudo passwd uzytkownik
```

**Zasady dobrego hasła:**
- ✅ Minimum 8 znaków
- ✅ Co najmniej jedna wielka litera
- ✅ Co najmniej jedna mała litera  
- ✅ Co najmniej jedna cyfra
- ⚠️ Unikaj specjalnych znaków (może powodować problemy z SSH)

**Przykład dobrego hasła:**
```
MyServer2024
Django123
UbuntuPass99
```

**NIE używaj:**
- Słownika (password, admin, 12345)
- Powtórzeń (aaaaa, 11111)
- Tylko cyfr lub tylko liter

---

## 🔄 Szybki fix - pełna procedura

Jeśli nic nie działa, wykonaj to krok po kroku:

```bash
# 1. Zmień hasło
sudo passwd uzytkownik

# 2. Upewnij się że PasswordAuthentication jest włączone
sudo sed -i 's/#PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
sudo grep -q "^PasswordAuthentication yes" /etc/ssh/sshd_config || echo "PasswordAuthentication yes" | sudo tee -a /etc/ssh/sshd_config

# 3. Zrestartuj SSH
sudo systemctl restart ssh

# 4. Sprawdź status
sudo systemctl status ssh

# 5. Sprawdź czy port 22 jest otwarty
sudo ufw allow 22/tcp
sudo ufw status
```

---

## 🧪 Test końcowy

Po wykonaniu powyższych kroków:

1. **Z Windows PowerShell:**
```powershell
ssh uzytkownik@IP_ADRES
```

2. **Wprowadź nowe hasło** (pamiętaj - nie będzie widoczne podczas wpisywania)

3. **Jeśli nadal nie działa**, sprawdź logi w czasie rzeczywistym:
```bash
# Na serwerze:
sudo tail -f /var/log/auth.log
```

Następnie spróbuj połączyć się z Windows - zobaczysz dokładnie co SSH zapisuje.

---

## 💡 Alternatywa: Klucz SSH (bez hasła)

Jeśli ciągle problemy z hasłem, użyj klucza SSH:

**Na Windows PowerShell:**
```powershell
# 1. Wygeneruj klucz (jeśli nie masz)
ssh-keygen -t ed25519

# 2. Skopiuj klucz na serwer (będzie potrzebne hasło raz)
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh uzytkownik@IP_ADRES "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Po skopiowaniu klucza będziesz mógł się logować bez hasła!

---

## ✅ Checklist rozwiązywania problemu

- [ ] Zmieniono hasło (`sudo passwd uzytkownik`)
- [ ] Przetestowano hasło lokalnie (`su - uzytkownik`)
- [ ] Sprawdzono PasswordAuthentication w SSH (musi być `yes`)
- [ ] Zrestartowano SSH (`sudo systemctl restart ssh`)
- [ ] Sprawdzono AllowUsers (jeśli istnieje, użytkownik musi być na liście)
- [ ] Sprawdzono firewall (`sudo ufw allow 22/tcp`)
- [ ] Sprawdzono logi SSH podczas próby połączenia

---

**Spróbuj teraz zmienić hasło i połączyć się ponownie!** 🚀





