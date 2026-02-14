# Usunięcie nieużywanych modeli Product, ProductImage, ProductVariant

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tabu', '0003_tabu_product_detail_gallery'),
    ]

    operations = [
        migrations.DeleteModel(name='ProductImage'),
        migrations.DeleteModel(name='ProductVariant'),
        migrations.DeleteModel(name='Product'),
    ]
