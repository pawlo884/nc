#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Skrypt do testowania połączenia przez SSH tunnel.
Sprawdza dostępność portu 5434 w kontenerze postgres-ssh-tunnel.
"""
import subprocess
import sys
import time
import os

# Ustaw kodowanie UTF-8 dla Windows
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

def check_container_status():
    """Sprawdza status kontenera postgres-ssh-tunnel."""
    print("=" * 60)
    print("1. Sprawdzanie statusu kontenera postgres-ssh-tunnel...")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=postgres-ssh-tunnel", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"[OK] Kontener działa: {result.stdout.strip()}")
            return True
        else:
            print("[ERROR] Kontener nie jest uruchomiony")
            print("  Uruchom: docker-compose -f docker-compose.dev.yml up -d postgres-ssh-tunnel")
            return False
    except Exception as e:
        print(f"[ERROR] Blad sprawdzania statusu: {e}")
        return False

def check_port_in_container():
    """Sprawdza czy port 5434 jest dostępny w kontenerze."""
    print("\n" + "=" * 60)
    print("2. Sprawdzanie portu 5434 w kontenerze...")
    print("=" * 60)
    
    try:
        # Sprawdź czy port jest nasłuchiwany w kontenerze
        result = subprocess.run(
            ["docker", "exec", "postgres-ssh-tunnel", "nc", "-z", "localhost", "5434"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("[OK] Port 5434 jest dostepny w kontenerze")
            return True
        else:
            print("[ERROR] Port 5434 nie jest dostepny")
            print("  Sprawdź logi: docker-compose -f docker-compose.dev.yml logs postgres-ssh-tunnel")
            return False
    except subprocess.TimeoutExpired:
        print("[ERROR] Timeout podczas sprawdzania portu")
        return False
    except Exception as e:
        print(f"[ERROR] Blad sprawdzania portu: {e}")
        return False

def check_port_from_web_container():
    """Sprawdza czy kontener web może połączyć się z tunnel."""
    print("\n" + "=" * 60)
    print("3. Sprawdzanie połączenia z kontenera web do tunnel...")
    print("=" * 60)
    
    try:
        # Sprawdź czy kontener web może połączyć się z postgres-ssh-tunnel:5434
        result = subprocess.run(
            ["docker", "exec", "nc-project-web-1", "nc", "-z", "postgres-ssh-tunnel", "5434"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("[OK] Kontener web moze polaczyc sie z postgres-ssh-tunnel:5434")
            return True
        else:
            print("[ERROR] Kontener web nie moze polaczyc sie z tunnel")
            print("  Sprawdź czy kontener web jest uruchomiony")
            return False
    except subprocess.TimeoutExpired:
        print("[ERROR] Timeout podczas sprawdzania polaczenia")
        return False
    except Exception as e:
        print(f"[ERROR] Blad sprawdzania polaczenia: {e}")
        print(f"  Możliwe że kontener web nie jest uruchomiony lub ma inną nazwę")
        return False

def check_env_variables():
    """Sprawdza czy zmienne środowiskowe są ustawione."""
    print("\n" + "=" * 60)
    print("0. Sprawdzanie zmiennych środowiskowych...")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ["docker", "exec", "postgres-ssh-tunnel", "env"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            env_output = result.stdout
            has_password = "SSH_PASSWORD" in env_output and env_output.count("SSH_PASSWORD=") > 0
            has_key = "SSH_KEY" in env_output and len([line for line in env_output.split('\n') if 'SSH_KEY=' in line and line.strip() != 'SSH_KEY=']) > 0
            has_host = "SSH_HOST" in env_output
            has_user = "SSH_USER" in env_output
            
            if has_password:
                print("[OK] SSH_PASSWORD jest ustawione")
            elif has_key:
                print("[OK] SSH_KEY jest ustawione")
            else:
                print("[ERROR] SSH_PASSWORD lub SSH_KEY nie sa ustawione")
                print("  Dodaj do .env.dev:")
                print("    SSH_PASSWORD=twoje_haslo")
                print("  LUB")
                print("    SSH_KEY=\"-----BEGIN OPENSSH PRIVATE KEY-----...\"")
                return False
            
            if has_host:
                host_line = [line for line in env_output.split('\n') if 'SSH_HOST=' in line][0]
                print(f"[OK] SSH_HOST: {host_line.split('=', 1)[1]}")
            else:
                print("[ERROR] SSH_HOST nie jest ustawione")
                return False
                
            if has_user:
                user_line = [line for line in env_output.split('\n') if 'SSH_USER=' in line][0]
                print(f"[OK] SSH_USER: {user_line.split('=', 1)[1]}")
            else:
                print("[ERROR] SSH_USER nie jest ustawione")
                return False
            
            return True
        else:
            print("[ERROR] Nie mozna sprawdzic zmiennych srodowiskowych")
            return False
    except Exception as e:
        print(f"[ERROR] Blad sprawdzania zmiennych: {e}")
        return False

def show_logs():
    """Pokazuje ostatnie logi z kontenera."""
    print("\n" + "=" * 60)
    print("Ostatnie logi z kontenera postgres-ssh-tunnel:")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "logs", "--tail=20", "postgres-ssh-tunnel"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("Nie można pobrać logów")
    except Exception as e:
        print(f"Błąd pobierania logów: {e}")

def main():
    """Główna funkcja."""
    print("\n" + "=" * 60)
    print("TEST POŁĄCZENIA SSH TUNNEL")
    print("=" * 60 + "\n")
    
    # Sprawdź zmienne środowiskowe
    env_ok = check_env_variables()
    
    if not env_ok:
        print("\n⚠️  Najpierw ustaw zmienne środowiskowe w .env.dev!")
        show_logs()
        return 1
    
    # Sprawdź status kontenera
    container_ok = check_container_status()
    
    if not container_ok:
        show_logs()
        return 1
    
    # Sprawdź port w kontenerze
    port_ok = check_port_in_container()
    
    if not port_ok:
        show_logs()
        return 1
    
    # Sprawdź połączenie z kontenera web
    connection_ok = check_port_from_web_container()
    
    # Podsumowanie
    print("\n" + "=" * 60)
    print("PODSUMOWANIE")
    print("=" * 60)
    
    if env_ok and container_ok and port_ok:
        print("[OK] SSH Tunnel dziala poprawnie!")
        if connection_ok:
            print("[OK] Kontener web moze polaczyc sie z tunnel")
            print("\nMozesz teraz przetestowac polaczenie z baza danych:")
            print("  docker-compose -f docker-compose.dev.yml exec web python scripts/check_db_connections.py")
            return 0
        else:
            print("[WARNING] Tunnel dziala, ale kontener web nie moze sie polaczyc")
            print("   Sprawdz czy kontener web jest uruchomiony")
            return 1
    else:
        print("[ERROR] SSH Tunnel nie dziala poprawnie")
        show_logs()
        return 1

if __name__ == '__main__':
    sys.exit(main())
