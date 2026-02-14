# Generated manually - brand/category FK w TabuProduct

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tabu', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tabuproduct',
            old_name='category_id',
            new_name='api_category_id',
        ),
        migrations.RenameField(
            model_name='tabuproduct',
            old_name='producer_id',
            new_name='api_producer_id',
        ),
        migrations.AlterField(
            model_name='tabuproduct',
            name='category_path',
            field=models.CharField(
                blank=True,
                help_text="Ścieżka kategorii z API, np. 'Dla niej > Skarpetki > Stopki'",
                max_length=500,
            ),
        ),
        migrations.AlterField(
            model_name='tabuproduct',
            name='producer_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='tabuproduct',
            name='brand',
            field=models.ForeignKey(
                blank=True,
                db_column='tabu_brand_fk_id',
                help_text='Marka/producent z API (producer_id)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tabu_products',
                to='tabu.brand',
            ),
        ),
        migrations.AddField(
            model_name='tabuproduct',
            name='category',
            field=models.ForeignKey(
                blank=True,
                db_column='tabu_category_fk_id',
                help_text='Kategoria z API (category_id)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tabu_products',
                to='tabu.category',
            ),
        ),
    ]
