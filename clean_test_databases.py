"""
Skrypt do czyszczenia testowych baz danych PostgreSQL
Uruchom: python clean_test_databases.py
"""
import os
import sys
from pathlib import Path

# Dodaj projekt do ścieżki
sys.path.insert(0, str(Path(__file__).parent))

# Załaduj ustawienia Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
import django
django.setup()

from django.db import connections
from django.core.management import call_command

def clean_test_databases():
    """Usuwa wszystkie testowe bazy danych"""
    print("🧹 Czyszczenie testowych baz danych...\n")
    
    # Lista testowych baz do usunięcia
    test_databases = [
        'test_zzz_default',
        'test_zzz_MPD',
        'test_zzz_matterhorn1',
        'test_zzz_web_agent',
    ]
    
    # Użyj połączenia do postgres (domyślna baza systemowa)
    try:
        # Pobierz konfigurację pierwszej bazy danych
        default_db = connections['default']
        db_config = default_db.settings_dict
        
        # Połącz się z bazą postgres (systemowa)
        import psycopg2
        conn = psycopg2.connect(
            host=db_config['HOST'],
            port=db_config['PORT'],
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            database='postgres'  # Połącz się z bazą systemową
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        for db_name in test_databases:
            try:
                # Sprawdź czy baza istnieje
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_name,)
                )
                exists = cursor.fetchone()
                
                if exists:
                    # Zakończ wszystkie połączenia do bazy
                    cursor.execute("""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = %s AND pid <> pg_backend_pid()
                    """, (db_name,))
                    
                    # Usuń bazę
                    cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
                    print(f"  ✅ {db_name} usunięta")
                else:
                    print(f"  ℹ️  {db_name} nie istnieje")
                    
            except Exception as e:
                print(f"  ⚠️  Błąd przy usuwaniu {db_name}: {e}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Czyszczenie zakończone!")
        print("\nMożesz teraz uruchomić testy:")
        print("  python manage.py test --settings=nc.settings.dev")
        
    except Exception as e:
        print(f"❌ Błąd: {e}")
        print("\nAlternatywnie, możesz usunąć bazy ręcznie przez psql:")
        print("  psql -U postgres -c 'DROP DATABASE IF EXISTS test_zzz_default;'")
        print("  psql -U postgres -c 'DROP DATABASE IF EXISTS test_zzz_MPD;'")
        print("  psql -U postgres -c 'DROP DATABASE IF EXISTS test_zzz_matterhorn1;'")
        print("  psql -U postgres -c 'DROP DATABASE IF EXISTS test_zzz_web_agent;'")
        sys.exit(1)

if __name__ == '__main__':
    clean_test_databases()

