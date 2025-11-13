# Generated migration to change image_url from URLField to CharField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matterhorn1', '0004_ensure_stock_history_table'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productimage',
            name='image_url',
            field=models.CharField(max_length=1000),
        ),
    ]

