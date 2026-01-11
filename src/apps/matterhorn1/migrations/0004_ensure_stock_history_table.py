"""Zapewnij istnienie tabeli matterhorn1_stock_history.

Scenariusze obsługiwane:
- jeśli istnieje stara tabela stock_history, a brakuje nowej, wykonujemy rename,
- jeśli żadna tabela nie istnieje, tworzymy matterhorn1_stock_history z indeksami.
"""

from django.db import migrations


SQL_RENAME_OR_CREATE = """
DO $$
BEGIN
    -- Jeśli istnieje stara tabela i brakuje nowej, przemianuj
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
    END IF;

    -- Jeśli po rename nadal brak tabeli, utwórz ją
    IF NOT EXISTS (
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
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    END IF;
END $$;
"""


SQL_CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS mh1_sh_variant_idx ON matterhorn1_stock_history (variant_uid);
CREATE INDEX IF NOT EXISTS mh1_sh_product_idx ON matterhorn1_stock_history (product_uid);
CREATE INDEX IF NOT EXISTS mh1_sh_timestamp_idx ON matterhorn1_stock_history (timestamp);
CREATE INDEX IF NOT EXISTS mh1_sh_change_idx ON matterhorn1_stock_history (change_type);
CREATE INDEX IF NOT EXISTS mh1_sh_prod_time_idx ON matterhorn1_stock_history (product_uid, timestamp);
"""


class Migration(migrations.Migration):

    dependencies = [
        ('matterhorn1', '0003_rename_stock_history_table'),
    ]

    operations = [
        migrations.RunSQL(
            sql=SQL_RENAME_OR_CREATE,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql=SQL_CREATE_INDEXES,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]


