# Generated manually 2026-03-22
# Fixes model issues identified in MPD app review:
# 1. Colors.parent_id (FK named with _id suffix) -> parent
# 2. ProductVariants.color/producer_color: CASCADE -> SET_NULL
# 3. Products.series: DO_NOTHING -> SET_NULL
# 4. ProductSetItem.product_set_id/product_id: IntegerField -> ForeignKey
# 5. ProductPaths.product_id/path_id: IntegerField -> ForeignKey
# 6. FabricComponent/ProductFabric: add managed = True

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0014_remove_productimage_iai_product_id_and_more'),
    ]

    operations = [
        # 1. Rename Colors.parent_id field (ForeignKey was confusingly named with _id suffix)
        migrations.RenameField(
            model_name='colors',
            old_name='parent_id',
            new_name='parent',
        ),

        # 2. ProductVariants: color CASCADE -> SET_NULL
        migrations.AlterField(
            model_name='productvariants',
            name='color',
            field=models.ForeignKey(
                blank=True,
                db_column='color_id',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='MPD.colors',
            ),
        ),

        # 3. ProductVariants: producer_color CASCADE -> SET_NULL
        migrations.AlterField(
            model_name='productvariants',
            name='producer_color',
            field=models.ForeignKey(
                blank=True,
                db_column='producer_color_id',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='producer_variants',
                to='MPD.colors',
            ),
        ),

        # 4. Products: series DO_NOTHING -> SET_NULL
        migrations.AlterField(
            model_name='products',
            name='series',
            field=models.ForeignKey(
                blank=True,
                db_column='series_id',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='MPD.productseries',
            ),
        ),

        # 5a. ProductSetItem: product_set_id IntegerField -> ForeignKey
        migrations.AlterField(
            model_name='productsetitem',
            name='product_set_id',
            field=models.ForeignKey(
                db_column='product_set_id',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='items',
                to='MPD.productset',
            ),
        ),
        migrations.RenameField(
            model_name='productsetitem',
            old_name='product_set_id',
            new_name='product_set',
        ),

        # 5b. ProductSetItem: product_id IntegerField -> ForeignKey
        migrations.AlterField(
            model_name='productsetitem',
            name='product_id',
            field=models.ForeignKey(
                db_column='product_id',
                on_delete=django.db.models.deletion.CASCADE,
                to='MPD.products',
            ),
        ),
        migrations.RenameField(
            model_name='productsetitem',
            old_name='product_id',
            new_name='product',
        ),

        # 6a. ProductPaths: remove old unique_together (uses old field names)
        migrations.AlterUniqueTogether(
            name='productpaths',
            unique_together=set(),
        ),

        # 6b. ProductPaths: product_id IntegerField -> ForeignKey
        migrations.AlterField(
            model_name='productpaths',
            name='product_id',
            field=models.ForeignKey(
                db_column='product_id',
                on_delete=django.db.models.deletion.CASCADE,
                to='MPD.products',
            ),
        ),
        migrations.RenameField(
            model_name='productpaths',
            old_name='product_id',
            new_name='product',
        ),

        # 6c. ProductPaths: path_id IntegerField -> ForeignKey
        migrations.AlterField(
            model_name='productpaths',
            name='path_id',
            field=models.ForeignKey(
                db_column='path_id',
                on_delete=django.db.models.deletion.CASCADE,
                to='MPD.paths',
            ),
        ),
        migrations.RenameField(
            model_name='productpaths',
            old_name='path_id',
            new_name='path',
        ),

        # 6d. ProductPaths: restore unique_together with new field names
        migrations.AlterUniqueTogether(
            name='productpaths',
            unique_together={('product', 'path')},
        ),
    ]
