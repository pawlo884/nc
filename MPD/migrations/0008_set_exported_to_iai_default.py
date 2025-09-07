# Generated manually to set default value for exported_to_iai

from django.db import migrations


def set_exported_to_iai_default(apps, schema_editor):
    """Ustaw wartość domyślną False dla wszystkich rekordów z NULL w exported_to_iai"""
    Products = apps.get_model('MPD', 'Products')
    Products.objects.using('MPD').filter(
        exported_to_iai__isnull=True).update(exported_to_iai=False)


def reverse_set_exported_to_iai_default(apps, schema_editor):
    """Funkcja odwrotna - nie robi nic"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0007_alter_products_exported_to_iai'),
    ]

    operations = [
        migrations.RunPython(
            set_exported_to_iai_default,
            reverse_set_exported_to_iai_default,
        ),
    ]
