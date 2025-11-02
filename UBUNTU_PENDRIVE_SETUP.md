# 🚀 Instalacja Ubuntu na Pendrive

Przewodnik do przygotowania bootowalnego pendrive z Ubuntu dla serwera VPS.

## 📋 Potrzebne rzeczy

- Pendrive minimum **8 GB** (zalecane 16 GB lub więcej)
- Komputer z systemem Windows/Linux/Mac
- Dostęp do internetu

---

## 🪟 Windows (Rufus - zalecane)

### Krok 1: Pobierz Ubuntu Server
1. Idź na: https://ubuntu.com/download/server
2. Pobierz najnowszą wersję **Ubuntu Server LTS** (22.04 lub 24.04)
3. Plik będzie miał rozszerzenie `.iso` (około 2-3 GB)

### Krok 2: Pobierz Rufus
1. Idź na: https://rufus.ie/
2. Pobierz **Rufus** (portable wersja - nie wymaga instalacji)
3. Uruchom `rufus.exe`

### Krok 3: Przygotuj Pendrive w Rufus
1. **Podłącz pendrive** do komputera
2. **Otwórz Rufus**
3. **Urządzenie**: Wybierz swój pendrive (⚠️ UWAGA: wszystkie dane zostaną usunięte!)
4. **Wybór rozruchu**: Kliknij **WYBIERZ** i wybierz pobrany plik `.iso` Ubuntu
5. **Schemat partycji**: Zostaw **GPT**
6. **System docelowy**: Zostaw **UEFI (non CSM)**
7. **Nowa etykieta woluminu**: Możesz zmienić na np. "UBUNTU_SERVER"
8. Kliknij **START**

### Krok 4: Ostrzeżenie
- Rufus wyświetli ostrzeżenie że wszystkie dane na pendrive zostaną usunięte
- Jeśli masz ważne dane, **zrób backup!**
- Kliknij **OK**

### Krok 5: Oczekiwanie
- Rufus przygotuje pendrive (10-20 minut w zależności od szybkości USB)
- Gdy zobaczysz **GOTOWE**, pendrive jest gotowy!

---

## 🐧 Linux (dd - terminal)

### Krok 1: Pobierz Ubuntu Server
```bash
# Pobierz najnowszą wersję Ubuntu Server
wget https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso
```

### Krok 2: Sprawdź nazwę pendrive
```bash
# Podłącz pendrive, potem:
lsblk
# Znajdź swój pendrive (np. /dev/sdb lub /dev/sdc)
# ⚠️ BARDZO WAŻNE: Sprawdź czy to na pewno twój pendrive!
```

### Krok 3: Odmontuj pendrive (jeśli zamontowany)
```bash
# Zamień X na literę twojego pendrive (np. sdb)
sudo umount /dev/sdX*
```

### Krok 4: Zapisz obraz na pendrive
```bash
# Zamień X na literę twojego pendrive
# Zamień ścieżkę na ścieżkę do pobranego ISO
sudo dd if=/home/user/ubuntu-24.04-live-server-amd64.iso of=/dev/sdX bs=4M status=progress oflag=sync
```

**UWAGA**: 
- To może zająć 10-30 minut
- **NIE WYJMUJ** pendrive podczas zapisu!
- Gdy zobaczysz komunikat o liczbie zapisanych bloków, gotowe!

### Krok 5: Sprawdź czy się udało
```bash
# Sprawdź czy pendrive ma poprawną strukturę
sudo fdisk -l /dev/sdX
```

---

## 🍎 macOS (Balena Etcher lub terminal)

### Opcja 1: Balena Etcher (prostsze)
1. Pobierz: https://www.balena.io/etcher/
2. Zainstaluj i uruchom
3. Kliknij **Flash from file** → wybierz plik `.iso`
4. Kliknij **Select target** → wybierz pendrive
5. Kliknij **Flash!**
6. Poczekaj na zakończenie

### Opcja 2: Terminal (dd)
```bash
# 1. Pobierz Ubuntu Server ISO
# 2. Sprawdź identyfikator pendrive
diskutil list

# 3. Odmontuj pendrive (zamień N na numer dysku)
diskutil unmountDisk /dev/diskN

# 4. Zapisz obraz (zamień N i ścieżkę do ISO)
sudo dd if=/path/to/ubuntu-24.04-live-server-amd64.iso of=/dev/rdiskN bs=1m

# 5. Eject (opcjonalnie)
diskutil eject /dev/diskN
```

---

## ✅ Weryfikacja pendrive

### Windows
- Pendrive powinien mieć nazwę "UBUNTU_SERVER" (lub inną którą ustawiłeś)
- W Eksploratorze plików zobaczysz kilka plików/folderów Ubuntu

### Linux/Mac
```bash
# Sprawdź czy pendrive ma partycje
lsblk  # Linux
diskutil list  # Mac

# Powinny być widoczne partycje EFI i inne
```

---

## 🚀 Uruchomienie z pendrive

### Na maszynie VPS/komputerze:
1. **Podłącz pendrive** do komputera docelowego
2. **Włącz komputer**
3. **Wejdź do BIOS/UEFI** (zwykle F2, F10, F12, Delete podczas startu)
4. **Wybierz boot z USB/Pendrive**:
   - Znajdź opcję "Boot Order" lub "Boot Priority"
   - Ustaw USB/Pendrive jako **pierwszy**
   - Zapisz i wyjdź (Save & Exit)
5. **Komputer uruchomi się z Ubuntu**
6. Zobaczysz instalator Ubuntu Server

---

## 📝 Następne kroki po uruchomieniu z pendrive

### 1. Wybierz język i konfigurację początkową
- Język: **English** (zalecane dla VPS) lub Polski
- Układ klawiatury: wybierz swój

### 2. Konfiguracja sieci
- Jeśli masz dostęp do internetu przez kabel, Ubuntu automatycznie go wykryje
- Dla WiFi: wybierz sieć i wpisz hasło

### 3. Konfiguracja użytkownika
- **Nazwa użytkownika**: np. `admin` lub `deploy`
- **Hasło**: ustaw silne hasło (zapamiętaj!)
- **Serwer**: nazwa serwera (np. `nc-server`)

### 4. Instalacja
- Ubuntu zainstaluje się na dysk (jeśli wybierzesz opcję instalacji)
- Albo możesz użyć **Try Ubuntu** (live mode) do testów

### 5. Po instalacji
- Zrestartuj komputer
- Wyjmij pendrive (lub zmień kolejność bootowania w BIOS)
- Zaloguj się na świeżo zainstalowanym Ubuntu

---

## ⚙️ Po instalacji Ubuntu - kolejne kroki

Gdy masz już działający Ubuntu Server, uruchom skrypt konfiguracji:

```bash
# Pobierz skrypt konfiguracji VPS
wget https://raw.githubusercontent.com/pawlo884/nc/main/setup-vps.sh

# Lub skopiuj lokalnie jeśli masz
sudo bash setup-vps.sh
```

Skrypt `setup-vps.sh` automatycznie:
- Zainstaluje Docker i Docker Compose
- Skonfiguruje firewall
- Przygotuje użytkownika i katalogi
- Skonfiguruje bezpieczeństwo

---

## 🔧 Troubleshooting

### Pendrive się nie uruchamia
- Sprawdź czy BIOS wspiera boot z USB
- Upewnij się że pendrive jest zapisany poprawnie (spróbuj ponownie)
- Użyj innego portu USB (preferuj USB 2.0 zamiast 3.0)

### Błąd podczas zapisu w Rufus
- Upewnij się że pendrive jest odłączony od innych programów
- Zamknij Eksplorator plików z otwartym pendrive
- Spróbuj formatować pendrive najpierw (FAT32)

### Ubuntu się nie instaluje
- Sprawdź czy masz wystarczająco miejsca na dysku (min. 25 GB)
- Upewnij się że wybrałeś poprawny dysk do instalacji
- Sprawdź czy obraz ISO nie jest uszkodzony (porównaj hash MD5)

---

## 📚 Przydatne linki

- **Ubuntu Server Download**: https://ubuntu.com/download/server
- **Rufus**: https://rufus.ie/
- **Balena Etcher**: https://www.balena.io/etcher/
- **Dokumentacja Ubuntu**: https://ubuntu.com/server/docs

---

## ⚠️ WAŻNE UWAGI

1. **Backup danych**: Przed zapisem na pendrive, zrób backup wszystkich ważnych danych!
2. **Weryfikacja ISO**: Sprawdź hash MD5/SHA256 pobranego ISO (dla bezpieczeństwa)
3. **Test na pendrive**: Możesz uruchomić Ubuntu w trybie "Try Ubuntu" bez instalacji
4. **Dokumentacja**: Zapisz hasła i konfiguracje w bezpiecznym miejscu

---

**Gotowe?** Po przygotowaniu pendrive i uruchomieniu Ubuntu, użyj skryptu `setup-vps.sh` do pełnej konfiguracji!

