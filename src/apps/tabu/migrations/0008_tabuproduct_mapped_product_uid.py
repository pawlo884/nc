# Generated manually for Tabu integrator

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tabu', '0007_add_stock_history'),
    ]

    operations = [
        migrations.AddField(
            model_name='tabuproduct',
            name='mapped_product_uid',
            field=models.IntegerField(blank=True, db_index=True, help_text='ID produktu w bazie MPD', null=True),
        ),
    ]
