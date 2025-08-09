#!/usr/bin/env python
"""
Skrypt do konfiguracji periodic tasks dla eksportu XML
Uruchom: python setup_periodic_tasks.py
"""

from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import os
import sys
import django
from datetime import timedelta

# Dodaj ścieżkę do projektu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ustaw zmienne środowiskowe
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')

# Inicjalizuj Django
django.setup()


def setup_periodic_tasks():
    """Konfiguruj periodic tasks dla eksportu XML"""

    print("🚀 Konfiguruję periodic tasks dla eksportu XML...")

    # 1. Eksport full.xml co godzinę (przyrostowy)
    try:
        # Sprawdź czy task już istnieje
        full_xml_task, created = PeriodicTask.objects.get_or_create(
            name='Eksport full.xml co godzinę (przyrostowy)',
            defaults={
                'task': 'mpd.export_full_xml_hourly',
                'interval': IntervalSchedule.objects.get_or_create(
                    every=1,
                    period=IntervalSchedule.HOURS,
                )[0],
                'enabled': True,
                'description': 'Eksport przyrostowy full.xml co godzinę - nowe produkty od ostatniego eksportu'
            }
        )

        if created:
            print("✅ Utworzono task: Eksport full.xml co godzinę (przyrostowy)")
        else:
            print("ℹ️  Task już istnieje: Eksport full.xml co godzinę (przyrostowy)")

    except Exception as e:
        print(f"❌ Błąd podczas tworzenia taska full.xml: {e}")

    # 2. Eksport full_change.xml co godzinę (monitoring zmian)
    try:
        # Sprawdź czy task już istnieje
        full_change_task, created = PeriodicTask.objects.get_or_create(
            name='Eksport full_change.xml co godzinę (monitoring zmian)',
            defaults={
                'task': 'mpd.export_full_change_xml_hourly',
                'interval': IntervalSchedule.objects.get_or_create(
                    every=1,
                    period=IntervalSchedule.HOURS,
                )[0],
                'enabled': True,
                'description': 'Eksport przyrostowy full_change.xml co godzinę - monitoruje zmiany w wyeksportowanych produktach'
            }
        )

        if created:
            print(
                "✅ Utworzono task: Eksport full_change.xml co godzinę (monitoring zmian)")
        else:
            print(
                "ℹ️  Task już istnieje: Eksport full_change.xml co godzinę (monitoring zmian)")

    except Exception as e:
        print(f"❌ Błąd podczas tworzenia taska full_change.xml: {e}")

    # 3. Eksport pełny full.xml raz dziennie (opcjonalnie)
    try:
        # Sprawdź czy task już istnieje
        full_xml_daily_task, created = PeriodicTask.objects.get_or_create(
            name='Eksport pełny full.xml raz dziennie',
            defaults={
                'task': 'mpd.export_full_xml_full',
                'interval': IntervalSchedule.objects.get_or_create(
                    every=1,
                    period=IntervalSchedule.DAYS,
                )[0],
                'enabled': False,  # Domyślnie wyłączony
                'description': 'Eksport pełny full.xml raz dziennie - wszystkie produkty'
            }
        )

        if created:
            print("✅ Utworzono task: Eksport pełny full.xml raz dziennie (wyłączony)")
        else:
            print("ℹ️  Task już istnieje: Eksport pełny full.xml raz dziennie")

    except Exception as e:
        print(f"❌ Błąd podczas tworzenia taska pełnego full.xml: {e}")

    # 4. Eksport pełny full_change.xml raz dziennie (opcjonalnie)
    try:
        # Sprawdź czy task już istnieje
        full_change_daily_task, created = PeriodicTask.objects.get_or_create(
            name='Eksport pełny full_change.xml raz dziennie',
            defaults={
                'task': 'mpd.export_full_change_xml_full',
                'interval': IntervalSchedule.objects.get_or_create(
                    every=1,
                    period=IntervalSchedule.DAYS,
                )[0],
                'enabled': False,  # Domyślnie wyłączony
                'description': 'Eksport pełny full_change.xml raz dziennie - wszystkie produkty'
            }
        )

        if created:
            print(
                "✅ Utworzono task: Eksport pełny full_change.xml raz dziennie (wyłączony)")
        else:
            print("ℹ️  Task już istnieje: Eksport pełny full_change.xml raz dziennie")

    except Exception as e:
        print(f"❌ Błąd podczas tworzenia taska pełnego full_change.xml: {e}")

    print("\n📋 Podsumowanie skonfigurowanych tasków:")

    # Pokaż wszystkie taski
    tasks = PeriodicTask.objects.filter(task__startswith='mpd.')
    for task in tasks:
        status = "🟢 Włączony" if task.enabled else "🔴 Wyłączony"
        print(f"  {status} | {task.name}")
        print(f"    Task: {task.task}")
        print(f"    Interwał: {task.interval}")
        print(f"    Opis: {task.description}")
        print()

    print("🎯 Następne kroki:")
    print("  1. Uruchom Celery worker: celery -A nc worker -l info")
    print("  2. Uruchom Celery beat: celery -A nc beat -l info")
    print("  3. Sprawdź status w Django Admin -> Periodic Tasks")
    print("  4. Możesz włączyć/wyłączyć taski w panelu admina")


def cleanup_periodic_tasks():
    """Usuń wszystkie periodic tasks dla eksportu XML"""

    print("🧹 Usuwam periodic tasks dla eksportu XML...")

    try:
        deleted_count = PeriodicTask.objects.filter(
            task__startswith='mpd.'
        ).delete()[0]

        print(f"✅ Usunięto {deleted_count} tasków")

    except Exception as e:
        print(f"❌ Błąd podczas usuwania tasków: {e}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Konfiguracja periodic tasks dla eksportu XML')
    parser.add_argument('--cleanup', action='store_true',
                        help='Usuń wszystkie taski przed utworzeniem nowych')

    args = parser.parse_args()

    if args.cleanup:
        cleanup_periodic_tasks()
        print()

    setup_periodic_tasks()
