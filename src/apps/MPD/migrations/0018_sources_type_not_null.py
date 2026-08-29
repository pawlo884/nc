from django.db import migrations, models


def fill_null_source_types(apps, schema_editor):
    Sources = apps.get_model('MPD', 'Sources')
    Sources.objects.using(schema_editor.connection.alias).filter(
        type__isnull=True
    ).update(type='Magazyn obcy')


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0017_alter_productvariantssources_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(fill_null_source_types, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='sources',
            name='type',
            field=models.CharField(
                help_text='Np. hurtownia, api, Magazyn główny, Magazyn obcy, Magazyn wymiany, Magazyn pomocniczy',
                max_length=255,
            ),
        ),
    ]
