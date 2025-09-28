#!/usr/bin/env python3
"""
Skrypt do naprawy plików statycznych admin_interface
"""

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import execute_from_command_line
import os
import sys
import django
from pathlib import Path

# Dodaj ścieżkę do Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.prod')

# Inicjalizuj Django
django.setup()


def fix_static_files():
    """Naprawia pliki statyczne admin_interface"""
    print("🔧 Naprawianie plików statycznych admin_interface...")

    try:
        # 1. Wyczyść istniejące pliki statyczne
        print("1. Czyszczenie istniejących plików statycznych...")
        execute_from_command_line(
            ['manage.py', 'collectstatic', '--clear', '--noinput'])

        # 2. Sprawdź czy admin_interface jest w INSTALLED_APPS
        print("2. Sprawdzanie konfiguracji admin_interface...")
        if 'admin_interface' not in settings.INSTALLED_APPS:
            print("❌ admin_interface nie jest w INSTALLED_APPS!")
            return False

        # 3. Sprawdź pliki admin_interface
        print("3. Sprawdzanie plików admin_interface...")
        admin_static_paths = [
            'admin_interface/css/themes/',
            'admin_interface/js/',
            'admin_interface/css/base.css'
        ]

        static_root = settings.STATIC_ROOT
        missing_files = []

        for path in admin_static_paths:
            full_path = os.path.join(static_root, path)
            if not os.path.exists(full_path):
                missing_files.append(path)
                print(f"❌ Brak: {path}")
            else:
                print(f"✅ OK: {path}")

        if missing_files:
            print("\n🔧 Próba naprawy...")

            # Sprawdź czy pliki są w źródłach
            for finder in finders.get_finders():
                for path, storage in finder.list([]):
                    if 'admin_interface' in path:
                        print(f"📁 Znaleziono: {path}")

            # Ponownie zbierz pliki statyczne
            print("4. Ponowne zbieranie plików statycznych...")
            execute_from_command_line(
                ['manage.py', 'collectstatic', '--noinput'])

            # Sprawdź ponownie
            print("5. Sprawdzanie po naprawie...")
            for path in admin_static_paths:
                full_path = os.path.join(static_root, path)
                if os.path.exists(full_path):
                    print(f"✅ Naprawione: {path}")
                else:
                    print(f"❌ Nadal brak: {path}")

        print("\n✅ Naprawa plików statycznych zakończona")
        return True

    except Exception as e:
        print(f"❌ Błąd podczas naprawy: {e}")
        return False


def check_static_configuration():
    """Sprawdza konfigurację plików statycznych"""
    print("\n🔍 Sprawdzanie konfiguracji plików statycznych...")

    print(f"STATIC_URL: {settings.STATIC_URL}")
    print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
    print(f"STATICFILES_DIRS: {settings.STATICFILES_DIRS}")
    print(f"STATICFILES_STORAGE: {settings.STATICFILES_STORAGE}")

    # Sprawdź czy STATIC_ROOT istnieje
    if os.path.exists(settings.STATIC_ROOT):
        print(f"✅ STATIC_ROOT istnieje: {settings.STATIC_ROOT}")
    else:
        print(f"❌ STATIC_ROOT nie istnieje: {settings.STATIC_ROOT}")
        os.makedirs(settings.STATIC_ROOT, exist_ok=True)
        print(f"📁 Utworzono STATIC_ROOT: {settings.STATIC_ROOT}")


if __name__ == "__main__":
    print("🛠️  NARZĘDZIE NAPRAWY PLIKÓW STATYCZNYCH")
    print("=" * 50)

    check_static_configuration()
    success = fix_static_files()

    if success:
        print("\n🎉 Naprawa zakończona pomyślnie!")
    else:
        print("\n❌ Naprawa nie powiodła się!")
        sys.exit(1)
