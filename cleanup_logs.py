#!/usr/bin/env python3
"""
Skrypt do czyszczenia starych logów i optymalizacji pamięci.
Uruchamiaj regularnie (np. codziennie) aby zapobiec akumulacji logów.
"""

import os
import glob
import time
from pathlib import Path


def cleanup_logs():
    """Czyści stare pliki logów i kompresuje duże pliki."""

    log_dir = Path("logs/matterhorn")

    if not log_dir.exists():
        print("Katalog logów nie istnieje.")
        return

    # Usuń pliki logów starsze niż 7 dni
    cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7 dni w sekundach

    removed_count = 0
    for log_file in log_dir.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                removed_count += 1
                print(f"Usunięto stary plik: {log_file}")
            except Exception as e:
                print(f"Błąd podczas usuwania {log_file}: {e}")

    # Sprawdź rozmiar aktualnego pliku logu
    main_log = log_dir / "import_all_by_one.log"
    if main_log.exists():
        size_mb = main_log.stat().st_size / (1024 * 1024)
        print(f"Aktualny rozmiar głównego pliku logu: {size_mb:.2f} MB")

        if size_mb > 10:  # Jeśli plik jest większy niż 10MB
            print("Plik logu jest bardzo duży. Rozważ restart aplikacji.")

    print(f"Zakończono czyszczenie. Usunięto {removed_count} plików.")


if __name__ == "__main__":
    cleanup_logs()
