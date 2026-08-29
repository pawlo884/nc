# Tabela path powstała z rename categories → path; constraint UNIQUE (name)
# został ze starą nazwą categories_name_key. Nazwy ścieżek mogą się powtarzać
# w różnych gałęziach drzewa (np. „Biustonosze | Topy” w bieliźnie i strojach kąpielowych).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0019_sources_type_choices'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE path DROP CONSTRAINT IF EXISTS categories_name_key;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP INDEX IF EXISTS categories_name_key;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
