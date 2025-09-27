#!/usr/bin/env python3
"""
Celery Security Test
Testuje czy Celery worker działa z bezpiecznym użytkownikiem
"""

import os
import subprocess
import time
import logging
from celery import Celery

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_celery_user_security():
    """Testuje bezpieczeństwo użytkownika Celery"""

    print("🔒 Test bezpieczeństwa Celery...")

    # Sprawdź czy Celery worker działa
    try:
        # Sprawdź procesy Celery
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        celery_processes = [line for line in result.stdout.split(
            '\n') if 'celery' in line.lower()]

        print(f"📊 Znaleziono {len(celery_processes)} procesów Celery:")

        for process in celery_processes:
            if process.strip():
                parts = process.split()
                if len(parts) >= 2:
                    user = parts[0]
                    pid = parts[1]
                    command = ' '.join(parts[10:])

                    if user == 'root':
                        print(f"❌ BŁĄD: Proces {pid} działa jako ROOT!")
                        print(f"   Komenda: {command}")
                        return False
                    else:
                        print(
                            f"✅ OK: Proces {pid} działa jako użytkownik: {user}")

        return True

    except Exception as e:
        print(f"❌ Błąd podczas testowania: {e}")
        return False


def test_celery_connection():
    """Testuje połączenie z Celery"""

    print("\n🔗 Test połączenia z Celery...")

    try:
        # Konfiguracja Celery
        app = Celery('test')
        app.config_from_object({
            'broker_url': 'redis://:dev_password@localhost:6379/0',
            'result_backend': 'redis://:dev_password@localhost:6379/0',
        })

        # Test połączenia
        inspect = app.control.inspect()
        stats = inspect.stats()

        if stats:
            print("✅ Połączenie z Celery działa!")
            for worker, stat in stats.items():
                print(f"   Worker: {worker}")
                print(
                    f"   Pool: {stat.get('pool', {}).get('implementation', 'unknown')}")
        else:
            print("❌ Brak aktywnych workerów Celery")
            return False

        return True

    except Exception as e:
        print(f"❌ Błąd połączenia z Celery: {e}")
        return False


def test_celery_task():
    """Testuje wykonanie taska Celery"""

    print("\n⚡ Test wykonania taska...")

    try:
        # Konfiguracja Celery
        app = Celery('test')
        app.config_from_object({
            'broker_url': 'redis://:dev_password@localhost:6379/0',
            'result_backend': 'redis://:dev_password@localhost:6379/0',
        })

        # Definicja prostego taska
        @app.task
        def test_task():
            return f"Task wykonany przez użytkownika: {os.getuid()}"

        # Wykonaj task
        result = test_task.delay()

        # Czekaj na wynik
        try:
            task_result = result.get(timeout=10)
            print(f"✅ Task wykonany pomyślnie: {task_result}")
            return True
        except Exception as e:
            print(f"❌ Błąd wykonania taska: {e}")
            return False

    except Exception as e:
        print(f"❌ Błąd podczas testowania taska: {e}")
        return False


def check_docker_containers():
    """Sprawdza kontenery Docker"""

    print("\n🐳 Sprawdzanie kontenerów Docker...")

    try:
        # Sprawdź kontenery
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'],
                                capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Kontenery Docker:")
            print(result.stdout)
        else:
            print("❌ Błąd podczas sprawdzania kontenerów")
            return False

        return True

    except Exception as e:
        print(f"❌ Błąd: {e}")
        return False


def main():
    """Główna funkcja testowa"""

    print("🚀 Uruchamianie testów bezpieczeństwa Celery...\n")

    tests = [
        ("Bezpieczeństwo użytkownika", test_celery_user_security),
        ("Połączenie z Celery", test_celery_connection),
        ("Wykonanie taska", test_celery_task),
        ("Kontenery Docker", check_docker_containers),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Test: {test_name}")
        print('='*50)

        try:
            result = test_func()
            results.append((test_name, result))

            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")

        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))

    # Podsumowanie
    print(f"\n{'='*50}")
    print("📊 PODSUMOWANIE TESTÓW")
    print('='*50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")

    print(f"\nWynik: {passed}/{total} testów przeszło pomyślnie")

    if passed == total:
        print("🎉 Wszystkie testy przeszły! Celery jest bezpiecznie skonfigurowany.")
        return True
    else:
        print("⚠️  Niektóre testy nie przeszły. Sprawdź konfigurację.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
