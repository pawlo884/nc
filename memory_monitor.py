#!/usr/bin/env python3
"""
Skrypt do monitorowania zużycia pamięci przez aplikację Django.
Pomaga w identyfikacji memory leaks i optymalizacji.
"""

import psutil
import os
import time
import logging
from datetime import datetime

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('memory_monitor.log'),
        logging.StreamHandler()
    ]
)


def get_memory_usage():
    """Pobiera informacje o zużyciu pamięci."""
    process = psutil.Process()
    memory_info = process.memory_info()

    return {
        'rss': memory_info.rss / 1024 / 1024,  # MB
        'vms': memory_info.vms / 1024 / 1024,  # MB
        'percent': process.memory_percent(),
        'num_threads': process.num_threads(),
        'num_fds': process.num_fds() if hasattr(process, 'num_fds') else 0
    }


def monitor_memory():
    """Monitoruje zużycie pamięci i loguje ostrzeżenia."""

    while True:
        try:
            memory = get_memory_usage()

            # Loguj co 5 minut
            if int(time.time()) % 300 == 0:
                logging.info(f"Memory usage: RSS={memory['rss']:.1f}MB, "
                             f"VMS={memory['vms']:.1f}MB, "
                             f"Percent={memory['percent']:.1f}%, "
                             f"Threads={memory['num_threads']}")

            # Ostrzeżenie przy wysokim zużyciu pamięci
            if memory['percent'] > 80:
                logging.warning(
                    f"WYSOKIE ZUŻYCIE PAMIĘCI: {memory['percent']:.1f}%")

            # Ostrzeżenie przy zbyt wielu wątkach
            if memory['num_threads'] > 100:
                logging.warning(f"ZBYT WIELE WĄTKÓW: {memory['num_threads']}")

            time.sleep(60)  # Sprawdzaj co minutę

        except KeyboardInterrupt:
            logging.info("Zatrzymano monitorowanie pamięci.")
            break
        except Exception as e:
            logging.error(f"Błąd podczas monitorowania: {e}")
            time.sleep(60)


if __name__ == "__main__":
    logging.info("Rozpoczęto monitorowanie pamięci...")
    monitor_memory()
