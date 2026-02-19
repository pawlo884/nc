# Kod producenta per hurtownia w product_variants_sources (zamiast tylko other)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0005_stockandprices_id_autoincrement'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariantssources',
            name='producer_code',
            field=models.CharField(
                blank=True,
                help_text='Kod producenta w tej hurtowni (np. symbol w Tabu, variant_uid w Matterhorn).',
                max_length=255,
                null=True
            ),
        ),
    ]
