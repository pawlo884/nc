#!/usr/bin/env python
"""
Skrypt do utworzenia tabeli full_change_files w bazie danych MPD
"""

from MPD.sql.create_full_change_files import sql_content
from django.db import connection
import os
import sys
import django
from pathlib import Path

# Dodaj ścieżkę do projektu Django
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Ustaw zmienne środowiskowe Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')

# Inicjalizuj Django
django.setup()


def create_full_change_files_table():
    """Tworzy tabelę full_change_files w bazie danych MPD"""

    print("🔧 Tworzenie tabeli full_change_files...")

    try:
        with connection.cursor() as cursor:
            # Wykonaj skrypt SQL
            cursor.execute(sql_content)
            connection.commit()

        print("✅ Tabela full_change_files została utworzona pomyślnie!")
        print("📋 Tabela zawiera:")
        print("   - id: Unikalny identyfikator rekordu")
        print("   - filename: Nazwa pliku (np. full_change2025-08-25T10-30-45.xml)")
        print("   - timestamp: Timestamp z nazwy pliku (YYYY-MM-DDTHH-MM-SS)")
        print("   - created_at: Data i czas utworzenia pliku")
        print("   - bucket_url: URL do pliku w buckecie S3/DO Spaces")
        print("   - local_path: Ścieżka do lokalnego pliku")
        print("   - file_size: Rozmiar pliku w bajtach")
        print("   - created_at_record: Data i czas utworzenia rekordu w bazie danych")

        return True

    except Exception as e:
        print(f"❌ Błąd podczas tworzenia tabeli full_change_files: {str(e)}")
        return False


if __name__ == "__main__":
    success = create_full_change_files_table()
    if success:
        print("\n🎉 Skrypt zakończony pomyślnie!")
        print("💡 Możesz teraz uruchomić eksport full_change.xml z datą w nazwie")
    else:
        print("\n💥 Skrypt zakończony z błędem!")
        sys.exit(1)
