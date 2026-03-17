from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("MPD", "0008_alter_productvariantssources_variant_uid"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="productvariants",
            name="iai_product_id",
        ),
    ]

