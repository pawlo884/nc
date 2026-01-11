# Generated migration to rename stock_history table to matterhorn1_stock_history

from django.db import migrations


def rename_table_if_exists(apps, schema_editor):
    """Przemianuj tabelę stock_history na matterhorn1_stock_history jeśli istnieje"""
    db_alias = schema_editor.connection.alias
    with schema_editor.connection.cursor() as cursor:
        # Sprawdź czy tabela stock_history istnieje
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'stock_history'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        # Sprawdź czy matterhorn1_stock_history już istnieje
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'matterhorn1_stock_history'
            );
        """)
        new_table_exists = cursor.fetchone()[0]
        
        if table_exists and not new_table_exists:
            # Przemianuj tabelę
            cursor.execute('ALTER TABLE stock_history RENAME TO matterhorn1_stock_history;')
        elif not table_exists and not new_table_exists:
            # Tabela nie istnieje - Django utworzy ją przez AlterModelTable
            # Ale najpierw musimy utworzyć tabelę stock_history, a potem ją przemianować
            # Lub utworzyć bezpośrednio matterhorn1_stock_history
            # Użyjemy CreateModel zamiast tego - Django to zrobi automatycznie
            pass


def reverse_rename_table(apps, schema_editor):
    """Odwróć przemianowanie - zmień z powrotem na stock_history"""
    db_alias = schema_editor.connection.alias
    with schema_editor.connection.cursor() as cursor:
        # Sprawdź czy tabela matterhorn1_stock_history istnieje
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'matterhorn1_stock_history'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            # Sprawdź czy stock_history już nie istnieje
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'stock_history'
                );
            """)
            old_table_exists = cursor.fetchone()[0]
            
            if not old_table_exists:
                # Przemianuj z powrotem
                cursor.execute('ALTER TABLE matterhorn1_stock_history RENAME TO stock_history;')


class Migration(migrations.Migration):

    dependencies = [
        ('matterhorn1', '0002_watchdog_periodic_task'),
    ]

    operations = [
        # Najpierw zaktualizuj db_table w modelu
        migrations.AlterModelTable(
            name='stockhistory',
            table='matterhorn1_stock_history',
        ),
        # Jeśli tabela stock_history istnieje, przemianuj ją na matterhorn1_stock_history
        # Jeśli nie istnieje, utwórz matterhorn1_stock_history bezpośrednio
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    -- Jeśli stock_history istnieje i matterhorn1_stock_history nie istnieje, przemianuj
                    IF EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'stock_history'
                    ) AND NOT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'matterhorn1_stock_history'
                    ) THEN
                        ALTER TABLE stock_history RENAME TO matterhorn1_stock_history;
                    -- Jeśli żadna z tabel nie istnieje, utwórz matterhorn1_stock_history
                    ELSIF NOT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'stock_history'
                    ) AND NOT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'matterhorn1_stock_history'
                    ) THEN
                        CREATE TABLE matterhorn1_stock_history (
                            id SERIAL PRIMARY KEY,
                            variant_uid VARCHAR(50) NOT NULL,
                            product_uid INTEGER NOT NULL,
                            product_name VARCHAR(500),
                            variant_name VARCHAR(50),
                            old_stock INTEGER,
                            new_stock INTEGER,
                            stock_change INTEGER,
                            change_type VARCHAR(20),
                            timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                        );
                        CREATE INDEX mh1_sh_variant_idx ON matterhorn1_stock_history (variant_uid);
                        CREATE INDEX mh1_sh_product_idx ON matterhorn1_stock_history (product_uid);
                        CREATE INDEX mh1_sh_timestamp_idx ON matterhorn1_stock_history (timestamp);
                        CREATE INDEX mh1_sh_change_idx ON matterhorn1_stock_history (change_type);
                        CREATE INDEX mh1_sh_prod_time_idx ON matterhorn1_stock_history (product_uid, timestamp);
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    -- Odwróć przemianowanie
                    IF EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'matterhorn1_stock_history'
                    ) AND NOT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'stock_history'
                    ) THEN
                        ALTER TABLE matterhorn1_stock_history RENAME TO stock_history;
                    END IF;
                END $$;
            """,
        ),
    ]

