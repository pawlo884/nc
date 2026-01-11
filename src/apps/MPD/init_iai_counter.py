#!/usr/bin/env python3
"""
Skrypt do inicjalizacji tabeli iai_product_counter w istniejącej bazie danych MPD.
Uruchom ten skrypt, aby dodać tabelę licznika i ustawić jej początkową wartość.
"""

import os
import sys
import django
from django.db import connections

# Dodaj ścieżkę do projektu Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ustaw zmienne środowiskowe Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')

# Inicjalizuj Django
django.setup()


def init_iai_counter():
    """Inicjalizuje tabelę iai_product_counter"""
    try:
        with connections['MPD'].cursor() as cursor:
            # Sprawdź czy tabela już istnieje
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'iai_product_counter'
                );
            """)
            table_exists_result = cursor.fetchone()
            table_exists = table_exists_result[0] if table_exists_result else False

            if not table_exists:
                print("Tworzę tabelę iai_product_counter...")

                # Utwórz tabelę
                cursor.execute("""
                    CREATE TABLE iai_product_counter (
                        id INTEGER PRIMARY KEY DEFAULT 1,
                        counter_value BIGINT NOT NULL DEFAULT 0,
                        CONSTRAINT single_row CHECK (id = 1)
                    );
                """)

                print("Tabela iai_product_counter została utworzona.")
            else:
                print("Tabela iai_product_counter już istnieje.")

            # Sprawdź czy tabela product_variants istnieje i ma dane
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'product_variants'
                );
            """)
            variants_table_exists_result = cursor.fetchone()
            variants_table_exists = variants_table_exists_result[
                0] if variants_table_exists_result else False

            if variants_table_exists:
                # Sprawdź czy kolumna iai_product_id istnieje
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'product_variants' 
                        AND column_name = 'iai_product_id'
                    );
                """)
                column_exists_result = cursor.fetchone()
                column_exists = column_exists_result[0] if column_exists_result else False

                if column_exists:
                    # Pobierz maksymalną wartość iai_product_id
                    cursor.execute(
                        "SELECT MAX(iai_product_id) FROM product_variants")
                    max_iai_id_result = cursor.fetchone()
                    max_iai_id = max_iai_id_result[0] if max_iai_id_result else None
                    initial_value = (max_iai_id or 0) + 1
                    print(
                        f"Znaleziono maksymalną wartość iai_product_id: {max_iai_id}")
                    print(
                        f"Ustawiam początkową wartość licznika na: {initial_value}")
                else:
                    initial_value = 1
                    print(
                        "Kolumna iai_product_id nie istnieje, ustawiam wartość początkową na 1")
            else:
                initial_value = 1
                print(
                    "Tabela product_variants nie istnieje, ustawiam wartość początkową na 1")

            # Inicjalizuj lub zaktualizuj licznik
            cursor.execute("""
                INSERT INTO iai_product_counter (id, counter_value) 
                VALUES (1, %s) 
                ON CONFLICT (id) 
                DO UPDATE SET counter_value = EXCLUDED.counter_value
            """, [initial_value])

            # Sprawdź aktualną wartość
            cursor.execute("SELECT * FROM iai_product_counter")
            result = cursor.fetchone()
            print(f"Aktualna wartość licznika: {result}")

            connections['MPD'].commit()
            print("Inicjalizacja zakończona pomyślnie!")

    except Exception as e:
        print(f"Błąd podczas inicjalizacji: {e}")
        connections['MPD'].rollback()
        raise


if __name__ == "__main__":
    print("Rozpoczynam inicjalizację tabeli iai_product_counter...")
    init_iai_counter()
    print("Inicjalizacja zakończona.")
