# colors_name_key (UNIQUE) i colors_name_not_null istnieją w bazie MPD od dawna —
# model dotąd tego nie odzwierciedlał (name = CharField(null=True) bez unique).
# DDL idempotentne (IF NOT EXISTS), bo na prod baza już to ma.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0022_merge_20260829_1405'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE colors ALTER COLUMN name SET NOT NULL;",
                    reverse_sql="ALTER TABLE colors ALTER COLUMN name DROP NOT NULL;",
                ),
                migrations.RunSQL(
                    sql=(
                        "DO $$ BEGIN "
                        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'colors_name_key') "
                        "THEN ALTER TABLE colors ADD CONSTRAINT colors_name_key UNIQUE (name); "
                        "END IF; END $$;"
                    ),
                    reverse_sql="ALTER TABLE colors DROP CONSTRAINT IF EXISTS colors_name_key;",
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='colors',
                    name='name',
                    field=models.CharField(max_length=50, unique=True),
                ),
            ],
        ),
    ]
