# Generated manually to fix exported_to_iai NULL constraint issue

from django.db import migrations, models


def fix_exported_to_iai_null(apps, schema_editor):
    """Ustaw wartość domyślną False dla wszystkich rekordów z NULL w exported_to_iai"""
    Products = apps.get_model('MPD', 'Products')
    Products.objects.using('MPD').filter(
        exported_to_iai__isnull=True).update(exported_to_iai=False)


def reverse_fix_exported_to_iai_null(apps, schema_editor):
    """Funkcja odwrotna - nie robi nic"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0005_remove_products_exported_in_full'),
    ]

    operations = [
        # Najpierw ustaw wartość domyślną dla istniejących rekordów
        migrations.RunPython(
            fix_exported_to_iai_null,
            reverse_fix_exported_to_iai_null,
        ),
        # Następnie zmień pole na null=True
        migrations.AlterField(
            model_name='products',
            name='exported_to_iai',
            field=models.BooleanField(
                default=False, null=True, verbose_name='Wyeksportowany do IAI'),
        ),
    ]
