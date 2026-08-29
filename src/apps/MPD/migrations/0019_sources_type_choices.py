from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0018_sources_type_not_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sources',
            name='type',
            field=models.CharField(
                choices=[
                    ('Magazyn główny', 'Magazyn główny'),
                    ('Magazyn obcy', 'Magazyn obcy'),
                    ('Magazyn wymiany', 'Magazyn wymiany'),
                    ('Magazyn pomocniczy', 'Magazyn pomocniczy'),
                ],
                help_text='Typ magazynu IAI.',
                max_length=255,
            ),
        ),
    ]
