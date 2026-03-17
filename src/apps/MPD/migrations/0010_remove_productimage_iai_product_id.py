from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("MPD", "0009_remove_productvariants_iai_product_id"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE product_images
            DROP COLUMN IF EXISTS iai_product_id;
            """,
            reverse_sql="""
            ALTER TABLE product_images
            ADD COLUMN IF NOT EXISTS iai_product_id integer NULL;
            """,
        ),
    ]

