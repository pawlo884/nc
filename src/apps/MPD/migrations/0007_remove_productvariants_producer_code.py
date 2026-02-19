# Usunięcie producer_code z product_variants (kod producenta tylko w product_variants_sources)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0006_productvariantssources_producer_code'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productvariants',
            name='producer_code',
        ),
    ]
