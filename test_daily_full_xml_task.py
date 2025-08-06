#!/usr/bin/env python
"""
Test zadania Celery do generowania full.xml
"""
import os
import sys
import django

# Dodaj ścieżkę do projektu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Skonfiguruj Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.development')
django.setup()


def test_daily_full_xml_task():
    """Test zadania generate_daily_full_xml"""
    from MPD.tasks import generate_daily_full_xml

    print("🚀 Testowanie zadania generate_daily_full_xml...")
    print("⏰ Zadanie zostanie uruchomione synchronicznie (bez Celery)")

    try:
        # Uruchom zadanie bezpośrednio (synchronicznie)
        result = generate_daily_full_xml()

        print("\n📊 Wyniki zadania:")
        print(f"Status: {result.get('status', 'unknown')}")

        if result.get('status') == 'success':
            print(f"✅ Bucket URL: {result.get('bucket_url')}")
            print(f"📁 Lokalny plik: {result.get('local_path')}")
            print(f"⏱️ Czas wykonania: {result.get('execution_time')}")
        else:
            print(f"❌ Błąd: {result.get('message')}")

        return result

    except Exception as e:
        print(f"💥 Błąd podczas testowania: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_with_celery():
    """Test zadania przez Celery (asynchronicznie)"""
    from MPD.tasks import generate_daily_full_xml

    print("\n🔄 Testowanie zadania przez Celery...")
    print("📝 Uwaga: Wymaga uruchomionego Celery worker!")

    try:
        # Uruchom zadanie przez Celery
        task = generate_daily_full_xml.delay()

        print(f"🆔 Task ID: {task.id}")
        print("⏳ Zadanie zostało dodane do kolejki...")
        print("💡 Sprawdź logi Celery worker aby zobaczyć postęp")

        return task

    except Exception as e:
        print(f"💥 Błąd podczas dodawania do kolejki: {str(e)}")
        return None


if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TEST ZADANIA GENERATE_DAILY_FULL_XML")
    print("=" * 60)

    # Test synchroniczny
    result = test_daily_full_xml_task()

    # Test asynchroniczny (opcjonalny)
    print("\n" + "=" * 60)
    response = input("Czy chcesz przetestować przez Celery? (y/n): ")
    if response.lower() in ['y', 'yes', 'tak', 't']:
        task = test_with_celery()

    print("\n🎉 Test zakończony!")
