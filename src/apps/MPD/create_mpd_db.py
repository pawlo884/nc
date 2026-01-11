import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


# Ładowanie zmiennych środowiskowych
load_dotenv('.env.dev')

# Pobieranie parametrów połączenia
db_host = os.getenv("MPD_DB_HOST")
db_port = os.getenv("MPD_DB_PORT")
db_name = os.getenv("MPD_DB_NAME")
db_user = os.getenv("MPD_DB_USER")
db_password = os.getenv("MPD_DB_PASSWORD")


def create_database():
    try:
        # Połączenie z domyślną bazą danych postgres
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Sprawdzenie czy baza danych już istnieje
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()

        if not exists:
            # Tworzenie bazy danych
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"Utworzono bazę danych {db_name}")
        else:
            print(f"Baza danych {db_name} już istnieje")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Błąd podczas tworzenia bazy danych: {e}")
        raise


def create_tables():
    try:
        # Połączenie z nowo utworzoną bazą danych
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        cursor = conn.cursor()

        # Tworzenie tabel
        from defs_db import create_tables_if_not_exist
        create_tables_if_not_exist(conn)

        print("Tabele zostały utworzone pomyślnie")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Błąd podczas tworzenia tabel: {e}")
        raise


if __name__ == "__main__":
    print("Rozpoczynam tworzenie bazy danych MPD...")
    create_database()
    create_tables()
    print("Proces tworzenia bazy danych MPD zakończony.") 