from django.db import migrations


class Migration(migrations.Migration):
    """
    Usunięcie kolumny iai_product_id z tabeli product_variants.

    Używamy RunSQL z DROP COLUMN IF EXISTS, żeby migracja była idempotentna
    i nie wywalała się w scenariuszu, gdy inna gałąź (0010_remove_productimage_iai_product_id_and_more)
    usunie kolumnę wcześniej.
    """

    dependencies = [
        ("MPD", "0008_alter_productvariantssources_variant_uid"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE product_variants
                DROP COLUMN IF EXISTS iai_product_id;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
