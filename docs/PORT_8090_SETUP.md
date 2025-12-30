# Konfiguracja portu 8090 dla Nginx

## ⚠️ Zmiana portu z 8080 na 8090

Port 8080 był zajęty przez Apache (httpd) z EnterpriseDB PostgreSQL, więc zmieniono port Docker na **8090**.

## ✅ Co zostało zrobione:

1. **Docker Compose** - nginx mapowany na port `8090:80`
2. **Nginx konfiguracja** - bez zmian (działa na porcie 80 wewnątrz kontenera)
3. **Django settings** - bez zmian (już skonfigurowane dla zewnętrznych IP)

## ⚠️ Co musisz zrobić:

### 1. Port Forwarding w Routerze

Zmień port forwarding w routerze:

| Parametr                | Stara wartość   | Nowa wartość    |
| ----------------------- | --------------- | --------------- |
| **Port zewnętrzny**     | `8080`          | `8090`          |
| **Port wewnętrzny**     | `8080`          | `8090`          |
| **Wewnętrzny adres IP** | `192.168.50.63` | `192.168.50.63` |
| **Protokół**            | `TCP`           | `TCP`           |

### 2. Windows Firewall

Dodaj regułę firewall dla portu 8090 (jako Administrator):

```powershell
New-NetFirewallRule -DisplayName "Docker Nginx Port 8090" -Direction Inbound -LocalPort 8090 -Protocol TCP -Action Allow
```

Lub użyj skryptu:

```powershell
.\scripts\setup-port-8080.ps1
```

(Edytuj skrypt i zmień 8080 na 8090)

### 3. Test

Po skonfigurowaniu:

- **Lokalnie**: `http://localhost:8090/admin/` ✅
- **Z zewnątrz**: `http://212.127.93.27:8090/admin/` ✅

## 📝 Uwaga o porcie 8080

Port 8080 jest zajęty przez Apache (httpd) z EnterpriseDB PostgreSQL. Jeśli chcesz użyć portu 8080:

1. Zatrzymaj Apache (wymaga uprawnień administratora):

   ```powershell
   Stop-Process -Name httpd -Force
   ```

2. Zmień port z powrotem na 8080 w `docker-compose.dev.yml`

3. Zrestartuj nginx

## ✅ Po konfiguracji

Po dodaniu port forwarding i firewall dla portu 8090, dostęp będzie działał przez nginx reverse proxy.
