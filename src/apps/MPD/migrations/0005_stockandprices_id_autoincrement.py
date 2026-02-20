# Sekwencja dla stock_and_prices.id - 0001 utworzył BigIntegerField bez auto-increment
# Przy świeżej bazie testowej brak sekwencji powodował IntegrityError

from django.db import migrations


def add_sequence(apps, schema_editor):
    """Dodaj sekwencję dla id w stock_and_prices (PostgreSQL). Używa połączenia z bazy migrowanej (--database)."""
    conn = schema_editor.connection
    if conn.vendor != 'postgresql':
        return
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE SEQUENCE IF NOT EXISTS stock_and_prices_id_seq;
            ALTER TABLE stock_and_prices ALTER COLUMN id
                SET DEFAULT nextval('stock_and_prices_id_seq');
            SELECT setval('stock_and_prices_id_seq',
                COALESCE((SELECT MAX(id) FROM stock_and_prices), 0) + 1);
        """)


def remove_sequence(apps, schema_editor):
    """Cofnij - usuń default z kolumny. Używa połączenia z bazy migrowanej (--database)."""
    conn = schema_editor.connection
    if conn.vendor != 'postgresql':
        return
    with conn.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE stock_and_prices ALTER COLUMN id DROP DEFAULT;
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0004_stockandprices_bigautofield'),
    ]

    operations = [
        migrations.RunPython(add_sequence, remove_sequence),
    ]
