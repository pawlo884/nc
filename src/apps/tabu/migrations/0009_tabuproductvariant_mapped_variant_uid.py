# Wzorzec jak Matterhorn: mapped_variant_uid + is_mapped dla linkowania i syncu stanów

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tabu', '0008_tabuproduct_mapped_product_uid'),
    ]

    operations = [
        migrations.AddField(
            model_name='tabuproductvariant',
            name='mapped_variant_uid',
            field=models.IntegerField(
                blank=True,
                db_index=True,
                help_text='ID wariantu w bazie MPD (variant_id)',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='tabuproductvariant',
            name='is_mapped',
            field=models.BooleanField(
                blank=True,
                help_text='Czy wariant jest zmapowany do MPD',
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name='tabuproductvariant',
            index=models.Index(fields=['mapped_variant_uid'], name='tabu_produ_mapped__idx'),
        ),
    ]
