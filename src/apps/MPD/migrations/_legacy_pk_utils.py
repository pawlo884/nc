"""Pomocnik migracji MPD — legacy tabele bez PRIMARY KEY na kolumnie id."""


def ensure_primary_key_on_tables(schema_editor, table_names):
    if schema_editor.connection.alias != 'MPD':
        return

    with schema_editor.connection.cursor() as cursor:
        for table in table_names:
            cursor.execute(
                f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = current_schema()
                          AND table_name = '{table}'
                    ) THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name = '{table}'
                          AND column_name = 'id'
                    ) THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint c
                        JOIN pg_class t ON c.conrelid = t.oid
                        WHERE t.relname = '{table}' AND c.contype = 'p'
                    ) THEN
                        DELETE FROM {table} a
                        USING {table} b
                        WHERE a.ctid < b.ctid AND a.id = b.id;

                        ALTER TABLE {table} ADD PRIMARY KEY (id);
                    END IF;
                END $$;
                """
            )


def drop_unique_constraints_on_table(schema_editor, table_name):
    if schema_editor.connection.alias != 'MPD':
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"""
            DO $$
            DECLARE r RECORD;
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = current_schema()
                      AND table_name = '{table_name}'
                ) THEN
                    RETURN;
                END IF;

                FOR r IN
                    SELECT c.conname
                    FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    WHERE t.relname = '{table_name}' AND c.contype = 'u'
                LOOP
                    EXECUTE format(
                        'ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS %I',
                        r.conname
                    );
                END LOOP;
            END $$;
            """
        )


def ensure_unique_constraint(schema_editor, table_name, constraint_name, columns):
    if schema_editor.connection.alias != 'MPD':
        return

    columns_sql = ', '.join(columns)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = current_schema()
                      AND table_name = '{table_name}'
                ) THEN
                    RETURN;
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    WHERE t.relname = '{table_name}' AND c.contype = 'u'
                ) THEN
                    ALTER TABLE {table_name}
                    ADD CONSTRAINT {constraint_name}
                    UNIQUE ({columns_sql});
                END IF;
            END $$;
            """
        )


# Tabele MPD czesto bez PK w starym schemacie produkcyjnym
MPD_LEGACY_PK_TABLES = [
    'attributes',
    'brands',
    'collections',
    'colors',
    'seasons',
    'products',
    'product_attributes',
    'sizes',
    'sources',
    'product_variants',
    'product_variants_sources',
    'product_variants_retail_price',
    'product_images',
    'product_set',
    'product_set_items',
    'product_series',
    'stock_and_prices',
    'stock_history',
    'categories',
    'vat',
    'path',
    'product_path',
    'units',
    'fabric_component',
    'product_fabric',
    'full_change_files',
]
