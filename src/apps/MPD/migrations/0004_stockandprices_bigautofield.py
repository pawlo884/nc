# Generated manually - BigAutoField dla StockAndPrices (id auto-generowane)
# Tabela ma już DEFAULT (BIGSERIAL) - tylko aktualizacja stanu modelu Django

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MPD', '0003_seasons_products_season'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='stockandprices',
                    name='id',
                    field=models.BigAutoField(primary_key=True, serialize=False),
                ),
            ],
            database_operations=[],  # DB już ma DEFAULT - bez zmian
        ),
    ]
