# Generated manually for source (matterhorn1 | tabu)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web_agent', '0006_alter_brandconfig_category_config_aiprompt'),
    ]

    operations = [
        migrations.AddField(
            model_name='automationrun',
            name='source',
            field=models.CharField(
                choices=[('matterhorn1', 'Matterhorn1'), ('tabu', 'Tabu')],
                default='matterhorn1',
                help_text='Źródło produktów: Matterhorn1 (przeglądarka) lub Tabu (backend).',
                max_length=20,
                verbose_name='Źródło',
            ),
        ),
    ]
