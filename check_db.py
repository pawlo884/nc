#!/usr/bin/env python
import os
import django

# Ustawienia Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nc.settings.dev')
django.setup()

from django.db import connection

def check_database():
    with connection.cursor() as cursor:
        # Sprawdź tabele matterhorn1
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename LIKE 'matterhorn1_%'
        """)
        tables = cursor.fetchall()
        print("Tabele matterhorn1:", [table[0] for table in tables])
        
        # Sprawdź migracje
        cursor.execute("""
            SELECT COUNT(*) 
            FROM django_migrations 
            WHERE app = 'matterhorn1'
        """)
        migrations_count = cursor.fetchone()[0]
        print("Liczba migracji matterhorn1:", migrations_count)
        
        # Sprawdź wszystkie tabele
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        all_tables = cursor.fetchall()
        print("Wszystkie tabele w bazie:", [table[0] for table in all_tables])

if __name__ == "__main__":
    check_database()
